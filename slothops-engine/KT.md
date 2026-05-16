# SlothOps Engine - Knowledge Transfer (KT)

This document is the operating map for `slothops-engine/`. It intentionally
focuses on the engine and excludes the demo app.

SlothOps is evolving from a hackathon-style automation into a client-ready
agentic repo operations platform. For the near-term MVP, the strongest path is
to ship two production-facing modules first:

1. PR QA Gate - reviews pull requests, runs agentic QA, posts reports, and sets
   commit status.
2. Deployment Rollback + Self-Healing - reacts to failed production deployments,
   reverts the bad commit, opens a backup/fix path, and attempts auto-resolution.

The Sentry crash-to-PR pipeline still exists, but it is not the priority for the
client MVP described here.

---

## Current Architecture

```
GitHub App Webhooks
  |
  +-- pull_request opened/synchronize
  |     |
  |     +-- main.py
  |     +-- github_automation.handle_human_pr_review()
  |     +-- qa_pipeline.run_qa_pipeline()
  |     +-- qa_agents/*
  |     +-- database.qa_reports
  |     +-- GitHub commit status + PR comments
  |
  +-- deployment_status failure/error
        |
        +-- main.py
        +-- rollback.perform_rollback()
        +-- database.rollbacks
        +-- resolution.attempt_resolution()
        +-- database.resolutions
        +-- GitHub backup branch + auto-fix PR
```

The engine is a FastAPI service with SQLite persistence, GitHub App
authentication, a static dashboard, Server-Sent Events, and a multi-provider LLM
client.

---

## Runtime Entry Point

### `main.py`

Owns the FastAPI app and all HTTP endpoints.

Important responsibilities:

- Starts database setup in the lifespan hook via `database.init_db()`.
- Serves the dashboard from `static/index.html`.
- Handles auth routes:
  - `POST /api/signup`
  - `POST /api/login`
  - JWT workspace extraction through `get_current_workspace()`.
- Handles GitHub App installation linking:
  - `POST /api/github/link`
  - `POST /webhook/github` installation events.
- Handles PR webhooks:
  - Human PRs trigger style/architecture review plus delayed QA.
  - SlothOps bot PRs skip review and run QA only.
- Handles deployment failure webhooks:
  - `deployment_status` with `failure` or `error` triggers rollback.
  - Failures on `slothops/backup-*` branches trigger another resolution attempt.
- Exposes dashboard APIs:
  - `/issues`
  - `/api/qa-reports`
  - `/api/rollbacks`
  - `/api/integrations/status`
  - `/api/developer-config`
  - `/api/qa-bypass/{report_id}`
  - `/api/qa-resolve/{report_id}`

Client MVP note:
`main.py` is currently doing too much. Before production use, split route groups
into `routes/auth.py`, `routes/github_webhooks.py`, `routes/qa.py`, and
`routes/rollbacks.py`.

---

## Data Model

### `models.py`

Single source of truth for Pydantic models and enum values.

Core models:

- `User`, `Workspace`, `WorkspaceUser`, `Integration`
  - Multi-tenant SaaS basics.
- `IssueRecord`
  - Used by the Sentry remediation pipeline.
- `QAReport`
  - Stores one QA run per PR/SHA.
- `RollbackRecord`
  - Stores production rollback events.
- `ResolutionRecord`
  - Stores auto-resolution attempts after rollback.
- `LLMFixResponse`, `FileChange`
  - Structured code generation output.

Important statuses:

- QA: `passed`, `warning`, `failed`, `running`, `bypassed`
- Rollback: `pending`, `completed`, `failed`
- Resolution: `pending`, `fix_pushed`, `pr_opened`, `build_passed`,
  `build_failed`, `abandoned`

Client MVP note:
The DB schema is good enough for MVP, but production should move from SQLite to
Postgres and add migration tooling.

### `database.py`

Async SQLite persistence using `aiosqlite`.

Tables created:

- `users`
- `workspaces`
- `workspace_users`
- `integrations`
- `developer_configs`
- `issues`
- `qa_reports`
- `qa_configs`
- `rollbacks`
- `resolutions`

Key functions for the MVP:

- Workspace/auth:
  - `create_user()`
  - `get_user_by_email()`
  - `create_workspace()`
  - `add_user_to_workspace()`
  - `get_user_workspaces()`
