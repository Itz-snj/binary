"""Auth router.

Owns signup, login, session inspection, and workspace listing.

Both the legacy paths (``/api/login``, ``/api/signup``) and the new
plan paths (``/api/auth/...``) are exposed so the dashboard can move
over incrementally without breaking existing clients.
"""

from __future__ import annotations

import logging
import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app import auth as _auth
from app import database as db
from app.core.security import get_current_workspace, oauth2_scheme
from app.schemas.auth import AuthSession, SignupRequest
from app.models import User, Workspace

logger = logging.getLogger("slothops.api.auth")

router = APIRouter(tags=["auth"])


async def _do_signup(req: SignupRequest) -> dict:
    try:
        existing = await db.get_user_by_email(req.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user_id = str(uuid.uuid4())
        hashed = _auth.get_password_hash(req.password)
        user = User(id=user_id, email=req.email, hashed_password=hashed)
        await db.create_user(user)

        workspace_id = str(uuid.uuid4())
        workspace = Workspace(id=workspace_id, name=req.workspace_name)
        await db.create_workspace(workspace)
        await db.add_user_to_workspace(workspace_id, user_id, role="admin")

        access_token = _auth.create_access_token(
            data={"sub": user.email, "workspace_id": workspace_id}
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Signup 500: %s %s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Engine Error: {str(e)}")


async def _do_login(form_data: OAuth2PasswordRequestForm) -> dict:
    try:
        user = await db.get_user_by_email(form_data.username)
        if not user or not _auth.verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect email or password")

        workspaces = await db.get_user_workspaces(user.id)
        workspace_id = workspaces[0].id if workspaces else "default_workspace"

        access_token = _auth.create_access_token(
            data={"sub": user.email, "workspace_id": workspace_id}
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login 500: %s %s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Engine Error: {str(e)}")


# Legacy paths (kept for existing clients).
@router.post("/api/signup")
async def signup_legacy(req: SignupRequest) -> dict:
    return await _do_signup(req)


@router.post("/api/login")
async def login_legacy(form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
    return await _do_login(form_data)


# New paths from the plan.
@router.post("/api/auth/signup")
async def signup(req: SignupRequest) -> dict:
    return await _do_signup(req)


@router.post("/api/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
    return await _do_login(form_data)


@router.post("/api/auth/logout")
async def logout() -> dict:
    """Stateless logout. The JWT is held client-side; this endpoint
    exists so the frontend has a single place to call. Once we move
    to server-side sessions or token revocation, this becomes useful.
    """
    return {"status": "logged_out"}


@router.get("/api/auth/me", response_model=AuthSession)
async def me(token: str = Depends(oauth2_scheme)) -> AuthSession:
    token_data = _auth.decode_access_token(token)
    if not token_data.user_id or not token_data.workspace_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.get_user_by_email(token_data.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return AuthSession(
        user_id=user.id,
        email=user.email,
        workspace_id=token_data.workspace_id,
        role="admin",
    )


@router.get("/api/auth/workspaces")
async def list_workspaces(token: str = Depends(oauth2_scheme)) -> list[dict]:
    token_data = _auth.decode_access_token(token)
    if not token_data.user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.get_user_by_email(token_data.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    workspaces = await db.get_user_workspaces(user.id)
    return [w.model_dump() for w in workspaces]


# Re-export for type hints; useful for tests that import from this module.
__all__ = ["router", "get_current_workspace"]
