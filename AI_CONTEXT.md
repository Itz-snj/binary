# SLOTHOPS — AI CONTEXT FILE
# Last Updated: 2025
# Purpose: Feed this file to any LLM before asking it to help
#          with SlothOps development. It contains the full
#          project spec, architecture, data contracts, and rules.

---

## WHAT IS SLOTHOPS

SlothOps is a production-aware automated bug remediation pipeline.
It monitors real-time application errors via Sentry webhooks,
classifies them as code vs infrastructure issues, fetches relevant
source code from GitHub, generates validated fixes using an LLM,
and opens governed draft Pull Requests for developer review.

It is NOT a code review tool.
It is NOT a monitoring dashboard.
It is a CLOSED-LOOP system that converts production errors into
reviewable code fixes automatically.

---

## CORE PIPELINE (in order)

1. SIGNAL INGESTION
   - Sentry webhook fires on new/recurring exceptions
   - FastAPI server receives the webhook payload
   - Payload is parsed to extract error metadata and stack frames

2. REDACTION
   - All PII, tokens, secrets, emails, IPs, JWTs are stripped
   - Only sanitized error context reaches the LLM
   - Redaction happens BEFORE any processing

3. FINGERPRINTING + DEDUPLICATION
   - fingerprint = hash(error_type + file_path + function_name)
   - If fingerprint exists in SQLite DB:
     - Increment occurrence_count
     - If a PR is already open for this fingerprint, skip
     - If a previous PR was merged but error recurs, re-trigger
   - If fingerprint is new: create new issue record

4. CLASSIFICATION
   - Heuristic classifier determines: code | infra | dependency | unknown
   - ONLY "code" classification proceeds to fix generation
   - "infra" and "unknown" are logged but no PR is created

5. SOURCE RESOLUTION
   - Parse Sentry stack trace frames
   - Skip frames from node_modules
   - Extract top application-level frame:
     - file_path
     - function_name
     - line_number
     - context_line

6. CODE CONTEXT RETRIEVAL
   - Use PyGithub to fetch from the target repo:
     - The failing source file (full content)
     - Associated test file (if exists, convention: src/ → tests/, .ts → .test.ts)
     - Local imports referenced in the failing file
   - Do NOT fetch the entire repo
   - Do NOT use embeddings or vector search (out of scope for MVP)

7. LLM FIX GENERATION
   - Model: Google Gemini 2.5 Pro (via google-genai SDK)
   - Temperature: 0.2 (deterministic)
   - Response format: JSON (enforced via response_schema)
   - System prompt enforces strict rules (see RULES section below)
   - Output includes:
     - root_cause (string)
     - confidence (high | medium | low)
     - files_changed (array of {path, original_content, fixed_content, explanation})
     - pr_title (string)
     - pr_body (markdown string)

8. CONFIDENCE GATING
   - high confidence → create draft PR
   - medium confidence → create draft PR with "needs-careful-review" label
   - low confidence → log recommendation only, do NOT create PR

9. GITHUB PR CREATION
   - Create branch: slothops/fix-{safe-file-name}-{issue-id-prefix}
   - Commit each changed file to the branch
   - Open a DRAFT Pull Request against main
   - PR body includes:
     - Root cause analysis
     - Confidence level
     - Error metadata table
     - Per-file change explanations
     - Warning that this is auto-generated

10. POST-MERGE RECURRENCE MONITORING
    - If the same fingerprint reappears after PR merge:
      - Mark previous fix as "fix_ineffective"
      - Re-trigger pipeline with extra context telling the LLM
        that a prior fix attempt failed
      - Include link to previous PR in the new prompt

---

## FILE-BY-FILE PIPELINE MAP

This section maps each pipeline step to the exact Python file responsible for it.
Use this as the ground truth when asking an LLM to work on a specific module.