- Integrations:
  - `get_integration()`
  - `upsert_integration()`
  - `get_workspace_by_installation_id()`
- QA:
  - `create_qa_report()`
  - `update_qa_report()`
  - `get_qa_reports()`
  - `get_qa_report()`
- Rollback/resolution:
  - `create_rollback()`
  - `update_rollback()`
  - `get_rollbacks()`
  - `get_rollback_by_backup_branch()`
  - `create_resolution()`
  - `update_resolution()`
  - `get_resolutions_for_rollback()`

Production hardening:

- Add workspace scoping to every lookup that exposes customer data.
- Add unique constraints for QA report IDs and rollback IDs where appropriate.
- Add migrations with Alembic before client deployment.
- Add indexes on `workspace_id`, `commit_sha`, `repo_name`, and
  `backup_branch`.

---

## GitHub Integration

### `github_automation.py`

Owns GitHub PR operations and review comments.

MVP-relevant functions:

- `handle_human_pr_review()`
  - Fetches changed PR files.
  - Runs style review if developer config exists.
  - Runs architecture/code review.
  - Posts results as PR comments.
- `post_qa_report_comment()`
  - Posts the QA report back to the PR.
- `post_style_review_comments()`
  - Posts style preference findings.
- `post_general_pr_comment()`
  - Posts architecture or code review output.
- `create_fix_pr()`
  - Used by Sentry remediation, not the MVP focus.

Production hardening:

- Standardize GitHub App auth. Some files use newer `Auth.AppAuth`; others use
  older `GithubIntegration(app_id, private_key)` / `get_access_token()` style.
- Always resolve the repository from webhook payload instead of "first installed
  repo".
- Verify GitHub webhook signatures.
- Make commit status context configurable, e.g. `SlothOps QA`.
- Avoid posting duplicate comments on synchronize events; update an existing bot
  comment when possible.

---

## PR QA Gate

### `qa_pipeline.py`

This is the main orchestrator for PR QA.

Trigger:

- GitHub webhook: `pull_request` event with `opened` or `synchronize`.

Current flow:

1. Resolve workspace from GitHub installation ID.
2. Authenticate as GitHub App installation.
3. Set GitHub commit status to `pending`.
4. Create `QAReport` with status `running`.
5. Clone repository to a temporary directory.
6. Checkout PR head SHA.
7. Detect stack with `stack_detector.detect_stack()`.
8. Install dependencies using detected install command.
9. Fetch PR changed files.
10. Ask LLM which QA tools to run.
11. Run selected QA agents.
12. Aggregate agent results into `passed`, `warning`, or `failed`.
13. Store report in DB.
14. Post PR comment.
15. Optionally send email.
16. Set GitHub commit status:
    - `success` for passed/warning
    - `failure` for failed

Current agents:

- `qa_agents/static_analysis.py`
- `qa_agents/functionality.py`
- `qa_agents/vapt.py`
- `qa_agents/regression.py`
- `qa_agents/performance.py`
- `qa_agents/stress_test.py`

Client MVP change:
Replace the LLM tool-selection step with deterministic triage first. Use the LLM
for analysis and test generation, not for deciding basic policy.

Recommended MVP triage rules:

| Change type | Risk | Run |
| --- | --- | --- |
| Docs/CSS/images only | low | static analysis only |
| Test-only changes | low | regression only |
| Dependency files | medium | static + VAPT + regression |
| Auth/payment/security paths | high | all agents, strict fail |
| API routes/controllers/services | high | static + functionality + regression + VAPT |
| Infra/config/deployment files | high | static + VAPT + regression |

Required MVP fixes:

- Add idempotency for repeated `synchronize` events.
- Store raw agent logs as artifacts or DB fields with truncation policy.
- Add timeouts per phase and a total QA timeout.
- Add explicit "required" vs "advisory" agents.
- Make warning/failure policy configurable per workspace.
- Run agents concurrently where safe.
- Do not mark `warning` as GitHub success unless the workspace policy allows it.

### `qa_agents/static_analysis.py`

Runs type-check and lint commands from stack detection.

MVP hardening:

- Parse outputs into structured findings.
- Use per-language defaults:
  - JS/TS: ESLint, `tsc --noEmit`
  - Python: Ruff, mypy when configured
  - Go: `go vet`, `go test`
  - Java: Maven/Gradle compile/check
- Treat tool-not-installed as `warning`, not `passed`.

