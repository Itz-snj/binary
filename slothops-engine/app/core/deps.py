"""Shared FastAPI dependencies.

Reserved for things like ``get_db_path``, ``get_settings``,
``get_workspace_or_404``. Today nothing lives here yet — the file
exists so the new layout is discoverable.
"""

from .config import Settings, load_settings


def get_settings() -> Settings:
    """Return the singleton settings object (re-read each call for now)."""
    return load_settings()