| Step | File | Function / Class | What it does |
|------|------|------------------|--------------|
| 1. Receive webhook | `main.py` | `POST /webhook/sentry` route | Accepts Sentry HTTP POST, returns 200 immediately, spawns async pipeline task |
| 2. Parse payload | `sentry_parser.py` | `parse_sentry_webhook(payload)` | Extracts error_type, error_message, file_path, function_name, line_number, stack_trace + call_chain from raw Sentry JSON. Returns `(IssueRecord, list[CallFrame])` |
| 3. Redact PII | `redactor.py` | `redact(text)` | Strips emails, IPs, tokens, JWTs, credit cards from all text fields before anything else touches them |
| 4. Fingerprint | `fingerprint.py` | `compute_fingerprint(...)` | Creates `sha256(error_type + file_path + function_name)` — the dedup key |
| 5. Dedup check | `fingerprint.py` | `check_dedup(fingerprint, db)` | Looks up fingerprint in SQLite; returns `CREATE`, `SKIP`, or `RETRIGGER` |
| 6a. Persist issue | `database.py` | `create_issue(issue)` / `update_issue_status(...)` | Writes or updates the issue record in SQLite via aiosqlite |
| 6b. Parse call chain | `call_chain.py` | `parse_call_chain(frames)` | Converts raw Sentry frame dicts into structured `CallFrame` list, filtering to app frames only (cap 5) |
| 7. Classify | `classifier.py` | `classify(issue)` | Returns `code`, `infra`, `dependency`, or `unknown`. Only `code` proceeds to fix generation |
| 8a. Fetch source (first pass) | `code_fetcher.py` | `fetch_code_context(issue)` | Uses PyGithub to download: main failing file + test file + up to 3 local imports |
| 8b. Fetch deep (recurrence) | `code_fetcher.py` | `fetch_deep_code_context(issue, call_chain)` | Fetches crash site + imports + all caller files from call chain (cap 7) |
| 9a. Generate fix (pass 1) | `llm_fixer.py` | `generate_fix(issue, code_context, call_chain)` | Builds system + user prompt, calls Gemini 2.5 Pro (temp=0.2, JSON mode), parses `LLMFixResponse`. If `deep_scan_needed`, triggers second pass |
| 9b. Second-pass fetch | `code_fetcher.py` | `fetch_requested_files(paths, repo)` | Fetches files specifically requested by LLM for deep scan |
| 10. Confidence gate | `pipeline.py` | inside `run_pipeline()` | Checks `fix.confidence`: high/medium → create PR, low → store recommendation only |
| 11. Create PR | `github_automation.py` | `create_fix_pr(issue, fix)` | Creates branch, commits each changed file, opens Draft PR on GitHub via PyGithub |
| 12. Broadcast | `sse_manager.py` | `broadcast(event_type, payload)` | Emits SSE events at each stage so the dashboard updates in real-time |
| 13. Serve dashboard | `main.py` | `GET /` | Serves `static/index.html` |
| 14. SSE stream | `main.py` | `GET /stream` | SSE endpoint; dashboard's `EventSource` connects here |
| 15. List issues | `main.py` | `GET /issues`, `GET /issues/{id}` | Returns SQLite issue records as JSON for dashboard to render |

### Recurrence Flow (Post-Merge)
```
Same fingerprint fires AFTER PR was merged
  → fingerprint.py: check_dedup() returns RETRIGGER
  → database.py: mark status = "fix_ineffective", set previous_fix_id
  → pipeline.py: re-runs full pipeline
  → llm_fixer.py: injects previous_pr_url into user prompt so Gemini knows prior fix failed
  → github_automation.py: opens a new Draft PR referencing the old one
```

### Data Object That Flows Through All Modules
Every module reads and writes the same `IssueRecord` Pydantic model (defined in `models.py`).
The full JSON shape is documented in the **INTERNAL DATA CONTRACT** section below.

---

## TECH STACK

| Component          | Technology              |
|--------------------|-------------------------|
| Bot Server         | Python 3.11 + FastAPI   |
| Target Demo App    | Node.js + Express + TypeScript |
| LLM                | Google Gemini 2.5 Pro   |
| Monitoring         | Sentry (free tier)      |
| Git Automation     | PyGithub                |
| Database           | SQLite (aiosqlite, multi-tenant) |
| Dashboard          | Static HTML + Custom CSS + SSE |
| Authentication     | bcrypt + PyJWT (Bearer tokens) |
| GitHub Integration | GitHub App (@slothops-bot) |
| CI Validation      | GitHub Actions in target repo |
| Tunnel (dev)       | ngrok                   |

