# SlothOps Expected Behaviour And Local Testing Guide

This guide is for a new developer validating SlothOps locally against a disposable GitHub demo repository. It covers what the product should do, how to configure it, and how to test each major MVP workflow end to end.

Do not use a production repository for the first run. Use a throwaway repo where SlothOps can create branches, commit files, open PRs, and set commit statuses.

---

## 1. Product Behaviour To Expect

### Core Principle

SlothOps should behave like a controlled repo-operations engine, not an uncontrolled production mutator.

Expected safety defaults:

- PR QA runs are deterministic and policy-driven.
- GitHub webhook deliveries are idempotent. Replaying the same delivery ID should not duplicate QA reports or rollback records.
- Rollbacks are approval-first by default.
- Default rollback strategy is `rollback_pr`, not direct push to `main`.
- Sentry issues must resolve to a configured repo before the fix pipeline runs.
- LLMs can generate recommendations/fixes, but they must not decide which required QA checks run.
- Every major bot action should be persisted in SQLite and, where implemented, written to `audit_events`.

### PR Opened Or Updated

When a human opens or updates a PR in the demo repo:

1. GitHub sends a `pull_request` webhook to SlothOps.
2. SlothOps resolves the workspace from the GitHub App installation ID.
3. SlothOps posts one consolidated PR insight comment.
4. SlothOps starts QA after a short delay.
5. GitHub commit status `SlothOps QA` becomes `pending`.
6. SlothOps clones the PR head SHA into a temp directory.
7. SlothOps detects the stack and triages changed files deterministically.
8. Required QA agents run first.
9. Advisory QA agents run only if required agents did not hard-fail.
10. SlothOps stores a row in `qa_reports`.
11. SlothOps posts a QA report comment to the PR.
12. GitHub commit status becomes:
    - `success` when QA passed.
    - `success` when QA has warnings and `warnings_block_merge=false`.
    - `failure` when a required agent fails, or when required warnings are configured to block.

Expected triage examples:

| PR change | Expected required agents | Expected advisory agents |
| --- | --- | --- |
| `README.md`, `docs/*`, images, CSS only | none | `static_analysis` |
| `package.json`, lockfiles, dependency manifests | `static_analysis`, `regression`, `vapt` | `functionality` |
| `auth`, `payment`, `security`, `api`, `routes`, `middleware` paths | `static_analysis`, `regression`, `vapt` | `functionality`, optionally `performance` |
| tests/spec files only | `regression` | none |
| generic source code | `static_analysis`, `regression`, `vapt` | `functionality` |

### Deployment Failure

When GitHub sends a `deployment_status` webhook with state `failure` or `error`:

1. SlothOps resolves workspace and repo.
2. SlothOps checks if the failed SHA already has a rollback record.
3. SlothOps creates one `rollbacks` row in `pending_approval`.
4. SlothOps does not mutate `main`.
5. After an operator calls the approval endpoint, SlothOps updates the rollback to `approved`.
6. SlothOps executes the configured strategy.
7. With default `rollback_pr`, SlothOps creates a rollback branch and opens a PR to `main`.
8. With explicit `direct_revert`, SlothOps pushes the revert to `main`.

Expected local MVP default:

```text
deployment_status failure -> rollbacks.status=pending_approval -> approval endpoint -> rollback PR opened
```

### Sentry Production Error

When Sentry sends an issue webhook:

1. SlothOps verifies the Sentry signature only if a secret exists.
2. SlothOps parses the payload.
3. SlothOps resolves the repo using `repo_configs.sentry_project_slug`.
4. If no repo config exists, SlothOps returns `409`.
5. If mapped, SlothOps sets `issue.repo_name`.
6. SlothOps fingerprints and deduplicates the issue.
7. SlothOps classifies the issue.
8. For code issues, SlothOps fetches source files from the mapped repo.
9. SlothOps asks the LLM for strict JSON.
10. High/medium confidence fixes open a draft PR.
11. Low confidence fixes store a recommendation only.

---

## 2. Prerequisites

Local tools:

- Python 3.11+
- Git
- `ngrok` or another public tunnel
- GitHub account with permission to create a GitHub App
- Disposable GitHub demo repository
- Optional but useful: `sqlite3`

