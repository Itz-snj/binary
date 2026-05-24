"""Central GitHub App authentication helpers."""

from __future__ import annotations

import os

from github import Auth, Github, GithubIntegration


def load_private_key(raw_or_path: str | None) -> str:
    if not raw_or_path:
        raise RuntimeError("GITHUB_APP_PRIVATE_KEY is not configured")
    if os.path.isfile(raw_or_path):
        with open(raw_or_path, "r") as f:
            return f.read()
    return raw_or_path.replace("\\n", "\n")


def get_app_auth(app_id: str | int | None, private_key: str | None):
    if not app_id:
        raise RuntimeError("GITHUB_APP_ID is not configured")
    return Auth.AppAuth(str(app_id), load_private_key(private_key))


def get_installation_client(app_id: str | int | None, private_key: str | None, installation_id: str | int):
    app_auth = get_app_auth(app_id, private_key)
    installation_auth = app_auth.get_installation_auth(int(installation_id))
    return Github(auth=installation_auth), installation_auth


def get_repo_for_installation(app_id: str | int | None, private_key: str | None, installation_id: str | int, repo_name: str):
    gh, installation_auth = get_installation_client(app_id, private_key, installation_id)
    return gh.get_repo(repo_name), installation_auth


def get_integration(app_id: str | int | None, private_key: str | None) -> GithubIntegration:
    return GithubIntegration(auth=get_app_auth(app_id, private_key))