---

## REPO STRUCTURE

```
slothops-engine/
├── main.py                  # FastAPI app entry point + auth routes
├── auth.py                  # bcrypt password hashing + PyJWT token management
├── config.py                # Environment variables and settings
├── models.py                # Pydantic models (IssueRecord, User, Workspace, Integration)
├── database.py              # SQLite connection and multi-tenant queries
├── pipeline.py              # Main orchestration: run_pipeline()
├── sentry_parser.py         # Parse Sentry webhook payloads
├── classifier.py            # Code vs infra classification
├── redactor.py              # PII and secret redaction
├── code_fetcher.py          # GitHub code context retrieval
├── llm_fixer.py             # Gemini prompt construction, fix gen + infra recommendations
├── github_automation.py     # Branch, commit, PR creation via GitHub App tokens
├── fingerprint.py           # Issue fingerprinting and dedup logic
├── call_chain.py            # Call chain parsing and path normalization
├── sse_manager.py           # Server-Sent Events for dashboard
├── static/
│   ├── index.html           # Dashboard UI (auth gate + issue feed + settings modal)
│   └── style.css            # Custom CSS design system
├── tests/
│   ├── test_classifier.py
│   ├── test_redactor.py
│   ├── test_fingerprint.py
│   ├── test_sentry_parser.py
│   └── fixtures/
│       ├── sentry_webhook.json       # Sample shallow bug payload
│       ├── sentry_deep_chain.json    # Bug 8: 4-file deep chain payload
│       ├── sentry_bug9_shipping.json # Bug 9: 4-file shipping calc crash
│       └── sentry_bug10_marketing.json # Bug 10: 5-file email blast crash
├── requirements.txt
└── .env.example

slothops-demo-app/
├── src/
│   ├── index.ts             # Express app with Sentry init
│   ├── routes/
│   │   ├── users.ts         # Bug 1: null profile reference, Bug 6: null feature config
│   │   ├── orders.ts        # Bug 7: undefined receiptId, Bug 8: deep chain invoice trigger
│   │   ├── sync.ts          # Bug 4: floating async promise in forEach
│   │   ├── config.ts        # Bug 5: global singleton cache poisoning
│   │   ├── shipping.ts      # Bug 9 trigger: Shipping Calculator
│   │   └── marketing.ts     # Bug 10 trigger: Marketing Blast
│   ├── middleware/
│   │   └── auth.ts          # Bug 3: unhandled jwt.verify crash
│   ├── services/
│   │   ├── userService.ts   # Bug 8, 10 root cause: missing fields
│   │   ├── orderService.ts  # Bug 2: array on undefined, Bug 8: calculateTotal
│   │   ├── discountService.ts # Bug 8 crash site: getLoyaltyDiscount
│   │   ├── inventoryService.ts # Bug 9 root cause: missing weight
│   │   ├── pricingService.ts   # Bug 9 crash site: calc total
│   │   ├── shippingService.ts  # Bug 9 orchestrator
│   │   ├── templateService.ts  # Bug 10 crash site: template rendering
│   │   ├── emailService.ts     # Bug 10 email loop
│   │   └── marketingService.ts # Bug 10 orchestrator
│   └── public/
│       ├── index.html       # Demo app frontend
│       └── style.css
├── tests/
│   ├── users.test.ts
│   └── orders.test.ts
├── .github/
│   └── workflows/
│       └── validate.yml     # CI: lint + typecheck + test
├── package.json
├── tsconfig.json
└── vercel.json
```

---

## DATABASE SCHEMA