SlothOps services/accounts:

- GitHub App with access to the demo repo.
- At least one LLM provider configured. The current engine uses `genai_client.py`; Vertex/Gemini is the primary path, with optional fallback providers.
- Optional Sentry project for testing the production-error workflow.

---

## 3. Environment Setup

From the repo root:

```bash
cd /Users/sumanjain/code/binary/slothops-engine
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in `slothops-engine/`:

```bash
DATABASE_PATH=./slothops.db
LOG_LEVEL=INFO
BASE_URL=https://YOUR-NGROK-DOMAIN.ngrok.app

GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY=/absolute/path/to/github-app-private-key.pem
GITHUB_WEBHOOK_SECRET=

ROLLBACK_DEFAULT_MODE=approval_required
ROLLBACK_DEFAULT_STRATEGY=rollback_pr
MAX_QA_LOG_CHARS=4000
MAX_LLM_CONTEXT_CHARS=24000

GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_CLOUD_LOCATION=us-central1

# Optional fallbacks
OPENROUTER_API_KEY=
TOGETHER_API_KEY=
ANTHROPIC_API_KEY=
```

For local manual `curl` webhook tests, keeping `GITHUB_WEBHOOK_SECRET` empty is simplest. If you set it, every manual GitHub webhook request must include a valid `X-Hub-Signature-256`.

Start the engine:

```bash
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

In another terminal:

```bash
ngrok http 8000
```

Copy the public HTTPS URL and use it as `BASE_URL`.

---

## 4. GitHub App Setup

Create or update a GitHub App for local testing.

Webhook URL:

```text
https://YOUR-NGROK-DOMAIN.ngrok.app/webhook/github
```

Subscribe to these events:

- Pull request
- Deployment status
- Installation

Minimum repository permissions:

- Contents: Read and write
- Pull requests: Read and write
- Commit statuses: Read and write
- Metadata: Read-only
- Actions: Read-only, useful for deployment log fetching

Install the GitHub App on the disposable demo repo.

---

## 5. Create A Local Workspace And Link GitHub

Create a workspace:

```bash
curl -s -X POST http://localhost:8000/api/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dev@example.com",
    "password": "dev-password",
    "workspace_name": "Local SlothOps"
  }'
```

Save the returned `access_token`:

```bash
export SLOTHOPS_TOKEN="paste-token-here"
```

Find your GitHub App installation ID. You can get it from the GitHub App installation URL or from GitHub webhook payloads.

Link the installation:

```bash
curl -s -X POST http://localhost:8000/api/github/link \
  -H "Authorization: Bearer $SLOTHOPS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"installation_id": "YOUR_INSTALLATION_ID"}'
```

Find the workspace ID:

```bash
python - <<'PY'
import sqlite3
db = sqlite3.connect("slothops.db")
for row in db.execute("select id, name from workspaces"):
    print(row)
PY
```

Export it:

```bash
export WORKSPACE_ID="paste-workspace-id-here"
export DEMO_REPO="your-org/your-demo-repo"
```

---

## 6. Seed Repo Policy

There is not yet a dashboard/API screen for repo policy. For local testing, seed `repo_configs` directly.

```bash
python - <<'PY'
import json
import os
import sqlite3
from datetime import datetime

workspace_id = os.environ["WORKSPACE_ID"]
repo_name = os.environ["DEMO_REPO"]
now = datetime.utcnow().isoformat()

policy = {
    "rollback_mode": "approval_required",
    "rollback_strategy": "rollback_pr",
    "required_agents": ["static_analysis", "regression", "vapt"],
    "advisory_agents": ["functionality"],
    "warnings_block_merge": False,
    "allowed_environments": ["production"],
    "max_resolution_attempts": 3,
    "stress_enabled": False
}

db = sqlite3.connect("slothops.db")
db.execute(
    """
    insert into repo_configs (
      workspace_id, repo_name, config_json, sentry_project_slug, active, created_at, updated_at
    ) values (?, ?, ?, ?, 1, ?, ?)
    on conflict(workspace_id, repo_name) do update set
      config_json=excluded.config_json,
      sentry_project_slug=excluded.sentry_project_slug,
      active=1,
      updated_at=excluded.updated_at
    """,
    (workspace_id, repo_name, json.dumps(policy), "demo-api", now, now),
)
db.commit()
print("Seeded repo config for", workspace_id, repo_name)
PY
```

