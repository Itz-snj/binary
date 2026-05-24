"""
SlothOps Engine — FastAPI Application
Entry point for the server.  Defines all HTTP endpoints and starts
the pipeline asynchronously on incoming Sentry webhooks.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from app import database as db
from app.models import AuditAction, AuditEvent, IssueRecord, RollbackStatus
from app.pipelines.pipeline import run_pipeline
from app.integrations.sentry_parser import parse_sentry_webhook
from app.sse_manager import broadcast, subscribe
from app.integrations.webhook_security import extract_github_delivery_id, verify_github_signature, verify_sentry_signature
# ── Load env early (before config.py import to avoid crash in dev) ───
from dotenv import load_dotenv
load_dotenv()


GITHUB_APP_ID = os.getenv("GITHUB_APP_ID", None)

# Support both inline PEM and file path
_pem_raw = os.getenv("GITHUB_APP_PRIVATE_KEY", "")
if _pem_raw and os.path.isfile(_pem_raw):
    with open(_pem_raw, "r") as f:
        GITHUB_APP_PRIVATE_KEY = f.read()
elif _pem_raw:
    GITHUB_APP_PRIVATE_KEY = _pem_raw.replace("\\n", "\n")
else:
    GITHUB_APP_PRIVATE_KEY = None
DATABASE_PATH = os.getenv("DATABASE_PATH", "./slothops.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s  %(name)-28s  %(levelname)-5s  %(message)s",
)
logger = logging.getLogger("slothops.main")


class SSELogHandler(logging.Handler):
    """Forward Python logs to connected dashboard clients over SSE."""

    def __init__(self) -> None:
        super().__init__()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def emit(self, record: logging.LogRecord) -> None:
        loop = self._loop
        if not loop or loop.is_closed():
            return

        # Prevent accidental recursion if SSE internals log.
        if record.name.startswith("slothops.sse"):
            return

        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        def _dispatch() -> None:
            asyncio.create_task(broadcast("log", payload))

        loop.call_soon_threadsafe(_dispatch)


sse_log_handler = SSELogHandler()


# ── Lifespan (runs on startup / shutdown) ────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    root_logger = logging.getLogger()
    if not any(isinstance(h, SSELogHandler) for h in root_logger.handlers):
        sse_log_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        root_logger.addHandler(sse_log_handler)
    sse_log_handler.set_loop(asyncio.get_running_loop())

    logger.info("Initialising database at %s", DATABASE_PATH)
    await db.init_db(DATABASE_PATH)
    logger.info("SlothOps engine ready 🦥")
    yield
    logger.info("Shutting down")


# ── FastAPI App ──────────────────────────────────────────────────────────
app = FastAPI(
    title="SlothOps Engine",
    description="Production-aware automated bug remediation pipeline",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

WEB_DIST_DIR = os.path.join(os.path.dirname(__file__), "web", "dist")

# ── Auth & Security ──────────────────────────────────────────────────────
from fastapi import Depends, HTTPException, status
from pydantic import BaseModel
from app import auth
import uuid
from app.core.security import oauth2_scheme, get_current_workspace


# ── Routes ───────────────────────────────────────────────────────────────

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.qa import router as qa_router
from app.api.repos import router as repos_router
from app.api.rollbacks import router as rollbacks_router
from app.api.webhooks import router as webhooks_router
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(health_router)
app.include_router(qa_router)
app.include_router(repos_router)
app.include_router(rollbacks_router)
app.include_router(webhooks_router)


@app.get("/")
async def serve_dashboard():
    index_path = os.path.join(WEB_DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({
        "message": "Dashboard build not found.",
        "hint": "Run `cd web && bun install && bun run build`, or use the Docker image which builds it automatically.",
    })

@app.get("/assets/{file_path:path}")
async def serve_web_assets(file_path: str):
    """Serve Vite-built assets (JS/CSS bundles, fonts) from web/dist/assets."""
    safe_path = os.path.normpath(file_path)
    if safe_path.startswith(".."):
        return JSONResponse({"error": "Forbidden"}, status_code=403)
    full_path = os.path.join(WEB_DIST_DIR, "assets", safe_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return FileResponse(full_path)
    return JSONResponse({"error": "Not found"}, status_code=404)

@app.get("/logo.png")
async def serve_logo():
    logo_path = os.path.join(WEB_DIST_DIR, "logo.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path)
    return JSONResponse({"error": "Not found"}, status_code=404)


from pydantic import BaseModel

class GithubLinkRequest(BaseModel):
    installation_id: str

@app.post("/api/github/link")
async def link_github_installation(req: GithubLinkRequest, workspace_id: str = Depends(get_current_workspace)):
    """
    Called securely by the Frontend Dashboard immediately after the user installs 
    the GitHub App and is redirected back to the Setup URL.
    Pairs the App Installation mathematically to their verified JWT workspace_id.
    """
    from app.models import Integration
    # Upsert the integration row
    integration = Integration(
        workspace_id=workspace_id,
        github_installation_id=req.installation_id
    )
    await db.upsert_integration(integration, DATABASE_PATH)
    logger.info("Successfully bound GitHub Installation %s to Workspace %s via Dashboard OAuth redirect!", req.installation_id, workspace_id)
    return {"status": "linked", "workspace": workspace_id}


# ── Developer Config ─────────────────────────────────────────────────────

@app.post("/api/developer-config")
async def upload_developer_config(request: Request, workspace_id: str = Depends(get_current_workspace)):
    """Upload or update developer.json style preferences for this workspace."""
    try:
        config = await request.json()
        import json as _json
        await db.upsert_developer_config(workspace_id, _json.dumps(config), DATABASE_PATH)
        logger.info("Developer config saved for workspace %s", workspace_id)
        return {"status": "saved", "workspace": workspace_id}
    except Exception as e:
        logger.error("Failed to save developer config: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid config: {str(e)}")

@app.get("/api/developer-config")
async def get_developer_config(workspace_id: str = Depends(get_current_workspace)):
    """Retrieve current developer.json preferences for this workspace."""
    config = await db.get_developer_config(workspace_id, DATABASE_PATH)
    if config is None:
        return {"config": None, "message": "No developer config set. Upload one to enable style reviews."}
    return {"config": config}


@app.get("/api/audit-events")
async def get_audit_events(
    repo_name: str | None = None,
    action: str | None = None,
    limit: int = 50,
    workspace_id: str = Depends(get_current_workspace),
):
    """Audit trail for this workspace, filtered by repo or action."""
    events = await db.list_audit_events(
        workspace_id, repo_name=repo_name, action=action,
        limit=min(limit, 200), db_path=DATABASE_PATH,
    )
    return [e.model_dump(mode="json") for e in events]


# ── Issue Routes ─────────────────────────────────────────────────────────

@app.get("/issues")
async def list_issues(workspace_id: str = Depends(get_current_workspace)):
    issues = await db.list_issues(workspace_id, DATABASE_PATH)
    return [issue.model_dump(mode="json") for issue in issues]

@app.get("/issues/{issue_id}")
async def get_issue(issue_id: str, workspace_id: str = Depends(get_current_workspace)):
    issue = await db.get_issue(issue_id, workspace_id, DATABASE_PATH)
    if not issue:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return issue.model_dump(mode="json")

# ── Integration & Health Status ──────────────────────────────────────────

@app.get("/api/integrations/status")
async def integrations_status(workspace_id: str = Depends(get_current_workspace)):
    """
    Returns live integration status for the current workspace:
    - GitHub App linked? Which repos?
    - Which repo is the active target?
    - Sentry webhook configured?
    """
    integration = await db.get_integration(workspace_id, DATABASE_PATH)

    github_linked = False
    github_repos = []
    github_installation_id = None
    target_repo = os.getenv("GITHUB_REPO", "")

    if integration and integration.github_installation_id:
        github_installation_id = integration.github_installation_id
        github_linked = True

        # Fetch actual connected repos using the correct GitHub App API
        try:
            from app.integrations.github_app import get_integration
            gi = get_integration(GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY)
            inst = gi.get_app_installation(int(integration.github_installation_id))

            for repo in inst.get_repos():
                is_target = (repo.full_name == target_repo)
                github_repos.append({
                    "full_name": repo.full_name,
                    "private": repo.private,
                    "default_branch": repo.default_branch,
                    "language": repo.language,
                    "url": repo.html_url,
                    "is_target": is_target,
                })

            # Sort: target repo first, then alphabetical
            github_repos.sort(key=lambda r: (not r["is_target"], r["full_name"]))

        except Exception as e:
            logger.warning("Could not fetch repos for workspace %s: %s", workspace_id, e)

    return {
        "github": {
            "linked": github_linked,
            "installation_id": github_installation_id,
            "target_repo": target_repo,
            "repos": github_repos,
            "total_repos": len(github_repos),
        },
        "sentry": {
            "webhook_url": f"{os.getenv('BASE_URL', '')}/webhook/sentry/{workspace_id}",
            "configured": True,
        },
    }


@app.get("/stream")
async def sse_stream(token: str):
    """Server-Sent Events endpoint for real-time dashboard updates. 
    Uses ?token query param since EventSource does not natively support Authorization headers.
    """
    token_data = auth.decode_access_token(token)
    if not token_data.workspace_id:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    async def event_generator():
        async for msg in subscribe():
            yield {
                "event": msg.get("event", "message"),
                "data": json.dumps(msg.get("data", {})),
            }

    return EventSourceResponse(event_generator())


@app.get("/{spa_path:path}")
async def serve_spa(spa_path: str):
    """Catch-all: return index.html for any path the React Router owns (e.g. /docs, /login, /overview)."""
    index_path = os.path.join(WEB_DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "Dashboard build not found."}, status_code=404)