```sql
CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE workspace_users (
    workspace_id TEXT,
    user_id TEXT,
    role TEXT DEFAULT 'admin',
    PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE integrations (
    workspace_id TEXT PRIMARY KEY,
    github_installation_id TEXT,
    sentry_webhook_secret TEXT
);

CREATE TABLE issues (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL DEFAULT 'default_workspace',
    fingerprint TEXT NOT NULL,
    error_type TEXT,
    error_message TEXT,
    file_path TEXT,
    function_name TEXT,
    line_number INTEGER,
    stack_trace TEXT,
    raw_payload TEXT,
    occurrence_count INTEGER DEFAULT 1,
    classification TEXT DEFAULT 'unknown',
    confidence TEXT,
    status TEXT DEFAULT 'received',
    fix_pr_url TEXT,
    fix_pr_branch TEXT,
    root_cause TEXT,
    recommendation TEXT,
    previous_fix_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fingerprint ON issues(fingerprint);
CREATE INDEX idx_status ON issues(status);
```

---

## INTERNAL DATA CONTRACT

This JSON shape flows through the entire pipeline.
All modules must read/write this structure.

```json
{
  "id": "uuid-v4",
  "fingerprint": "sha256-hash",
  "error_type": "TypeError",
  "error_message": "Cannot read properties of undefined (reading 'email')",
  "file_path": "src/routes/users.ts",
  "function_name": "getUserProfile",
  "line_number": 42,
  "stack_trace": "full raw stack trace string (redacted)",
  "occurrence_count": 5,
  "classification": "code",
  "confidence": "high",
  "status": "pr_created",
  "fix_pr_url": "https://github.com/org/repo/pull/42",
  "fix_pr_branch": "slothops/fix-src-routes-users-ts-abc12345",
  "root_cause": "user.profile can be null for users who...",
  "recommendation": null,
  "previous_fix_id": null,
  "call_chain": [
    { "file_path": "src/services/userService.ts", "function_name": "getUserById", "line_number": 15, "context_line": "return users.find(u => u.id === id) ?? null;" },
    { "file_path": "src/routes/users.ts", "function_name": "getUserProfile", "line_number": 42, "context_line": "const name = user.profile.displayName;" }
  ],
  "created_at": "2025-01-15T03:22:00Z",
  "updated_at": "2025-01-15T03:24:30Z"
}
```

### LLM Fix Response (deep scan fields)

```json
{
  "root_cause": "...",
  "confidence": "high",
  "files_changed": [...],
  "pr_title": "fix: ...",
  "pr_body": "...",
  "deep_scan_needed": false,
  "deep_scan_files": []
}
```

---

## LLM SYSTEM PROMPT (EXACT)

When generating fixes, use this exact system prompt:

```
You are SlothOps, an automated production bug remediation system.

RULES:
1. You MUST fix the root cause, not hide the symptom.
2. You MUST NOT wrap code in empty try/catch blocks.
3. You MUST NOT suppress or swallow errors silently.
4. You MUST NOT remove existing error logging or monitoring.
5. You MUST NOT comment out failing code.
6. You MUST NOT add generic fallbacks without clear reasoning.
7. You MUST preserve the original code style and conventions.
8. You MUST explain your root cause hypothesis clearly.
9. If the fix requires changes to multiple files, specify each file separately.
10. If you are not confident about the fix, set confidence to "low"
    and explain why.
11. You MUST return valid JSON matching the specified format.
12. You MUST return the COMPLETE file content for each changed file,
    not just the diff or snippet.

RESPONSE FORMAT (strict JSON):
{
  "root_cause": "one paragraph explanation of why this bug happens",
  "confidence": "high | medium | low",
  "files_changed": [
    {
      "path": "src/routes/users.ts",
      "original_content": "full original file content",
      "fixed_content": "full fixed file content",
      "explanation": "what was changed and why"
    }
  ],
  \"pr_title\": \"fix: short description of the fix\",
  \"pr_body\": \"markdown formatted PR description\",
  \"deep_scan_needed\": false,
  \"deep_scan_files\": []
}

DEEP SCAN (for recurrence / repeated errors):
If you are analyzing a recurrence of a previously-fixed bug, you MUST
set deep_scan_needed: true and list specific file paths in deep_scan_files
if the root cause appears to originate from a file not included in the
provided context. The call chain below shows the full execution path.
```