Verify:

```bash
python - <<'PY'
import sqlite3
db = sqlite3.connect("slothops.db")
for row in db.execute("select workspace_id, repo_name, sentry_project_slug, active, config_json from repo_configs"):
    print(row)
PY
```

---

## 7. Local Smoke Tests

Run the unit test suite:

```bash
cd /Users/sumanjain/code/binary/slothops-engine
source venv/bin/activate
python -m compileall -q .
python -m pytest tests -q
```

Expected result:

```text
87 passed
```

Health check:

```bash
curl -s http://localhost:8000/health
```

Expected:

```json
{"status":"ok","service":"slothops-engine"}
```

Integration status:

```bash
curl -s http://localhost:8000/api/integrations/status \
  -H "Authorization: Bearer $SLOTHOPS_TOKEN"
```

Expected:

- `github.linked` is `true`.
- `github.installation_id` is your installation ID.
- `github.repos` contains the demo repo if GitHub auth is correct.

---

## 8. Demo Repo Test Plan

Use a disposable repo with a simple app. A Node/TypeScript repo is a good default because stack detection can find `package.json`, lint/test commands, and dependency manifests.

Suggested demo repo shape:

```text
package.json
src/
  routes/
    users.ts
    auth.ts
tests/
  users.test.ts
README.md
```

The repo should have at least one test command in `package.json`, for example:

```json
{
  "scripts": {
    "test": "jest --runInBand",
    "lint": "eslint ."
  }
}
```

Install the GitHub App on this repo before testing.

---

## 9. Test PR Insight And Deterministic QA

Create a branch in the demo repo:

```bash
git checkout -b test/slothops-generic-code-change
```

Make a small source change, for example in `src/routes/users.ts`, then push and open a PR.

Expected GitHub behaviour:

- A SlothOps PR insight comment appears.
- Commit status `SlothOps QA` becomes `pending`.
- A QA report comment appears.
- Commit status becomes `success`, `failure`, or `success with warnings` depending on agent output.

Expected database rows:

```bash
python - <<'PY'
import sqlite3
db = sqlite3.connect("slothops.db")
for row in db.execute("select id, repo_name, pr_number, overall_status, required_agents, advisory_agents from qa_reports order by created_at desc limit 5"):
    print(row)
PY
```

For generic code changes, expect:

- `required_agents` includes `static_analysis`, `regression`, `vapt`.
- `advisory_agents` includes `functionality`.
- `overall_status` is `passed`, `warning`, or `failed`.

Repeat with a docs-only PR:

```bash
git checkout -b test/slothops-docs-only
echo "SlothOps docs smoke test" >> README.md
git add README.md
git commit -m "docs: smoke test slothops"
git push origin test/slothops-docs-only
```

Expected docs-only triage:

- `required_agents` is empty.
- `advisory_agents` is `static_analysis`.
- No regression/VAPT/functionality agents should be required.

Repeat with a dependency PR:

```bash
git checkout -b test/slothops-dependency-change
# edit package.json or lockfile
git add package.json package-lock.json
git commit -m "chore: dependency smoke test"
git push origin test/slothops-dependency-change
```

Expected dependency triage:

- `required_agents` includes `static_analysis`, `regression`, `vapt`.

---

## 10. Test QA Failure And QA Auto-Resolution

Create a PR that intentionally fails tests.

Example:

- Change application code so an existing test fails.
- Or add a failing test in `tests/users.test.ts`.

Expected:

- QA report `overall_status` becomes `failed`.
- GitHub commit status `SlothOps QA` becomes `failure`.
- PR comment contains the failing agent output.

Find the latest QA report ID:

```bash
python - <<'PY'
import sqlite3
db = sqlite3.connect("slothops.db")
for row in db.execute("select id, pr_number, overall_status, summary from qa_reports order by created_at desc limit 3"):
    print(row[0], row[1], row[2])
PY
```

