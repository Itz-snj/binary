"""Webhook verification helpers."""

from __future__ import annotations

import hashlib
import hmac
from typing import Mapping


def verify_github_signature(raw_body: bytes, signature_header: str | None, secret: str | None) -> bool:
    if not secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def extract_github_delivery_id(headers: Mapping[str, str]) -> str:
    return headers.get("x-github-delivery") or headers.get("X-GitHub-Delivery") or ""


def verify_sentry_signature(raw_body: bytes, signature_header: str | None, secret: str | None) -> bool:
    """Stub-safe Sentry verification. Enforced only when a secret exists."""
    if not secret:
        return True
    if not signature_header:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