---

## LLM USER PROMPT TEMPLATE

```
PRODUCTION ERROR:
  Type: {error_type}
  Message: {error_message}
  File: {file_path}
  Function: {function_name}
  Line: {line_number}
  Occurrences: {occurrence_count}

STACK TRACE:
{redacted_stack_trace}

SOURCE FILE ({main_file_path}):
{main_file_content}

RELATED FILES:
{for each related file: --- path ---\ncontent\n}

TEST FILE ({test_file_path}):
{test_file_content or "No test file found"}

{extra_context if recurrence: "IMPORTANT: A previous fix was attempted
(PR: {previous_pr_url}) but the same error has reoccurred.
The previous fix was insufficient. Please analyze why
and propose a deeper fix."}

FULL CALL CHAIN (if available):
[1] getUserById() @ src/services/userService.ts:15
    > return users.find(u => u.id === id) ?? null;
[2] getUserProfile() @ src/routes/users.ts:42
    > const name = user.profile.displayName  ← CRASH

Generate the fix following the rules and response format specified.
```

---

## CLASSIFICATION RULES

```
INFRA_SIGNALS (if any of these appear in error_type + error_message
               + stack_trace, classify as "infra"):
  - ECONNREFUSED
  - ETIMEDOUT
  - ECONNRESET
  - 502, 503, 504
  - OOMKilled
  - heap out of memory
  - SIGKILL, SIGTERM
  - connection refused
  - database (when paired with connection/timeout errors)
  - redis (when paired with connection/timeout errors)
  - timeout exceeded
  - certificate
  - DNS

CODE_SIGNALS (classify as "code"):
  - error_type is TypeError
  - error_type is ReferenceError
  - error_type is RangeError
  - error_type is SyntaxError
  - error_type is URIError

DEPENDENCY_SIGNALS (classify as "dependency"):
  - file_path contains "node_modules"

DEFAULT: "unknown" (do not generate fix)
```

---

## REDACTION PATTERNS

Strip these patterns from ALL text before sending to LLM:

```
email:        [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
bearer:       Bearer\s+[A-Za-z0-9\-._~+/]+=*
api_key:      (?:api[_-]?key|apikey|secret|token|password|auth)\s*[=:]\s*["']?[A-Za-z0-9\-._~+/]{16,}
ip_address:   \b(?:\d{1,3}\.){3}\d{1,3}\b
jwt:          eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+
uuid:         [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}
phone:        (?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}
credit_card:  \b(?:\d{4}[-\s]?){3}\d{4}\b
```

Replace each match with: [REDACTED_{PATTERN_NAME}]

---

## CONFIDENCE GATING RULES

| Confidence | Action                                              |
|------------|-----------------------------------------------------|
| high       | Create draft PR                                     |
| medium     | Create draft PR + add "needs-careful-review" label  |
| low        | Do NOT create PR, store recommendation only         |

---

## FINGERPRINT DEDUP RULES

- fingerprint = sha256(error_type + file_path + function_name)
- If fingerprint exists AND status is "pr_created":
    → increment count, do nothing
- If fingerprint exists AND status is "pr_merged":
    → mark as "fix_ineffective", re-trigger pipeline
- If fingerprint exists AND status is "ignored":
    → increment count, do nothing
- If fingerprint is new:
    → create record, trigger pipeline
- Cooldown: do not re-trigger same fingerprint within 10 minutes

---

## PR CREATION RULES

- Branch naming: slothops/fix-{file-path-slugified}-{issue-id-first-8-chars}
- Always create DRAFT PR, never ready-for-review
- Always target "main" branch
- PR body must include:
    - Root cause analysis
    - Confidence badge
    - Error metadata table (type, message, file, function, line, count)
    - Per-file change explanations
    - Footer warning that this is auto-generated
- Never auto-merge
- Never force-push
- One PR per fingerprint maximum

---

## API ENDPOINTS