### `qa_agents/functionality.py`

Uses the LLM to generate tests for changed files, writes them to the sandbox, and
runs them.

MVP hardening:

- Never overwrite existing tests unless writing under a SlothOps temp test path.
- Include PR diff and existing nearby tests in the prompt.
- Validate generated test file paths to prevent path traversal.
- Cap test file count and output size.
- Persist generated tests as QA artifacts.

### `qa_agents/vapt.py`

Runs dependency/audit tooling from stack detection.

MVP hardening:

- Add universal scanners when available:
  - OSV-Scanner
  - Trivy filesystem scan
  - Semgrep security rules
- Make missing scanner behavior explicit.
- Separate dependency vulnerabilities from secret findings.

### `qa_agents/regression.py`

Runs the existing repository test suite using the detected test command.

MVP hardening:

- This should be a required agent for most real client repos.
- Preserve full logs externally and store truncated summary in DB.
- Detect "no tests found" separately from pass/fail.

### `qa_agents/performance.py`

Boots the app and samples root endpoint latency.

MVP hardening:

- Make this advisory by default.
- Require configured healthcheck URL, not only `/`.
- Use project-specific start command from `.slothops.yml`.

### `qa_agents/stress_test.py`

Boots the app and runs `autocannon`.

MVP hardening:

- Disable by default for client MVP unless explicitly configured.
- Require safe load-test config.
- Never hit production URLs.

---

## Stack Detection

### `stack_detector.py`

Detects language/framework/commands from repo files and optional
`.slothops.yml` or `.slothops.yaml`.

Supported stacks:

- Node / TypeScript
- Python / Flask / Django
- Go
- Java / Maven / Gradle
- Rust
- Ruby / Rails
- PHP / Laravel
- .NET

Current outputs:

- `language`
- `framework`
- `start_command`
- `test_command`
- `lint_commands`
- `type_check_command`
- `audit_command`
- `install_command`
- `port`
- optional `workspaces`

Client MVP recommendation:
Require every client repo to include `.slothops.yml`. Heuristics are useful, but
production onboarding should be explicit.

Example:

```yaml
language: typescript
framework: node
install: npm ci
test: npm test -- --runInBand
lint:
  - npm run lint
type_check: npm run typecheck
audit: npm audit --json
start: npm start
port: 3000
qa_policy:
  warnings_block_merge: false
  required_agents:
    - static
    - regression
    - vapt
```

---

## Deployment Rollback

### `rollback.py`

Handles automatic production rollback when GitHub sends a failed deployment
status.

Trigger:

- GitHub webhook: `deployment_status` with state `failure` or `error`.

Current flow:

1. Resolve workspace from GitHub installation ID.
2. Authenticate as GitHub App installation.
3. Skip if rollback for the SHA already exists.
4. Fetch failed commit and linked PR.
5. Abort if the failed commit message starts with `Revert`.
6. Create backup branch: `slothops/backup-{sha}`.
7. Clone repo to a temp directory.
8. Checkout `main`.
9. Push backup branch.
10. Run `git revert --no-edit`; use `-m 1` for merge commits.
11. Push reverted `main`.
12. Store rollback as `completed`.
13. Comment on linked PR.
14. Send email notification if configured.
15. Trigger `resolution.attempt_resolution()` on the backup branch.

Client MVP hardening:

- Never enable auto-push-to-main without explicit client approval.
- Add a workspace-level rollback mode:
  - `disabled`
  - `suggest_only`
  - `auto_revert_with_approval`
  - `auto_revert`
- Verify the failed deployment corresponds to the default branch.
- Verify the provider/environment is production.
- Add deployment provider metadata to rollback records.
- Add branch protection compatibility checks.
- Add dry-run mode.
- Add a rollback lock per repo to avoid concurrent reverts.
- Add an allowlist of repos/environments where rollback is permitted.

Recommended client MVP default:
Start with `suggest_only` or `auto_revert_with_approval`. Full auto-revert should
come after successful controlled trials.

---

## Self-Healing Resolution

### `resolution.py`

Attempts to fix the code that caused a deployment failure after rollback.

Current flow:

1. Create `ResolutionRecord`.
2. Enforce max attempts: `MAX_RESOLUTION_ATTEMPTS = 3`.
3. Authenticate as GitHub App installation.
4. Fetch files changed in the failed commit.
5. Create a dummy `IssueRecord` with build logs as stack trace.
6. Call `llm_fixer.generate_fix()`.
7. Commit changed files and generated tests to the backup branch.
8. Open or update PR from backup branch to `main`.
9. Store resolution PR URL and number.
10. Broadcast and email resolution event.

Client MVP hardening:

- Use build logs from the deployment provider, not only webhook state text.
- Fetch CI logs from GitHub Actions when available.
- Do not use Sentry-style prompts for build failures; create a dedicated
  `build_fixer.py`.
- Include changed files, package files, lockfiles, CI config, and error logs in
  the prompt.
- Run QA on the generated resolution PR before marking it ready.
- Mark attempt as `abandoned` after max attempts and notify humans.

---

## LLM Layer

### `genai_client.py`

Centralized multi-provider LLM client.

Provider chain:

1. Vertex AI Gemini 2.5 Pro
2. OpenRouter DeepSeek
3. OpenRouter Qwen coder
4. Anthropic Claude Sonnet
5. Vertex AI Gemini Flash
6. Anthropic Claude Haiku

Important behavior:

- `generate_with_fallback()` is async.
- It serializes calls with `_llm_lock`.
- It retries rate limits with backoff.
- It skips bad-request provider failures and continues the chain.

Client MVP hardening:

- Add provider-level telemetry: latency, model, token estimate, failure reason.
- Add per-workspace provider configuration.
- Add strict JSON extraction/repair utility.
- Add cost controls and request-size limits.

### `llm_fixer.py`

Builds prompts and parses structured `LLMFixResponse`.

Important issue:
`generate_with_fallback()` is async, but parts of `llm_fixer.py` still call it as
if it were synchronous. Before relying on self-healing in production, make the
LLM fixer fully async or provide a safe sync wrapper.

MVP recommendation:
For the client MVP, split this file:

- `code_fixer.py` for source-code fixes.
- `build_fixer.py` for deployment/build failures.
- `qa_fixer.py` for QA auto-resolution.

---

## QA Auto-Resolve

### `main.py` - `_run_qa_resolution()`

Triggered by:

- `POST /api/qa-resolve/{report_id}`

Current flow:

1. Load failed/warning QA report.
2. Fetch PR changed files.
3. Build error context from failed QA agents.
4. Ask LLM for fixes in JSON.
5. Commit fixes atomically to the PR branch.
6. Post PR comment.
7. Mark QA report as `resolved`.

Client MVP hardening:

- Move this out of `main.py`.
- Require human click for auto-resolve in early MVP.
- Restrict writes to PR branches only.
- Show exact files that will be changed before commit in approval mode.
- Re-run QA automatically after pushing fixes.

---

## Dashboard and Events

### `sse_manager.py`

Fan-out Server-Sent Events manager.

Current event types include:

- `log`
- `status_update`
- `qa_update`
- `rollback_event`
- `resolution_event`

### `static/index.html` and `static/style.css`

Static dashboard UI with auth gate, issue feed, QA reports, rollback cards, and
settings/developer config flows.

Client MVP hardening:

- Add explicit setup checklist:
  - GitHub App installed
  - Repo selected
  - `.slothops.yml` detected
  - Webhook receiving events
  - QA status check configured
  - Rollback mode configured
- Add audit log view.
- Add per-repo settings instead of only workspace-level settings.

---

## Sentry Remediation Pipeline

This pipeline exists but is not the first client MVP target.

Key files:

- `pipeline.py`
- `sentry_parser.py`
- `redactor.py`
- `fingerprint.py`
- `classifier.py`
- `code_fetcher.py`
- `test_runner.py`
- `github_automation.create_fix_pr()`

Before using it in production:

- Fix async LLM calls in `llm_fixer.py`.
- Add webhook signature verification.
- Add stricter PII controls.
- Add repo selection by Sentry project/release.
- Add branch/PR idempotency.

---

## Minimal Client MVP Scope

Target only these capabilities first:

1. GitHub App install and workspace linking.
2. PR QA Gate:
   - Clone PR SHA.
   - Detect stack.
   - Install dependencies.
   - Run static analysis, regression, and VAPT.
   - Optionally run LLM-generated functionality tests.
   - Post PR report.
   - Set commit status.
   - Allow manual bypass with reason.
