import hashlib
import hmac
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app import database as db
from app.integrations.webhook_security import extract_github_delivery_id, verify_github_signature


def test_github_signature_valid():
    body = b'{"ok":true}'
    secret = "topsecret"
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_github_signature(body, sig, secret)


def test_github_signature_invalid():
    assert not verify_github_signature(b"{}", "sha256=bad", "topsecret")


def test_signature_disabled_without_secret():
    assert verify_github_signature(b"{}", None, None)


def test_extract_delivery_id():
    assert extract_github_delivery_id({"x-github-delivery": "abc"}) == "abc"


@pytest.mark.asyncio
async def test_duplicate_delivery_skip(tmp_path):
    db_path = str(tmp_path / "slothops.db")
    await db.init_db(db_path)

    assert await db.record_webhook_delivery("delivery-1", "pull_request", "ws1", "org/repo", db_path)
    assert not await db.record_webhook_delivery("delivery-1", "pull_request", "ws1", "org/repo", db_path)