| Method | Path                          | Auth?   | Description                                 |
|--------|-------------------------------|---------|---------------------------------------------|
| POST   | /webhook/sentry/{workspace_id}| No      | Receives Sentry webhook alerts (per-tenant) |
| POST   | /webhook/github               | No      | Receives GitHub App installation events     |
| POST   | /api/signup                   | No      | Create workspace + user account             |
| POST   | /api/login                    | No      | Authenticate and receive JWT                |
| POST   | /api/github/link              | Bearer  | Link GitHub App installation to workspace   |
| GET    | /issues                       | Bearer  | List workspace-scoped tracked issues        |
| GET    | /issues/{id}                  | Bearer  | Get single issue detail                     |
| GET    | /stream                       | Token   | SSE stream for dashboard (token via query)  |
| GET    | /health                       | No      | Health check                                |
| GET    | /                             | No      | Serve dashboard HTML                        |

---

## ENVIRONMENT VARIABLES

```
GEMINI_API_KEY=AIza...              # Google AI Studio API key
GITHUB_APP_ID=123456                # GitHub App numeric ID
GITHUB_APP_PRIVATE_KEY=-----BEGIN...# GitHub App .pem private key (inline or file path)
JWT_SECRET=your-secret-key-here     # HMAC key for PyJWT (min 32 bytes recommended)
SENTRY_WEBHOOK_SECRET=whsec_...     # (optional) for signature verification
DATABASE_PATH=./slothops.db
PORT=8000
LOG_LEVEL=INFO
```

> **DEPRECATED:** `GITHUB_TOKEN` and `GITHUB_REPO` are no longer used.
> Repository access is handled dynamically via the GitHub App installation tokens.

---

## IMPORTANT CONSTRAINTS FOR AI ASSISTANTS

When helping develop SlothOps:

1. Keep all modules in separate files. Do not merge into monolith.
2. Use Pydantic models for all data validation.
3. Use async/await throughout FastAPI handlers.
4. Handle GitHub API rate limits gracefully.
5. Always redact before logging or sending to LLM.
6. Never store raw Sentry payloads with PII in the database
   without redaction.
7. The dashboard uses Server-Sent Events, not WebSockets.
8. SQLite is sufficient. Do not suggest PostgreSQL or Redis
   for the MVP.
9. The target demo app is a SEPARATE repo from the engine.
10. All GitHub operations use PyGithub library, not raw HTTP.
11. Error handling in the pipeline should be granular:
    if LLM fails, status = "fixing_failed"
    if GitHub API fails, status = "pr_creation_failed"
    Do not use catch-all exception handlers.
12. The LLM response MUST be parsed as JSON.
    If parsing fails, retry once. If it fails again,
    mark issue as "fixing_failed".

---

## MVP BUG CATEGORIES (what the system handles)

For this MVP, SlothOps handles TypeScript/JavaScript:
- TypeError: Cannot read properties of undefined/null
- Unhandled promise rejections
- Missing null/undefined guards on API response data
- Array method calls on non-array values
- Shared state / cache poisoning mutations
- Missing try/catch around throwing synchronous calls

It does NOT handle:
- Logic bugs with no runtime error
- Performance issues
- Memory leaks
- Race conditions
- CSS/UI bugs
- Build/compilation errors
- Infrastructure failures (these are classified and logged with DevOps recommendations)

---

## TESTING EXPECTATIONS

The engine itself should have tests for:
- classifier.py: infra vs code vs dependency classification
- redactor.py: PII stripping works correctly
- fingerprint.py: same errors produce same fingerprint
- sentry_parser.py: correct frame extraction from payload

The demo app should have:
- Basic route tests that currently PASS
- The bugs should be in code paths not covered by tests
  (so the existing test suite passes on main branch)
- When SlothOps fixes a bug, the fix should not break
  existing tests

---

## DEMO SCENARIOS

Scenario 1 — NULL REFERENCE (happy path):
  Trigger: GET /users/999/profile (user with null profile)
  Expected: TypeError captured → classified as code →
            fix generated → draft PR opened