Trigger QA resolution:

```bash
export QA_REPORT_ID="paste-report-id"

curl -s -X POST http://localhost:8000/api/qa-resolve/$QA_REPORT_ID \
  -H "Authorization: Bearer $SLOTHOPS_TOKEN"
```

Expected:

- QA report changes to `resolving`, then `resolved` or `failed`.
- If the LLM generated fixes, SlothOps commits only to the PR branch.
- SlothOps posts a QA auto-resolution PR comment.
- GitHub sends a `synchronize` webhook and QA reruns.

If the LLM provider is not configured, expected result is a controlled failure summary, not a server crash.

---

## 11. Test Deployment Rollback Planning

The safest local test is to post a synthetic GitHub `deployment_status` webhook. Keep `GITHUB_WEBHOOK_SECRET` empty for this manual test, or sign the body if you configured a secret.

Create a payload file:

```bash
cat > /tmp/slothops-deployment-failure.json <<JSON
{
  "action": "created",
  "installation": { "id": YOUR_INSTALLATION_ID },
  "repository": { "full_name": "$DEMO_REPO" },
  "deployment": {
    "sha": "PUT_A_REAL_COMMIT_SHA_FROM_DEMO_REPO",
    "ref": "main"
  },
  "deployment_status": {
    "state": "failure",
    "environment": "production",
    "target_url": "https://example.invalid/deploy/1",
    "description": "Synthetic local rollback test"
  },
  "sender": { "login": "local-tester" }
}
JSON
```

Send it:

```bash
curl -s -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: deployment_status" \
  -H "X-GitHub-Delivery: local-deploy-$(date +%s)" \
  -d @/tmp/slothops-deployment-failure.json
```

Expected API response:

```json
{"status":"rollback_planned"}
```

Expected database row:

```bash
python - <<'PY'
import sqlite3
db = sqlite3.connect("slothops.db")
for row in db.execute("select id, repo_name, failed_commit_sha, status, rollback_mode, rollback_strategy from rollbacks order by created_at desc limit 5"):
    print(row)
PY
```

Expected:

- `status` is `pending_approval`.
- `rollback_mode` is `approval_required`.
- `rollback_strategy` is `rollback_pr`.
- No branch or PR should be created yet.

Replay the same webhook with the same `X-GitHub-Delivery` value.

Expected:

```json
{"status":"duplicate_ignored"}
```

---

## 12. Test Rollback Approval

Approve the rollback:

```bash
export ROLLBACK_ID="paste-rollback-id"

curl -s -X POST http://localhost:8000/api/rollbacks/$ROLLBACK_ID/approve \
  -H "Authorization: Bearer $SLOTHOPS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Local validation of approval-first rollback flow"}'
```

Expected immediate response:

```json
{"status":"approved","rollback_id":"..."}
```

Expected eventual behaviour:

- `rollbacks.status` becomes `reverting`.
- Then it becomes `rollback_pr_opened` if GitHub operations succeed.
- A branch named like `slothops/backup-<sha>` is created.
- A branch named like `slothops/rollback-<sha>` is created.
- A rollback PR is opened against `main`.
- `audit_events` includes rollback planned, approved, and executed/failure events.

Check:

```bash
python - <<'PY'
import sqlite3
db = sqlite3.connect("slothops.db")
print("Rollbacks:")
for row in db.execute("select id, status, pr_url, approved_by, approval_reason from rollbacks order by created_at desc limit 5"):
    print(row)
print("Audit:")
for row in db.execute("select action, target_type, target_id, metadata_json from audit_events order by created_at desc limit 10"):
    print(row)
PY
```

If the failed SHA is not a valid commit in the demo repo, expected result is `failed` with a stored reason.

---

## 13. Test Sentry Repo Mapping

First, make sure `repo_configs.sentry_project_slug` matches the Sentry project slug. The seed example uses:

```text
demo-api
```

Manual fixture test:

