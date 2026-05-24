"""HTTP route groups (FastAPI routers).

Each module here owns one slice of the public API surface:
    auth.py        – signup / login / session
    dashboard.py   – overview, activity, metrics
    repos.py       – repo onboarding, policy, summaries
    qa.py          – QA reports, bypass, resolution
    rollbacks.py   – rollback queue, approvals
    webhooks.py    – inbound GitHub / Sentry webhooks
    health.py      – liveness + integration health
"""
