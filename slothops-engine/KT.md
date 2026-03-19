# SlothOps Engine — Knowledge Transfer (KT)

A quick reference for every file in `slothops-engine/`.
Read this to understand **what each file does** and **how they connect**.

---

## Project Setup Files

### `requirements.txt`
All Python dependencies pinned to specific versions. Install with:
```bash
pip install -r requirements.txt
```

### `.env.example`
Template for environment variables. Copy to `.env` and fill in your real keys before running the server. Three are **required** (`OPENAI_API_KEY`, `GITHUB_TOKEN`, `GITHUB_REPO`); the rest have sensible defaults.

### `config.py`
Loads `.env` via `python-dotenv` and exports typed constants. If a required key is missing, it raises a `RuntimeError` at import time — you'll know immediately rather than hitting a `None` somewhere deep in the pipeline.

---

## Data Layer

### `models.py`
The **single source of truth** for data shapes. Contains:
- **`IssueRecord`** — the central Pydantic model. Every pipeline module reads and writes this object. Fields map 1:1 to the SQLite `issues` table.
- **`LLMFixResponse`** / **`FileChange`** — models for parsing the GPT-4o JSON response.
- **Enums** — `Classification` (code/infra/dependency/unknown), `Confidence` (high/medium/low), `IssueStatus` (received → pr_created → pr_merged → ...), `DedupeAction` (create/skip/retrigger).

### `database.py`
Async SQLite wrapper using `aiosqlite`. Provides:
- `init_db()` — creates the `issues` table and indexes (safe to call repeatedly).
- `create_issue()` — inserts a new record.
- `get_issue()` / `get_issue_by_fingerprint()` — lookups.
- `update_issue_status()` — partial update (any columns via kwargs).
- `increment_occurrence()` — bumps the count for duplicate events.
- `list_issues()` — returns all issues (newest first).

Every function takes a `db_path` parameter so tests can point to a temp database.

---

## Pure Logic Modules (no external APIs)

### `redactor.py`
Regex-based PII stripper. Scans text for 8 patterns (email, bearer token, API key, IP, JWT, UUID, phone, credit card) and replaces them with `[REDACTED_EMAIL]`, `[REDACTED_JWT]`, etc.

**Important:** Patterns are applied in priority order — JWT is checked before UUID because JWT strings contain segments that look like UUIDs.

### `classifier.py`
Heuristic error classifier. Examines `error_type`, `error_message`, `stack_trace`, and `file_path` against three signal lists:
1. **Infra signals** (ECONNREFUSED, ETIMEDOUT, 502/503/504, OOMKilled, etc.) — some like "database" only trigger when paired with connection/timeout keywords.
2. **Code signals** — error_type is one of TypeError, ReferenceError, RangeError, SyntaxError, URIError.
3. **Dependency signals** — `node_modules` appears in the file path.
4. **Default** — "unknown" (no fix generated).

### `fingerprint.py`
Two functions:
- **`compute_fingerprint()`** — SHA-256 hash of `error_type + file_path + function_name`. Same bug = same hash.
- **`check_dedup()`** — Given an existing issue's status, decides:  CREATE (new), SKIP (already handled), or RETRIGGER (merged fix didn't work). Enforces a 10-minute cooldown to prevent spam.

### `sentry_parser.py`
Parses Sentry's webhook JSON into an `IssueRecord`. Key logic:
- Walks `event.exception.values[*].stacktrace.frames`
- Filters out `node_modules` frames
- Picks the **last** application frame (top of the call stack)
- Extracts `error_type`, `error_message`, `file_path`, `function_name`, `line_number`
- Builds a readable stack trace string
- Assigns a new UUID as the issue `id`

---

## Tests

### `tests/fixtures/sentry_webhook.json`
A realistic Sentry webhook payload matching the Bug 1 scenario (null user profile crash). Contains both `node_modules` and application frames.

### `tests/test_classifier.py`
Tests all classification paths: infra signals (14 cases), code signals (5 error types), dependency (node_modules path), and unknown fallback.

### `tests/test_redactor.py`
Tests each of the 8 redaction patterns plus edge cases (clean text, empty string, `None` input).

### `tests/test_fingerprint.py`
Tests hash determinism, uniqueness, SHA-256 format, `None` handling, and the full dedup decision matrix including the 10-minute cooldown.

### `tests/test_sentry_parser.py`
Tests fixture parsing (all fields extracted correctly), `node_modules` frame filtering, and edge cases (empty payload, missing exception key).

---

## How Everything Connects

```
Sentry webhook JSON
       │
       ▼
 sentry_parser.py  →  IssueRecord (models.py)
       │
       ▼
   redactor.py     →  strips PII from stack_trace
       │
       ▼
  fingerprint.py   →  computes hash, checks dedup via database.py
       │
       ▼
  classifier.py    →  sets classification field
       │
       ▼
   database.py     →  persists to SQLite
       │
   (Phase 2: code_fetcher → llm_fixer → github_automation)
```

---

## Running Tests

```bash
cd slothops-engine
pip install -r requirements.txt
python -m pytest tests/ -v
```

All 4 test files should pass with **zero API keys required**.
