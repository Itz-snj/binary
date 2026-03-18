# SlothOps

> **Production-aware automated bug remediation.** SlothOps watches your app for crashes via Sentry, fetches the relevant source code from GitHub, asks GPT-4o to fix it, and opens a Draft PR — all before a developer wakes up.

```
Sentry alert → AI reads the code → Draft PR waiting for you
```

---

## Repos in This Monorepo

| Folder | Language | Purpose |
|---|---|---|
| `slothops-engine/` | Python 3.11 + FastAPI | The bot: webhook receiver, pipeline, LLM, GitHub automation |
| `slothops-demo-app/` | Node.js + TypeScript | Target app with 3 intentional bugs for demo |

---

## How It Works (10-second version)

1. A bug crashes in the demo app → Sentry fires a webhook
2. The engine receives it, strips PII, fingerprints the error
3. If it's a **code** bug (not infra), it fetches the failing source file from GitHub
4. GPT-4o generates a fix with root cause analysis
5. If confidence is **high/medium**, a Draft PR is opened automatically
6. Dashboard shows the issue moving through each stage in real-time

---

## Detailed Pipeline Walkthrough

| Step | File | What it does |
|---|---|---|
| 1 | `main.py` | Receives `POST /webhook/sentry`, returns 200, spawns async task |
| 2 | `sentry_parser.py` | Extracts error type, message, file, function, line from payload |
| 3 | `redactor.py` | Strips PII (emails, IPs, tokens, JWTs) before anything touches LLM |
| 4 | `fingerprint.py` | `sha256(error_type + file_path + function_name)` — dedup check |
| 5 | `database.py` | Creates/updates issue record in SQLite via `aiosqlite` |
| 6 | `classifier.py` | `code` / `infra` / `dependency` / `unknown` — only `code` proceeds |
| 7 | `code_fetcher.py` | Downloads failing file + test file + imports via PyGithub |
| 8 | `llm_fixer.py` | Builds prompt, calls GPT-4o (temp 0.2, JSON mode), parses response |
| 9 | `github_automation.py` | Creates branch, commits fix, opens Draft PR |
| 10 | `sse_manager.py` | Broadcasts status updates to dashboard at each stage |

---

## Deploying the Engine (Sentry Webhook URL)

### Option A — ngrok (local dev, free)
```bash
ngrok http 8000
# Set Sentry webhook to: https://<hash>.ngrok.io/webhook/sentry
# Note: URL changes on every ngrok restart (free tier)
```

### Option B — Vercel (recommended for hackathon demo)
> ⚠️ The engine is a **FastAPI app** (WSGI/ASGI), not a static site.  
> You can deploy it to Vercel using the `@vercel/python` runtime with a `vercel.json` adapter.  
> This gives you a **stable, persistent URL** — ideal for Sentry webhooks.

```json
// vercel.json (place in slothops-engine/)
{
  "builds": [{ "src": "main.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/(.*)", "dest": "main.py" }]
}
```

Set environment variables in Vercel dashboard (same as `.env`):  
`OPENAI_API_KEY`, `GITHUB_TOKEN`, `GITHUB_REPO`, `DATABASE_PATH`, etc.

Sentry webhook URL becomes: `https://your-project.vercel.app/webhook/sentry` — **stable forever**.

> 💡 **SQLite note:** Vercel's filesystem is ephemeral. For demo purposes this is fine (data resets on redeploy). For persistence, swap to a free [Turso](https://turso.tech) SQLite-compatible DB.

### Option C — Railway / Render (easiest persistent backend)
Both support Python/FastAPI with a stable URL and persistent disk. One-click deploys from GitHub.

---

## Quick Start

### Engine
```bash
cd slothops-engine
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
uvicorn main:app --reload --port 8000
```

### Demo App
```bash
cd slothops-demo-app
npm install
cp .env.example .env   # fill in SENTRY_DSN
npm run dev
```

### Trigger a bug manually (no live Sentry needed)
```bash
curl -X POST http://localhost:8000/webhook/sentry \
  -H "Content-Type: application/json" \
  -d @slothops-engine/tests/fixtures/sentry_webhook.json
```

---

## Environment Variables

| Variable | Where | Description |
|---|---|---|
| `OPENAI_API_KEY` | engine | GPT-4o access |
| `GITHUB_TOKEN` | engine | PAT with `repo` + `write:discussion` scopes |
| `GITHUB_REPO` | engine | `org/slothops-demo-app` |
| `DATABASE_PATH` | engine | Default: `./slothops.db` |
| `PORT` | engine | Default: `8000` |
| `SENTRY_WEBHOOK_SECRET` | engine | Optional signature verification |
| `SENTRY_DSN` | demo-app | From Sentry project settings |

---

## Demo Scenarios

| # | Scenario | How to trigger | Expected outcome |
|---|---|---|---|
| 1 | Null reference | `GET /users/999/profile` | Draft PR with optional chaining fix |
| 2 | Infra error | Kill database, hit any endpoint | Logged as `infra`, no PR |
| 3 | Recurrence | Merge PR from #1, re-trigger same error | `fix_ineffective` → new deeper PR |

---

## Definition of Done

- [ ] Buggy endpoint triggers Sentry
- [ ] Sentry webhook reaches FastAPI
- [ ] Error classified correctly (code vs infra)
- [ ] Source file fetched from GitHub
- [ ] LLM generates fix with root cause
- [ ] Draft PR opens on GitHub
- [ ] GitHub Actions CI passes on PR
- [ ] Dashboard shows real-time stage updates
- [ ] Duplicate errors don't create duplicate PRs
- [ ] Infra errors classified and skipped
- [ ] All 3 demo bugs produce valid fixes
- [ ] Unit tests pass (classifier, redactor, fingerprint, parser)