Scenario 2 — ARRAY ON UNDEFINED:
  Trigger: GET /orders/ORD-999/subtotal (order with no items array)
  Expected: TypeError → code → fix with default empty array

Scenario 3 — UNHANDLED JWT CRASH:
  Trigger: GET /orders/ORD-001 with header `Authorization: Bearer garbage`
  Expected: JsonWebTokenError → code → fix wraps jwt.verify in try/catch

Scenario 4 — FLOATING ASYNC PROMISE:
  Trigger: GET /sync/batch
  Expected: Unhandled rejection → code → fix replaces forEach with Promise.all

Scenario 5 — CACHE POISONING / SHARED MUTATION:
  Trigger: GET /config/theme?forceDark=bad_string then GET /config/theme
  Expected: TypeError on second request → code → fix uses local variable

Scenario 6 — INFRA ERROR (classification demo):
  Trigger: Kill the database, then hit any endpoint
  Expected: ECONNREFUSED → classified as infra →
            no PR created, DevOps recommendation logged

Scenario 7 — RECURRENCE (closed-loop demo):
  Trigger: Merge a PR from above, then re-trigger the same bug
  Expected: Same fingerprint detected → previous fix marked
            ineffective → new PR with deeper analysis

---

## PHASE 5: SAAS MULTI-TENANT ✅ COMPLETED

1. **Authentication:** Pure Python `bcrypt` + `PyJWT` implementation. Native frontend login/signup flows.
2. **Multi-Tenant DB:** SQLite schemas (`workspaces`, `users`, `integrations`). All issues scoped by `workspace_id`.
3. **GitHub App:** `@slothops-bot` fully integrated via `POST /webhook/github`. Dynamic repo targeting via `installation.get_repos()`.

---

## PHASE 6: QA PIPELINE + TECH STACK DETECTION + PRE-MERGE GATE

### Overview
SlothOps now intercepts Pull Requests **before merge** and runs a full QA pipeline:
- Static Analysis, Functionality Testing (LLM-generated), VAPT, Stress Testing, Regression, Performance
- Sets a GitHub Commit Status (`SlothOps QA`) that **blocks the merge button** until QA passes
- Automatically detects the repository's tech stack (or reads `.slothops.yml`)

### QA Pipeline Flow
```
Developer opens PR → GitHub webhook fires (opened/synchronize)
  → SlothOps receives webhook
  → Sets commit status to PENDING ⏳
  → Clones repo in temp sandbox
  → detect_stack() identifies language/framework/commands
  → Installs dependencies via detected install_command
  → LangChain AgentExecutor picks which sub-agents to run:
     ├─ StaticAnalysis    (ESLint, TSC, flake8, clippy, etc.)
     ├─ FunctionalityTest (LLM generates + runs unit tests)
     ├─ VAPTScan          (npm audit, pip-audit, cargo audit, govulncheck)
     ├─ StressTesting     (autocannon load test)
     ├─ RegressionTest    (run existing test suite)
     └─ PerformanceCheck  (endpoint response time baseline)
  → Aggregates results → Sets commit status:
     SUCCESS ✅ = merge allowed
     FAILURE ❌ = merge blocked
  → Posts QA report as PR comment
  → Sends email summary (if configured)

Developer fixes code → Pushes → QA re-runs automatically
OR → Developer clicks "Bypass" on SlothOps dashboard → Merge unblocked
```

### Tech Stack Detection (`stack_detector.py`)
Auto-detects from repo marker files:

| Marker File | Detected Stack |
|---|---|
| `package.json` + `tsconfig.json` | TypeScript/Node |
| `package.json` (no TS) | JavaScript/Node |
| `requirements.txt` + `manage.py` | Python/Django |
| `requirements.txt` + Flask import | Python/Flask |
| `requirements.txt` (generic) | Python |
| `go.mod` | Go |
| `pom.xml` | Java/Maven |
| `build.gradle` | Java/Gradle |
| `Cargo.toml` | Rust |

**Optional override:** Place `.slothops.yml` at repo root:
```yaml
stack: node
start: npm start
test: npm test
lint: npx eslint .
port: 3000
```