3. Deployment Rollback:
   - Receive deployment failure.
   - Record rollback event.
   - In MVP phase 1, suggest rollback instead of immediately pushing to main.
   - In MVP phase 2, allow approved auto-revert.
4. Self-Healing:
   - Fetch build logs and changed files.
   - Generate fix PR on backup branch.
   - Run QA on the fix PR.
   - Stop after 3 attempts.

Do not include in first client MVP:

- Fully autonomous Sentry crash remediation.
- Unapproved production auto-revert.
- Stress testing by default.
- Multi-repo autonomous repo selection without explicit config.

---

## Walkthrough: Turning SlothOps Into a Working MVP

### Step 1 - Define the production safety policy

Add workspace/repo config for:

- `rollback_mode`
- `required_agents`
- `warnings_block_merge`
- `allowed_environments`
- `default_branch`
- `deployment_provider`

Store this in `qa_configs` or a new `repo_configs` table.

### Step 2 - Require `.slothops.yml` in client repos

Use stack detection as fallback only. Production client repos should explicitly
define install, test, lint, audit, start, port, and QA policy.

### Step 3 - Harden GitHub webhook handling

Add:

- Signature verification using GitHub webhook secret.
- Event idempotency with `X-GitHub-Delivery`.
- Repo and workspace lookup from installation ID plus repository full name.
- Fast ACK with background task queue.

### Step 4 - Make QA deterministic first

Replace LLM-driven agent selection with deterministic triage.

Recommended required MVP agents:

- Static analysis
- Regression tests
- VAPT/dependency audit

Optional/advisory:

- Functionality test generation
- Performance check
- Stress test

### Step 5 - Improve QA result quality

Each agent should return:

```json
{
  "status": "passed | warning | failed",
  "summary": "short human-readable result",
  "issues": [],
  "logs": "truncated logs",
  "artifacts": []
}
```

Then aggregate with policy:

- Required agent failed -> commit status failure.
- Required agent warning -> depends on `warnings_block_merge`.
- Advisory agent failed -> warning unless configured otherwise.

### Step 6 - Split QA auto-resolution out of `main.py`

Create a dedicated `qa_resolution.py` module:

- Load report.
- Fetch PR branch files.
- Build prompt.
- Generate fixes.
- Commit to PR branch.
- Comment.
- Let GitHub synchronize webhook re-run QA.

### Step 7 - Make rollback approval-based first

For a real client project, start with:

- Detect failed deployment.
- Record rollback.
- Post PR/dashboard recommendation.
- Provide "Approve Rollback" action.

Only after validation should `rollback.py` push directly to `main`.

### Step 8 - Use real build logs for self-healing

The current `deployment_status` event often gives too little context.

Add provider integrations:

- GitHub Actions logs for failed workflow runs.
- Vercel deployment logs if Vercel is used.
- Render/Railway/Fly logs if those are used.

Feed those logs into a dedicated build fixer.

### Step 9 - Run QA on self-healing PRs

The backup branch PR should go through the same QA gate as human PRs.
Do not mark self-healing complete until QA passes or a human bypasses it.

### Step 10 - Add observability and audit

Minimum production logging:

- webhook received
- workspace/repo resolved
- clone started/finished
- every QA command and exit code
- rollback suggested/approved/executed
- resolution attempt number
- LLM provider/model used
- GitHub status/comment result

Minimum audit log:

- user bypassed QA
- user approved rollback
- bot pushed fix
- bot reverted commit

---

## Local Verification

Run engine unit tests:

```bash
cd slothops-engine
source venv/bin/activate
python -m pytest tests -q
```

Run syntax check:

```bash
cd ..
python3 -m compileall -q slothops-engine
```

Current known local baseline:

- Unit tests pass for parser/classifier/fingerprint/redaction.
- QA, rollback, and resolution need integration tests with mocked GitHub APIs.

---

## Highest Priority Backlog

1. Fix async/sync LLM boundary in `llm_fixer.py`.
2. Verify GitHub webhook signatures.
3. Add deterministic QA triage.
4. Add repo-level `.slothops.yml` enforcement.
5. Move QA auto-resolve out of `main.py`.
6. Add approval mode for rollback.
7. Add build-log fetchers for deployment providers.
8. Add integration tests for PR QA and rollback flows.
9. Move SQLite to Postgres for hosted client deployments.
10. Add audit log and per-workspace/repo policy.
