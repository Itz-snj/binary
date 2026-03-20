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
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

import database as db
from models import IssueRecord
from pipeline import run_pipeline
from sentry_parser import parse_sentry_webhook
from sse_manager import subscribe
# ── Load env early (before config.py import to avoid crash in dev) ───
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", None)
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID", None)
GITHUB_APP_PRIVATE_KEY = os.getenv("GITHUB_APP_PRIVATE_KEY", "").replace("\\n", "\n") if os.getenv("GITHUB_APP_PRIVATE_KEY") else None
DATABASE_PATH = os.getenv("DATABASE_PATH", "./slothops.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s  %(name)-28s  %(levelname)-5s  %(message)s",
)
logger = logging.getLogger("slothops.main")


# ── Lifespan (runs on startup / shutdown) ────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
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
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# ── Auth & Security ──────────────────────────────────────────────────────
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import auth
import uuid
from models import User, Workspace

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

async def get_current_workspace(token: str = Depends(oauth2_scheme)):
    token_data = auth.decode_access_token(token)
    if not token_data.workspace_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token_data.workspace_id

class SignupRequest(BaseModel):
    email: str
    password: str
    workspace_name: str

@app.post("/api/signup")
async def signup(req: SignupRequest):
    existing = await db.get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    hashed = auth.get_password_hash(req.password)
    user = User(id=user_id, email=req.email, hashed_password=hashed)
    await db.create_user(user)
    
    workspace_id = str(uuid.uuid4())
    workspace = Workspace(id=workspace_id, name=req.workspace_name)
    await db.create_workspace(workspace)
    await db.add_user_to_workspace(workspace_id, user_id, role="admin")
    
    access_token = auth.create_access_token(
        data={"sub": user.email, "workspace_id": workspace_id}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await db.get_user_by_email(form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    workspaces = await db.get_user_workspaces(user.id)
    workspace_id = workspaces[0].id if workspaces else "default_workspace"
    
    access_token = auth.create_access_token(
        data={"sub": user.email, "workspace_id": workspace_id}
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ── Routes ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "slothops-engine"}


@app.get("/")
async def serve_dashboard():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "Dashboard not built yet. See Phase 3."})

@app.get("/style.css")
async def serve_css():
    css_path = os.path.join(STATIC_DIR, "style.css")
    if os.path.exists(css_path):
        return FileResponse(css_path)
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.post("/webhook/sentry/{workspace_id}")
async def receive_sentry_webhook(workspace_id: str, request: Request):
    """
    Receive a Sentry webhook, parse it, bind to workspace, and kick off the pipeline async.
    Returns 200 immediately so Sentry doesn't retry.
    """
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    # Parse payload into an IssueRecord
    try:
        issue = parse_sentry_webhook(payload)
        issue.workspace_id = workspace_id
    except Exception as exc:
        logger.error("Failed to parse Sentry payload: %s", exc)
        return JSONResponse({"error": "Parse failed"}, status_code=400)

    logger.info(
        "Webhook received: %s — %s in %s",
        issue.error_type,
        issue.error_message,
        issue.file_path,
    )

    # Kick off pipeline in background
    asyncio.create_task(
        run_pipeline(
            issue=issue,
            db_path=DATABASE_PATH,
            gemini_api_key=GEMINI_API_KEY,
            github_repo=GITHUB_REPO,
            github_token=GITHUB_TOKEN,
            github_app_id=GITHUB_APP_ID,
            github_app_private_key=GITHUB_APP_PRIVATE_KEY,
        )
    )

    return JSONResponse({"status": "accepted", "issue_id": issue.id})

@app.post("/webhook/github")
async def receive_github_webhook(request: Request):
    """
    Receives GitHub App install/uninstall Background Webhooks.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    action = payload.get("action")
    if action == "created" and "installation" in payload:
        installation_id = str(payload["installation"]["id"])
        
        # When moving fully to SaaS, the Setup Action URL tracks `workspace_id` via a state integer.
        # For the engine, we automatically bind new app installs to the `default_workspace`.
        from models import Integration
        integration = Integration(
            workspace_id="default_workspace", 
            github_installation_id=installation_id
        )
        await db.upsert_integration(integration, DATABASE_PATH)
        logger.info(f"GitHub App explicitly granted permissions! Bootstrapped Installation ID {installation_id} into Integrations table natively.")

    return {"status": "ok"}


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
