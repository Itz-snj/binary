"""Security / auth dependencies for FastAPI.

Lifted out of main.py so routers in app.api.* can declare
``Depends(get_current_workspace)`` without reaching into main.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

import auth as _auth_module

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


async def get_current_workspace(token: str = Depends(oauth2_scheme)) -> str:
    token_data = _auth_module.decode_access_token(token)
    if not token_data.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return token_data.workspace_id
