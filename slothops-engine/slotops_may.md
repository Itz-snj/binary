# SlothOps — May 2026 Walkthrough

This document is a snapshot of the SlothOps engine as of May 2026. It
covers current architecture, the end-to-end flow, how to bring the stack
up locally with Docker, and how to verify it works.

For deeper, historical implementation notes, see `docs/archive/KT.md`.

---

## 1. Current Status

The engine has been overhauled in two passes:

1. **Database**: SQLite → PostgreSQL (asyncpg + Alembic migrations).
2. **Application layout**: monolithic `main.py` (~1000 LOC) → routers
   under `app/api/`, services under `app/services/`, view models under
   `app/schemas/`, shared config/auth helpers under `app/core/`.
3. **Dashboard**: server-rendered vanilla HTML in `static/` → a React
   18 + TypeScript SPA under `web/` (Vite, TanStack Query, React Router).

What's done:

- 42 HTTP routes registered, split across these routers:
  - `app/api/auth.py` — signup/login (legacy + `/api/auth/*` paths), session, workspaces.
  - `app/api/dashboard.py` — `/api/dashboard/{overview,activity,metrics,repos,health}`.
  - `app/api/health.py` — `/health`, `/api/health/engine`, `/api/health/llm`.
  - `app/api/qa.py` — QA reports list/detail, bypass, AI-driven resolve.
  - `app/api/repos.py` — repo listing, policy upsert, preflight checks.
  - `app/api/rollbacks.py` — rollback queue + operator approval.
  - `app/api/webhooks.py` — Sentry + GitHub webhook receivers.
- `main.py` is now ~150 LOC; remaining inline handlers are
  `/issues*`, `/api/audit-events`, `/api/developer-config`,
  `/api/github/link`, `/api/integrations/status`, `/stream`, and the
  React SPA serving routes.
- Multi-stage Dockerfile and `docker compose up`-ready stack.

What's still owed (future work, not blocking):

- Move the remaining inline handlers in `main.py` into their own
  routers (`issues`, `audit`, `integrations`, `streams`, `config`).
- Flesh out the React pages beyond `Overview` and `Login` (the others
  are placeholders that exist to keep the router happy).

---

## 2. Repo Layout

```
slothops-engine/
├── main.py                    FastAPI entry. Lifespan, SSE log bridge,
│                              SPA serving, router wiring.
├── app/                       New layered app code.
│   ├── api/                   Routers (one per resource).
│   ├── core/                  config.py, security.py, deps.py.
│   ├── services/              Aggregation / business logic above CRUD.
│   └── schemas/               Pydantic view models for the dashboard.
│
├── pipeline.py                Sentry-issue remediation orchestrator.
├── qa_pipeline.py             Post-PR QA runner.
├── qa_agents/                 Six QA agents (static, functionality,
│                              regression, performance, stress, vapt).
├── qa_resolution.py           LLM-driven auto-fix for failed QA runs.
├── rollback.py                Plan / execute production rollbacks.
├── resolution.py              Re-cycle rollback PRs on deploy failure.
│
├── llm_fixer.py               Fix-generation prompt + retry logic.
├── classifier.py              Code / infra / dependency / unknown.
├── code_fetcher.py            Pull source context from GitHub.
├── genai_client.py            LLM provider fallback chain.
├── github_app.py              GitHub App auth + repo handles.
├── github_automation.py       PR creation, review comments.
├── sentry_parser.py           Sentry webhook → IssueRecord + frames.
├── webhook_security.py        HMAC signature verification.
├── sse_manager.py             In-process pub/sub for SSE.
├── policy.py                  Per-repo policy resolution.
├── models.py                  Pydantic models + enums.
│
├── database.py                Compatibility facade. All call-sites
│                              go through here.
├── db/                        Actual data layer.
│   ├── engine.py              async SQLAlchemy engine factory.
│   ├── crud.py                Per-model query helpers.
│   └── models.py              SQLModel ORM definitions.
├── alembic/                   Migrations.
│
├── web/                       React dashboard (Vite + TS).
│   ├── src/api/               API client.
│   ├── src/app/               App shell + router.
│   ├── src/pages/             Page components.
│   └── src/lib/               apiFetch helper, token storage.
│
├── docker-compose.yml         Postgres + engine.
├── Dockerfile                 Multi-stage: bun build → python runtime.
├── alembic.ini                Migration config.
├── requirements.txt           Python deps.
└── docs/archive/              Historical KT notes.
```