### New QA Files
```
slothops-engine/
├── qa_pipeline.py              # LangChain-orchestrated QA pipeline + commit status
├── stack_detector.py           # Auto-detect tech stack + .slothops.yml merge
├── email_sender.py             # HTML QA report email via SMTP
├── qa_agents/
│   ├── __init__.py
│   ├── static_analysis.py      # Linters + type checkers per stack
│   ├── functionality.py        # LLM-generated unit tests
│   ├── vapt.py                 # Dependency vulnerability audit
│   ├── stress_test.py          # autocannon load testing
│   ├── regression.py           # Native test suite runner
│   └── performance.py          # Response time baselines
```

### QA Pipeline API Endpoints
| METHOD | PATH | Description |
|---|---|---|
| `POST` | `/webhook/github` | Receives PR events, triggers QA on `opened`/`synchronize` |
| `GET` | `/api/qa-reports` | List QA reports for workspace |
| `GET` | `/api/qa-reports/{id}` | Get single QA report |
| `POST` | `/api/qa-bypass/{id}` | Bypass failed QA (sets commit status to success) |

### Environment Variables (QA)
| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Required for LLM-powered test generation |
| `SMTP_HOST` | Optional, for email reports |
| `SMTP_PORT` | Default: 587 |
| `SMTP_USER` | SMTP login |
| `SMTP_PASSWORD` | SMTP password |
| `QA_EMAIL_RECIPIENT` | Who receives QA emails |

### QA Database Schema
```sql
CREATE TABLE qa_reports (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    pr_number INTEGER,
    pr_url TEXT,
    commit_sha TEXT,
    repo_name TEXT,
    overall_status TEXT DEFAULT 'running',
    summary TEXT,
    static_analysis TEXT,
    functionality TEXT,
    vapt TEXT,
    stress_test TEXT,
    regression TEXT,
    performance TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Branch Protection Setup
To enforce the pre-merge gate, enable **"Require status checks to pass"** in GitHub Branch Rules and add **`SlothOps QA`** as a required check.

---

## PHASE 7: PRODUCTION AUTO-ROLLBACK & RESOLUTION ✅ COMPLETED

### Overview
If a bug merges to `main` and breaks the production build (e.g. Vercel deployment fails), SlothOps catches the GitHub `deployment_status` webhook and rescues production automatically. It then tries to fix the failed branch using the LLM and creates an Auto-Fix PR.

### The Flow
1. **Detection:** GitHub sends a `deployment_status` webhook with `state: failure` on the `main` branch.
2. **Rollback (`rollback.py`):**
   - SlothOps clones the repo in a sandbox.
   - Creates a backup branch `slothops/backup-<sha>`.
   - Runs `git revert <sha>` on `main` to undo the broken commit gracefully.
   - Pushes the reverted `main` back to GitHub, restoring production.
   - **Loop Prevention:** If the failing commit's message starts with `"Revert"`, SlothOps aborts the rollback to prevent infinite revert loops.
3. **Resolution (`resolution.py`):**
   - After rollback, SlothOps triggers `attempt_resolution()` asynchronously.
   - It fetches the broken code from the `slothops/backup-<sha>` branch.
   - LLM analyzes the deployment failure logs and code to generate a fix.
   - The fix is committed to `slothops/backup-<sha>`.
   - A new Draft PR is opened targeting `main`.
4. **Re-Cycle (Self-Healing):**
   - If the Vercel build for the Auto-Fix PR fails *again*, SlothOps catches the new `deployment_status` failure strictly for that `slothops/backup-*` branch.
   - It re-triggers `attempt_resolution()` recursively (up to 3 max attempts) to try fixing its own mistakes.

### New API & DB
- Database: `rollbacks` and `resolutions` tables with lifecycle tracking.
- Endpoints: `GET /api/rollbacks` for the frontend to render rollback cards with nested resolution attempts.
- SSE: `rollback_event` and `resolution_event` for live UI updates.

---
## END OF AI CONTEXT