```bash
python - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("tests/fixtures/sentry_webhook.json").read_text())
payload["project_slug"] = "demo-api"
Path("/tmp/slothops-sentry.json").write_text(json.dumps(payload))
PY

curl -s -X POST http://localhost:8000/webhook/sentry/$WORKSPACE_ID \
  -H "Content-Type: application/json" \
  -d @/tmp/slothops-sentry.json
```

Expected response when repo config exists:

```json
{"status":"accepted","issue_id":"..."}
```

Expected response when repo config is missing:

```json
{"error":"No repo configured for this Sentry project"}
```

Check issue routing:

```bash
python - <<'PY'
import sqlite3
db = sqlite3.connect("slothops.db")
for row in db.execute("select id, repo_name, error_type, status, fix_pr_url, root_cause from issues order by created_at desc limit 5"):
    print(row)
PY
```

Expected:

- `repo_name` is the demo repo.
- Status advances through `triaging`, `classified`, `fixing`.
- If source files match the Sentry stack trace and LLM/GitHub are configured, a draft PR is opened.
- If source files do not exist in the demo repo, status becomes `fixing_failed` with a clear root cause.

For a true Sentry end-to-end test, configure Sentry Webhooks URL:

```text
https://YOUR-NGROK-DOMAIN.ngrok.app/webhook/sentry/YOUR_WORKSPACE_ID
```

Then trigger an exception in the demo app whose stack trace points to a file that exists in the demo repo.

---

## 14. Dashboard Checks

Open:

```text
http://localhost:8000/
```

Expected:

- Engine loads without a 500.
- QA reports are visible after PR tests.
- Rollback records are visible after deployment failure tests.
- SSE log stream updates while the engine is running.

If auth blocks a dashboard action, verify the same state through the API and SQLite queries above.

---

## 15. Pass/Fail Checklist

Mark the local run as passed only if all required items pass:

- Health endpoint returns OK.
- Unit tests pass.
- GitHub App installation is linked to the workspace.
- `repo_configs` contains the demo repo.
- Human PR receives a PR insight comment.
- Human PR creates a QA report.
- GitHub commit status is set by SlothOps.
- Docs-only PR uses advisory/static-only triage.
- Generic code PR uses static/regression/VAPT required triage.
- Duplicate GitHub delivery is ignored.
- Deployment failure creates `pending_approval`, not an immediate direct revert.
- Rollback approval opens a rollback PR by default.
- Sentry webhook rejects unconfigured project mapping.
- Sentry webhook accepts configured project mapping and stores `issue.repo_name`.

Optional pass items:

- QA auto-resolution commits to the PR branch.
- Sentry issue opens a draft fix PR.
- Resolution branch PR opens after rollback execution.

---

## 16. Common Failure Modes

### GitHub webhook received but no QA starts

Check:

- GitHub App is installed on the demo repo.
- Installation ID is linked to the workspace.
- `X-GitHub-Event` is `pull_request`.
- PR action is `opened` or `synchronize`.
- Engine logs show workspace resolution.

### QA report is warning because tools are missing

This is expected for bare demo repos. Missing configured static/VAPT/regression tools should produce warnings, not fake passes. Add real `test`, `lint`, and audit commands to the demo repo to get stronger signal.

### Rollback approval fails

Check:

- Rollback status is `pending_approval`.
- Failed SHA exists in the demo repo.
- GitHub App has contents write and pull request write permissions.
- Demo repo has a `main` branch.

### Sentry issue accepted but no PR appears

Check:

- The Sentry stack trace file exists in the demo repo.
- LLM provider is configured.
- GitHub App can read the file.
- `issues.root_cause` and `issues.status` for the failure reason.

### Duplicate tests keep being skipped

Use a new `X-GitHub-Delivery` value for every manual webhook test unless you are intentionally testing idempotency.

---

## 17. What Is Not Finished Yet

These are expected MVP gaps, not local setup mistakes:

- Repo policy still needs a dashboard/API surface; local tests seed SQLite directly.
- `main.py` still owns too many routes and should be split before client rollout.
- SQLite is fine for local MVP, but Postgres plus Alembic migrations are needed for clients.
- Full GitHub/Sentry integration tests are still manual.
- Direct production revert should remain disabled unless a repo policy explicitly opts in.

