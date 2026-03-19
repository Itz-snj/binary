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
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
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


@app.post("/webhook/sentry")
async def receive_sentry_webhook(request: Request):
    """
    Receive a Sentry webhook, parse it, and kick off the pipeline async.
    Returns 200 immediately so Sentry doesn't retry.
    """
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    # Parse payload into an IssueRecord
    try:
        issue = parse_sentry_webhook(payload)
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
            openai_api_key=OPENAI_API_KEY,
            github_token=GITHUB_TOKEN,
            github_repo=GITHUB_REPO,
        )
    )

    return JSONResponse({"status": "accepted", "issue_id": issue.id})


@app.get("/issues")
async def list_issues():
    issues = await db.list_issues(DATABASE_PATH)
    return [issue.model_dump(mode="json") for issue in issues]


@app.get("/issues/{issue_id}")
async def get_issue(issue_id: str):
    issue = await db.get_issue(issue_id, DATABASE_PATH)
    if not issue:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return issue.model_dump(mode="json")


@app.get("/stream")
async def sse_stream():
    """Server-Sent Events endpoint for real-time dashboard updates."""
    async def event_generator():
        async for msg in subscribe():
            yield {
                "event": msg.get("event", "message"),
                "data": json.dumps(msg.get("data", {})),
            }

    return EventSourceResponse(event_generator())