---

## 3. End-to-End Flow

There are four distinct flows the engine handles. Each one starts at a
webhook or a dashboard action and ends with a verifiable artifact in
GitHub or the database.

### 3.1 Sentry issue → fix PR

```
Sentry webhook
   │
   ▼
POST /webhook/sentry/{workspace_id}                     app/api/webhooks.py
   │  - HMAC verify (per-workspace secret)
   │  - parse_sentry_webhook → IssueRecord + CallFrame[]
   │  - resolve repo_config via sentry_project_slug
   │
   ▼ asyncio.create_task
run_pipeline(issue)                                            pipeline.py
   │  redact → fingerprint → dedupe check
   │  classify (code | infra | dependency | unknown)
   │  fetch_code_context (or fetch_deep for high confidence)
   │  generate_fix via llm_fixer
   │  create_fix_pr via github_automation
   │
   ▼
Issue status: PR_CREATED
PR appears on the target repo with the proposed patch.
```

Every stage updates the issue row and broadcasts an `issue_update` SSE
event so the dashboard can paint progress live.

### 3.2 Human/bot PR → QA report

```
GitHub webhook: pull_request opened|synchronize
   │
   ▼
POST /webhook/github                                    app/api/webhooks.py
   │  - HMAC verify
   │  - sender bot?  →  run QA only
   │    sender human? →  handle_human_pr_review  +  delayed QA (5s)
   │
   ▼
run_qa_pipeline(pr)                                          qa_pipeline.py
   │  triage  (qa_triage.py → required vs advisory agents)
   │  fan-out:
   │     static_analysis · functionality · regression
   │     performance     · stress_test  · vapt
   │  aggregate verdict → QAReport row
   │  set GitHub commit status (success | failure)
   │
   ▼
QA report visible at /api/qa-reports/{id} and on the dashboard.
```

If QA fails, the operator can:

- `POST /api/qa-bypass/{id}` — manual override, marks status `bypassed`
  and flips the commit status to success.
- `POST /api/qa-resolve/{id}` — kicks `qa_resolution.py`, which reads
  the failing agents' logs, asks the LLM for fixes, and commits them
  back to the PR branch. The push triggers a new QA cycle.

### 3.3 Deploy failure → rollback

```
GitHub webhook: deployment_status (state: failure|error)
   │
   ▼
POST /webhook/github                                    app/api/webhooks.py
   │  - if deployment ref is a SlothOps backup branch:
   │       → attempt_resolution (re-cycle the fix)
   │    else:
   │       → plan_rollback                                     rollback.py
   │
   ▼
plan_rollback
   │  determine last-known-good SHA
   │  consult repo policy (mode + strategy)
   │  - APPROVAL_REQUIRED   →  RollbackRecord(status=pending_approval)
   │  - AUTO_REVERT         →  execute_rollback immediately
   │
   ▼ (if approval needed)
POST /api/rollbacks/{id}/approve                       app/api/rollbacks.py
   │
   ▼
execute_rollback                                              rollback.py
   - DIRECT_REVERT  →  force-push revert commit
   - ROLLBACK_PR    →  open a PR with the revert + tracking branch
```

### 3.4 Dashboard reads

```
React (web/) →  /api/* (proxied :5173 → :8000 in dev)
                /stream (SSE) for live issue / log updates
                /api/dashboard/overview drives the home page
```

---

## 4. Local Spin-Up (Docker)

### 4.1 Prerequisites

- Docker Desktop 27+ (with Compose v2).
- A `.env` file at the repo root (copy from `.env.example`).
- Optional: a GitHub App + Sentry webhook secret if you want to drive
  the full pipeline. None of the LLM keys are mandatory — the engine
  will skip providers that don't have a key.

### 4.2 One-command bring-up

```bash
docker compose up --build
```

What happens:

1. Postgres 16 starts and the healthcheck waits until it accepts
   connections.
2. The engine image builds in two stages:
   - **web-builder** — `oven/bun:1.1-alpine` installs `web/package.json`
     and runs `bun run build`, producing `/web/dist`.
   - **runtime** — `python:3.13-slim`, installs `requirements.txt`,
     copies the engine source, and pulls `web/dist` from stage 1.
3. The container's `CMD` runs `alembic upgrade head` and then launches
   `uvicorn main:app --host 0.0.0.0 --port 8000`.

You should see roughly:

```
slothops_postgres  | database system is ready to accept connections
slothops_engine    | INFO Initialising database...
slothops_engine    | INFO SlothOps engine ready 🦥
slothops_engine    | INFO Uvicorn running on http://0.0.0.0:8000
```

Open <http://localhost:8000> to load the React dashboard. The OpenAPI
docs are at <http://localhost:8000/docs>.

### 4.3 Verifying the stack

```bash
# Liveness
curl -s http://localhost:8000/health

# Sign up and grab a token
curl -s -X POST http://localhost:8000/api/auth/signup \
  -H 'content-type: application/json' \
  -d '{"email":"you@example.com","password":"hunter2","workspace_name":"demo"}'

# Use the token
export TOKEN=...
curl -s http://localhost:8000/api/dashboard/overview \
  -H "authorization: Bearer $TOKEN"
```

### 4.4 Dev mode (no Docker for the engine)

Useful if you want fast reloads on the Python side. Postgres still
runs in Docker.

```bash
# In one shell — DB only
docker compose up -d postgres

# In another shell — engine
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000

# In a third shell — React (Vite dev server proxies to :8000)
cd web
bun install
bun run dev          # http://localhost:5173
```

### 4.5 Database migrations

Alembic targets `DIRECT_DATABASE_URL` (psycopg sync driver). In Docker
this happens automatically on container start. Locally:

```bash
alembic upgrade head             # apply
alembic revision --autogenerate -m "msg"  # add a new migration
alembic downgrade -1             # roll back the latest
```

### 4.6 Useful URLs

| URL | What |
|---|---|
| `http://localhost:8000/` | React dashboard |
| `http://localhost:8000/docs` | OpenAPI Swagger UI |
| `http://localhost:8000/health` | Engine liveness |
| `http://localhost:8000/stream?token=...` | SSE log + issue events |
| `http://localhost:8000/webhook/sentry/{ws}` | Sentry webhook receiver |
| `http://localhost:8000/webhook/github` | GitHub App webhook receiver |
| `http://localhost:5173/` | React dev server (when run on host) |
| `postgres://slothops:slothops_dev@localhost:5432/slothops` | Postgres |

---

## 5. Configuration Reference

Only the variables you're likely to touch. See `.env.example` for the
full list.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | asyncpg URL for runtime queries |
| `DIRECT_DATABASE_URL` | psycopg URL for Alembic |
| `GITHUB_APP_ID` | GitHub App ID |
| `GITHUB_APP_PRIVATE_KEY` | PEM contents *or* path to a `.pem` file |
| `GITHUB_WEBHOOK_SECRET` | HMAC secret for `/webhook/github` |
| `JWT_SECRET` | Signing key for dashboard JWTs |
| `BASE_URL` | Public URL (used when telling Sentry the webhook path) |
| `LLM_PROVIDER_CHAIN` | Comma-separated list, tried in order |
| `*_API_KEY` (Groq, Together, …) | One per provider; absent = skipped |

The compose file pins `DATABASE_URL` and `DIRECT_DATABASE_URL` to the
internal Postgres service (`postgres:5432`); everything else is read
from your host `.env`.

---

## 6. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `alembic upgrade head` errors in the engine container | Postgres healthcheck didn't pass before engine started — restart with `docker compose up --build --force-recreate` |
| Engine boots but dashboard is blank | The web-builder stage failed silently. `docker compose build --no-cache engine` and watch the bun build logs |
| `401 Invalid token` on every request | `JWT_SECRET` changed between sessions — log out and log in again |
| `Could not fetch repos for workspace` | `GITHUB_APP_ID` / `GITHUB_APP_PRIVATE_KEY` not set, or the App isn't installed on the org |
| Sentry webhook returns 401 | `SENTRY_WEBHOOK_SECRET` (per-workspace, stored in the `Integration` row) doesn't match the signature header |

---

## 7. What was Removed in this Pass

The following files were retired because the React dashboard, Postgres,
and the new layered layout supersede them:

- `static/` (the old vanilla-JS dashboard)
- `slothops.db` (legacy SQLite)
- `server.log` (stale uvicorn log)
- `tests/task.md` (planning checklist)
- `Procfile` (Heroku-style, replaced by `docker compose`)
- `SlothOps.postman_collection.json` (Swagger at `/docs` covers it)
- `__pycache__/`, `.pytest_cache/` (build artifacts; gitignored)

Historical notes moved to `docs/archive/`.
