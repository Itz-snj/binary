"""Auth request/response schemas.

Pydantic models exposed to the dashboard. The original SignupRequest
declared inline in main.py is re-exported here so future code uses
the new path.
"""

from pydantic import BaseModel


class SignupRequest(BaseModel):
    email: str
    password: str
    workspace_name: str


class AuthSession(BaseModel):
    """Returned by GET /api/auth/me once that endpoint lands."""
    user_id: str
    email: str
    workspace_id: str
    role: str
