# SlothOps — Developer Guide

Everything a contributor needs to understand, extend, and run the engine. This guide covers the complete file/folder structure, how each of the four pipeline flows works at the code level, and how to safely add new features.

---

## Table of Contents

1. [Codebase Tour](#1-codebase-tour)
2. [Database Layer](#2-database-layer)
3. [Pipeline Flows — Deep Dive](#3-pipeline-flows--deep-dive)
4. [How to Add a New Feature](#4-how-to-add-a-new-feature)
5. [Testing](#5-testing)
6. [Open Source Contribution Guide](#6-open-source-contribution-guide)

---

## 1. Codebase Tour

Every Python file lives under `app/`. `main.py` at the repo root is the only exception — it is the FastAPI entrypoint and nothing else.

### `main.py` — FastAPI entrypoint

| Responsibility | Detail |
|---|---|
| App creation | Creates the `FastAPI` instance, registers routers |
| Lifespan | `create_all_tables()` on startup |
| SSE bridge | `/stream` endpoint; publishes `sse_manager` events to clients |
| SPA serving | Serves `web/dist/index.html` and `web/dist/assets/*` |
| Inline handlers | A handful of routes not yet split into routers: `/issues*`, `/api/audit-events`, `/api/developer-config`, `/api/github/link`, `/api/integrations/status` |

---

### `app/api/` — HTTP Routers

One file per resource. Each router is thin: it validates the request, calls a service or pipeline function, and returns a response.

| File | Prefix | What it does |
|---|---|---|
| `auth.py` | `/api/auth`, `/login`, `/signup` | Signup, login (form + JSON), session info, workspace list |
| `dashboard.py` | `/api/dashboard` | Aggregated overview, activity, metrics, repo cards, health |
| `health.py` | `/health`, `/api/health` | Liveness, engine, LLM probe |
| `qa.py` | `/api/qa-reports` | List/detail, bypass, LLM-driven resolve |
| `repos.py` | `/api/repos` | Repo list, policy upsert, preflight check |
| `rollbacks.py` | `/api/rollbacks` | Queue list, detail, operator approval |
| `webhooks.py` | `/webhook` | Sentry + GitHub inbound event receivers |

---

### `app/core/` — Shared Plumbing

| File | Purpose |
|---|---|
| `config.py` | `load_settings()` — reads env vars into a `Settings` dataclass. Single source of truth for configuration. |
| `security.py` | `get_current_workspace` FastAPI dependency — validates JWT and returns the workspace ID. `oauth2_scheme` token extractor. |
| `deps.py` | Re-exports `load_settings` for convenience. |

---

### `app/services/` — Business Logic

Aggregation and logic that belongs above the CRUD layer but below the HTTP layer.

| File | Purpose |
|---|---|
| `dashboard_service.py` | Builds the dashboard overview, repo cards, activity feed, metrics, and health payload by querying `app.database`. |
| `auth_service.py` | Token creation helpers used by the auth router. |
| `audit_service.py` | Writes `AuditEvent` rows for significant state changes. |
| `repo_policy_service.py` | Effective policy resolution with workspace-level defaults. |

---

### `app/schemas/` — Pydantic View Models

Response shapes for the HTTP layer. Separate from the SQLModel ORM models in `app/db/models.py`.

| File | Contents |
|---|---|
| `dashboard.py` | `DashboardOverview`, `MetricCard`, `RepoCard`, `ActivityItem`, `HealthStatus` |
| `auth.py` | `SignupRequest`, `AuthSession` |
| `repos.py` | `RepoPolicyRequest`, `PreflightResult` |

---

### `app/models.py` — Domain Types

Pydantic models and Python enums shared across the entire codebase. These are **not** SQLModel ORM models — they are the in-memory domain types used by pipelines, parsers, and LLM modules.

Key types: `IssueRecord`, `CallFrame`, `LLMFixResponse`, `BuildFixResponse`, `QAReport`, `QATriageResult`, `IssueStatus`, `QAStatus`, `RollbackStatus`, `RollbackMode`, `RollbackStrategy`, `DedupeAction`, `Classification`, `AuditAction`, `AuditEvent`.

---

### `app/db/` — Data Layer

| File | Purpose |
|---|---|
| `models.py` | SQLModel ORM table definitions: `User`, `Workspace`, `RepoConfig`, `IssueRecord` (persisted), `QAReport`, `RollbackRecord`, `ResolutionRecord`, `AuditEvent`, `Integration`. Uses JSONB columns via SQLAlchemy dialects. |
| `crud.py` | Per-model async query helpers. Uses `session.exec()` (SQLModel) and `session.execute()` (SQLAlchemy) depending on the query type. |
| `engine.py` | Creates the async SQLAlchemy engine, `async_session_factory`, and the `get_session()` FastAPI dependency. Uses `asyncpg` driver. |
| `__init__.py` | Re-exports `engine`, `get_session`, `async_session_factory`, and `crud`. |

---

### `app/database.py` — Facade

A thin facade over `app.db.crud`. Every call-site in the codebase does `from app import database as db` and calls `db.upsert_issue()`, `db.list_issues()`, etc. This keeps the CRUD function signatures stable even if the underlying storage changes.

---

### `app/auth.py` — JWT + Passwords

`create_access_token()`, `verify_token()`, `hash_password()`, `verify_password()`. Backed by `python-jose` and `bcrypt`. No FastAPI dependency injection here — pure functions called by the auth router and `app/core/security.py`.

---

### `app/sse_manager.py` — Server-Sent Events

An in-process pub/sub broker. `broadcast(event_type, data)` sends a JSON event to all active SSE subscribers. `subscribe()` yields events as an async generator. The `/stream` endpoint in `main.py` wires these together.

Issues and pipeline stages call `broadcast("issue_update", {...})` so the React dashboard can paint progress live without polling.

---

### `app/policy.py` — Repo Policy

`get_effective_policy(workspace_id, repo_full_name)` returns the merged policy for a repo: workspace-level defaults overridden by repo-specific settings. The `RepoConfig` row in the database holds `auto_fix_enabled`, `qa_required`, `rollback_mode`, `rollback_strategy`, and `max_fix_attempts`.

---

### `app/pipelines/` — Orchestrators

| File | Triggered by | What it does |
|---|---|---|
| `pipeline.py` | `run_pipeline(issue)` called from webhooks | Sentry issue → fix PR. Full flow: redact → fingerprint → dedupe → classify → fetch context → LLM fix → create PR. |
| `qa_pipeline.py` | `run_qa_pipeline(pr)` called from webhooks | PR → QA report. Triage → fan-out 6 agents → aggregate → set commit status. |
| `qa_triage.py` | Called by `qa_pipeline.py` | Returns `QATriageResult` — which agents are required vs advisory for this repo's detected stack. |
| `qa_resolution.py` | `POST /api/qa-resolve/{id}` | Reads failing agent logs → LLM generates fixes → pushes to PR branch. |
| `rollback.py` | `plan_rollback()` and `execute_rollback()` called from webhooks + approval endpoint | Plans (finds last-good SHA, checks policy) and executes (force-push revert or rollback PR) rollbacks. |
| `resolution.py` | `attempt_resolution()` called from webhooks | Re-cycles a SlothOps fix PR when the deployment fails — tries to rebuild/re-fix rather than rolling back. |

---

### `app/integrations/` — External APIs

| File | Purpose |
|---|---|
| `github_app.py` | GitHub App auth using installation tokens. `get_repo_for_installation(installation_id, repo_full_name)` returns a PyGithub `Repository` handle. |
| `github_automation.py` | `create_fix_pr()` — commits file changes to a new branch and opens a PR. `post_qa_report_comment()` — posts a QA summary as a PR comment. |
| `sentry_parser.py` | `parse_sentry_webhook(payload)` — extracts `IssueRecord` and `CallFrame[]` from a Sentry webhook payload. |
| `webhook_security.py` | `verify_github_signature()`, `verify_sentry_signature()`, `extract_github_delivery_id()` — HMAC-SHA256 verification for inbound webhooks. |
| `email_sender.py` | `send_qa_report_email()`, `send_rollback_notification_email()`, `send_resolution_notification_email()` — SMTP notifications. No-op when SMTP env vars are absent. |

---

### `app/llm/` — LLM Glue

| File | Purpose |
|---|---|
| `client.py` | `generate_with_fallback(prompt)` — iterates the `LLM_PROVIDER_CHAIN`, calls each provider's HTTP API, falls back on failure. `health_check()` probes all configured providers. |
| `fixer.py` | `generate_fix(issue, code_context)` — constructs the fix prompt and parses the `LLMFixResponse`. `generate_infra_recommendation()` for infra-classified issues. `extract_json_object()` — robust JSON extraction from LLM output. |
| `classifier.py` | `classify(issue)` — returns `Classification` enum: `code / infra / dependency / unknown`. |
| `code_reviewer.py` | Advisory code review (not yet wired into a live flow). |
| `style_reviewer.py` | Advisory style review (not yet wired). |
| `pr_insights.py` | Advisory PR summary generation (not yet wired). |

---

### `app/code_analysis/` — Code-Understanding Utilities

| File | Purpose |
|---|---|
| `code_fetcher.py` | `fetch_code_context()` and `fetch_deep_code_context()` — pull source files from GitHub using the CallFrame paths. |
| `fingerprint.py` | `compute_fingerprint()` — deterministic hash of issue + stack trace. `check_dedup()` — returns `DedupeAction` (process / skip / re-trigger after cooldown). |
| `redactor.py` | `redact(text)` — strips secrets, tokens, and PII before sending to an LLM. |
| `stack_detector.py` | `detect_stack(repo_dir)` — infers language + framework from files in the repo directory. |
| `build_fixer.py` | `generate_build_fix()` — heuristic + LLM approach for build/CI errors. |
| `command_runner.py` | `run_command(cmd, cwd)` — thin subprocess wrapper used by QA agents. |
| `deployment_logs.py` | `fetch_deployment_logs()` — pulls GitHub Actions workflow run logs for a deployment. |
| `call_chain.py` | Advisory call-chain tracing (not yet wired into a live flow). |

---

### `app/qa_agents/` — Six QA Agents

Each agent exposes a single async function `run_<name>(pr_url, repo_dir) -> {"passed": bool, "log": str}`.

| Agent | What it checks |
|---|---|
| `static_analysis.py` | Linting, type errors, known anti-patterns |
| `functionality.py` | Unit and integration test pass rate |
| `regression.py` | Tests that were previously passing still pass |
| `performance.py` | Response times and memory benchmarks |
| `stress_test.py` | Behaviour under concurrent load |
| `vapt.py` | Known vulnerability patterns (OWASP top-10 heuristics) |

---

## 2. Database Layer

### ORM models (`app/db/models.py`)

All tables use `SQLModel` with PostgreSQL-specific JSONB columns for flexible data (agent logs, stack frames, audit payloads).

```
User           ←── many ──→ Workspace
Workspace      ←── many ──→ RepoConfig
                            IssueRecord
                            QAReport
                            RollbackRecord
                            ResolutionRecord
                            AuditEvent
                            Integration
```

### Migrations

```bash
# Generate a migration after changing app/db/models.py
alembic revision --autogenerate -m "describe change"

# Apply
alembic upgrade head

# Roll back one
alembic downgrade -1
```

`alembic/env.py` imports `app.db.models` as a side effect to register all tables with `SQLModel.metadata` before autogenerate runs.

### Session pattern

```python
from app.db.engine import get_session
from sqlmodel.ext.asyncio.session import AsyncSession

# In a FastAPI route:
async def my_route(session: AsyncSession = Depends(get_session)):
    result = await session.exec(select(MyModel).where(...))
    ...

# In a pipeline (no DI):
async with async_session_factory() as session:
    result = await session.exec(...)
```

**Important:** always use `AsyncSession` from `sqlmodel.ext.asyncio.session`, not from `sqlalchemy.ext.asyncio`. SQLAlchemy's `AsyncSession` lacks the `.exec()` method used throughout `app/db/crud.py`.

---

## 3. Pipeline Flows — Deep Dive

### 3.1 Sentry Issue → Fix PR

Entry point: `app/api/webhooks.py` → `POST /webhook/sentry/{workspace_id}`

```
parse_sentry_webhook()          app/integrations/sentry_parser.py
    ↓
check_dedup()                   app/code_analysis/fingerprint.py
    → DedupeAction.SKIP         (already seen within cooldown window)
    → DedupeAction.PROCESS      (new or retriggerable)
    ↓
asyncio.create_task(
    run_pipeline(issue)         app/pipelines/pipeline.py
)
    ↓
redact(issue)                   app/code_analysis/redactor.py
classify(issue)                 app/llm/classifier.py
    → code / infra / dependency / unknown
    ↓
fetch_code_context()            app/code_analysis/code_fetcher.py
    (or fetch_deep_code_context for high-confidence code issues)
    ↓
generate_fix() / generate_infra_recommendation()
                                app/llm/fixer.py
    → LLMFixResponse
    ↓
create_fix_pr()                 app/integrations/github_automation.py
    → PR URL
    ↓
issue.status = PR_CREATED
broadcast("issue_update", ...)  app/sse_manager.py
```

Every stage persists the issue row and broadcasts an SSE event. If any step raises, the issue is marked `ERROR`.

---

### 3.2 Pull Request → QA Report

Entry point: `app/api/webhooks.py` → `POST /webhook/github` (event: `pull_request`)

```
verify_github_signature()
    ↓
sender is SlothOps bot?
    Yes → run_qa_pipeline() immediately
    No  → handle_human_pr_review() + asyncio.create_task(run_qa_pipeline(), delay=5s)
    ↓
triage_pr(pr)                   app/pipelines/qa_triage.py
    → QATriageResult(required=[], advisory=[])
    ↓
asyncio.gather(
    run_static_analysis(),
    run_functionality_tests(),
    run_regression_tests(),
    run_performance_check(),
    run_stress_test(),
    run_vapt_scan(),
)                               app/qa_agents/*
    ↓
aggregate: all required agents passed?
    → QAReport(status=passed/failed)
    ↓
post_qa_report_comment()        app/integrations/github_automation.py
set GitHub commit status
```

---

### 3.3 Deploy Failure → Rollback

Entry point: `app/api/webhooks.py` → `POST /webhook/github` (event: `deployment_status` failure)

```
is this a SlothOps backup branch deployment?
    Yes → attempt_resolution()  app/pipelines/resolution.py
    No  ↓
plan_rollback(workspace_id, repo, sha)
                                app/pipelines/rollback.py
    ↓
find last-known-good SHA
get_effective_policy()
    → mode = AUTO_REVERT        execute_rollback() immediately
    → mode = APPROVAL_REQUIRED  RollbackRecord(status=pending_approval)
                                broadcast("rollback_update", ...)
    ↓ (after operator POSTs /api/rollbacks/{id}/approve)
execute_rollback()
    strategy = DIRECT_REVERT    force-push revert commit to main
    strategy = ROLLBACK_PR      open a PR with the revert
```

---

### 3.4 QA Failure → Auto-Resolve

Entry point: `app/api/qa.py` → `POST /api/qa-resolve/{id}`

```
load QAReport
    ↓
qa_resolution.py: resolve_qa_failure(report)
    ↓
for each failed agent:
    build structured prompt with agent name + failure log
    ↓
generate_with_fallback(prompt)  app/llm/client.py
    → corrective commit plan
    ↓
extract_json_object()           app/llm/fixer.py
    ↓
for each file in fix plan:
    commit file to PR branch    GitHub API
    ↓
new push → GitHub fires pull_request synchronize webhook
    → new QA cycle starts automatically
```

---

## 4. How to Add a New Feature

### Add a new HTTP endpoint

1. **Pick or create a router** in `app/api/`. Keep routers thin — one function per endpoint.

```python
# app/api/my_resource.py
from fastapi import APIRouter, Depends
from app.core.security import get_current_workspace
from app.services import my_service
from app.schemas.my_resource import MyResponse

router = APIRouter(prefix="/api/my-resource", tags=["my-resource"])

@router.get("/{id}", response_model=MyResponse)
async def get_item(id: str, workspace_id: str = Depends(get_current_workspace)):
    return await my_service.get_item(workspace_id, id)
```

2. **Add business logic** in `app/services/my_service.py`.

3. **Add a response schema** in `app/schemas/my_resource.py` (Pydantic `BaseModel`).

4. **Register the router** in `main.py`:

```python
from app.api.my_resource import router as my_resource_router
app.include_router(my_resource_router)
```

---

### Add a new QA agent

1. Create `app/qa_agents/my_agent.py`:

```python
import logging

log = logging.getLogger("slothops.qa.my_agent")

async def run_my_agent(pr_url: str, repo_dir: str) -> dict:
    try:
        # ... your check ...
        return {"passed": True, "log": "All checks passed."}
    except Exception as e:
        return {"passed": False, "log": str(e)}
```

2. Import and call it in `app/pipelines/qa_pipeline.py` alongside the existing agents:

```python
from app.qa_agents.my_agent import run_my_agent

# Inside run_qa_pipeline():
results = await asyncio.gather(
    run_static_analysis(pr_url, repo_dir),
    run_my_agent(pr_url, repo_dir),
    ...
)
```

3. If the agent should be advisory (not required) for some stacks, update the `triage_pr()` logic in `app/pipelines/qa_triage.py`.

---

### Add a new LLM provider

All providers are defined in `app/llm/client.py` as `ProviderConfig` entries:

```python
# app/llm/client.py

@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str
    model: str
    headers: dict = field(default_factory=dict)

PROVIDERS = [
    ProviderConfig(
        name="myprovider",
        base_url="https://api.myprovider.ai/v1",
        api_key_env="MYPROVIDER_API_KEY",
        model="my-model-name",
    ),
    # ... existing providers ...
]
```

Then add the key to `.env.example` and to `LLM_PROVIDER_CHAIN` in your `.env`.

---

### Add a database model

1. Define the table in `app/db/models.py`:

```python
class MyTable(SQLModel, table=True):
    __tablename__ = "my_table"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    workspace_id: str = Field(index=True)
    data: dict = Field(default={}, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

2. Add CRUD helpers in `app/db/crud.py`.

3. Expose them through `app/database.py` (the facade).

4. Generate and apply the migration:

```bash
alembic revision --autogenerate -m "add my_table"
alembic upgrade head
```

---

### Add a new pipeline

1. Create `app/pipelines/my_pipeline.py` with an async entry-point function.

2. Wire it in `app/api/webhooks.py` (if webhook-triggered) or a new router (if operator-triggered).

3. Use `asyncio.create_task(my_pipeline(data))` to run it in the background so the HTTP response returns immediately.

4. Call `broadcast("my_event", {...})` from `app.sse_manager` at each stage for live dashboard updates.

---

## 5. Testing

```bash
source venv/bin/activate
pytest -x tests/                              # stop on first failure

# Skip tests that need a live Postgres:
pytest --ignore=tests/test_database_repo_config.py \
       --ignore=tests/test_rollback_approval.py \
       --ignore=tests/test_sentry_repo_resolution.py \
       tests/

# Run a specific file:
pytest tests/test_classifier.py -v
```

### Test organisation

| File | What it covers |
|---|---|
| `test_classifier.py` | LLM classifier label assignment |
| `test_fingerprint.py` | Dedup key computation and cooldown logic |
| `test_redactor.py` | PII and secret stripping |
| `test_sentry_parser.py` | Sentry webhook → IssueRecord parsing |
| `test_webhook_security.py` | HMAC signature verification |
| `test_policy.py` | Policy merge logic |
| `test_llm_fixer_async.py` | JSON extraction from LLM output |
| `test_genai_client.py` | Provider chain configuration |
| `test_qa_pipeline.py` | QA agent fan-out (async, DB-optional) |
| `test_qa_triage.py` | Triage decision logic |
| `test_database_repo_config.py` | CRUD round-trip (requires Postgres) |
| `test_rollback_approval.py` | Rollback state machine (requires Postgres) |
| `test_runner.py` | Smoke test helper imported at runtime by `pipeline.py` |

### Writing new tests

- Tests that only exercise pure logic (no DB, no network) can use plain `pytest` — no fixtures needed.
- Tests that need a database should connect to `DATABASE_URL` from the environment and call `create_all_tables()` in a fixture.
- Avoid mocking the database in integration tests — use a real Postgres instance (the `docker compose up -d postgres` target works well in CI).

---

## 6. Open Source Contribution Guide

### Guiding principles

- **No half-finished implementations.** A PR that adds a feature should include the wiring, the test, and the schema update. Stubs and `TODO` comments belong in issues, not in merged code.
- **No compatibility shims.** When you rename or move something, update all call-sites. The codebase uses the `app.*` namespace cleanly; keep it that way.
- **Prefer editing over creating.** Before adding a new file, check whether an existing module should absorb the logic.
- **One concern per PR.** A PR that adds a QA agent shouldn't also refactor the rollback flow.

### Branching convention

```
feat/<short-description>    New feature
fix/<short-description>     Bug fix
refactor/<description>      Code reorganisation without behaviour change
docs/<description>          Documentation only
```

### Commit messages

Use the imperative mood, present tense. Describe the *why*, not the *what*:

```
Add VAPT agent timeout to prevent CI hangs
Fix fingerprint cooldown ignoring UTC offset
Refactor rollback policy resolution into repo_policy_service
```

### PR checklist

- [ ] `pytest -x tests/` passes locally
- [ ] New functionality has at least one test
- [ ] `.env.example` updated if a new env var was added
- [ ] `slotops_may.md` updated if the layout changed
- [ ] No `print()` statements — use `logging.getLogger("slothops.<module>")`

### Reporting bugs

Open an issue with:
1. What you expected to happen
2. What actually happened (paste the relevant log lines)
3. How to reproduce it (minimal curl / webhook payload)
4. Engine version (`git rev-parse --short HEAD`) and Python version

### Roadmap / good first issues

- Move the remaining inline handlers in `main.py` into routers (`issues`, `audit`, `integrations`, `streams`, `config`)
- Flesh out the React pages beyond `Overview` and `Login` (QA, Rollbacks, Repos, Audit, Settings are placeholder stubs)
- Add the three advisory LLM modules (`code_reviewer`, `style_reviewer`, `pr_insights`) into a live flow
- Wire `call_chain.py` into the code context fetcher for deeper stack analysis
- Add a proper test fixture for Postgres using `pytest-asyncio` and `testcontainers`
