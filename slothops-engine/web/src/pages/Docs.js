import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from "react";
import { Link } from "react-router-dom";
// ── Nav tree ─────────────────────────────────────────────────────────────────
const NAV = [
    {
        label: "Getting Started",
        items: [
            { id: "overview", label: "Overview" },
            { id: "quickstart", label: "Quick Start (Docker)" },
            { id: "devmode", label: "Dev Mode (no Docker)" },
            { id: "configuration", label: "Configuration" },
        ],
    },
    {
        label: "API Reference",
        items: [
            { id: "api-auth", label: "Auth" },
            { id: "api-dashboard", label: "Dashboard" },
            { id: "api-repos", label: "Repos" },
            { id: "api-qa", label: "QA Reports" },
            { id: "api-rollbacks", label: "Rollbacks" },
            { id: "api-health", label: "Health" },
        ],
    },
    {
        label: "Architecture",
        items: [
            { id: "webhooks", label: "Webhooks" },
            { id: "pipelines", label: "Pipeline Flows" },
        ],
    },
    {
        label: "Open Source",
        items: [
            { id: "contributing", label: "Contributing" },
        ],
    },
];
// ── Primitive components ─────────────────────────────────────────────────────
function Code({ children }) {
    return (_jsx("code", { style: {
            fontFamily: "monospace",
            fontSize: "0.85rem",
            backgroundColor: "#1a1a1a",
            border: "1px solid #2a2a2a",
            borderRadius: 4,
            padding: "2px 6px",
            color: "#c084fc",
        }, children: children }));
}
function CodeBlock({ children, lang = "bash" }) {
    const [copied, setCopied] = useState(false);
    const copy = () => {
        navigator.clipboard.writeText(children);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };
    return (_jsx("div", { style: { position: "relative", marginBottom: 24 }, children: _jsxs("div", { style: {
                backgroundColor: "#111",
                border: "1px solid #2a2a2a",
                borderRadius: 8,
                overflow: "hidden",
            }, children: [_jsxs("div", { style: {
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "8px 16px",
                        borderBottom: "1px solid #2a2a2a",
                        backgroundColor: "#161616",
                    }, children: [_jsx("span", { style: { fontFamily: "monospace", fontSize: "0.7rem", color: "#555", textTransform: "uppercase", letterSpacing: 1 }, children: lang }), _jsx("button", { onClick: copy, style: {
                                all: "unset",
                                cursor: "pointer",
                                fontFamily: "monospace",
                                fontSize: "0.7rem",
                                color: copied ? "#4ade80" : "#555",
                                transition: "color 0.2s",
                            }, children: copied ? "copied!" : "copy" })] }), _jsx("pre", { style: {
                        margin: 0,
                        padding: "16px",
                        fontFamily: "monospace",
                        fontSize: "0.85rem",
                        lineHeight: 1.65,
                        color: "#d4d4d8",
                        overflowX: "auto",
                        whiteSpace: "pre",
                    }, children: children })] }) }));
}
function MethodBadge({ method }) {
    const COLORS = {
        GET: "#2563eb",
        POST: "#16a34a",
        PUT: "#d97706",
        PATCH: "#7c3aed",
        DELETE: "#dc2626",
    };
    return (_jsx("span", { style: {
            display: "inline-block",
            padding: "2px 8px",
            borderRadius: 4,
            backgroundColor: COLORS[method] + "22",
            border: `1px solid ${COLORS[method]}44`,
            color: COLORS[method],
            fontFamily: "monospace",
            fontSize: "0.75rem",
            fontWeight: 700,
            letterSpacing: 0.5,
            marginRight: 10,
        }, children: method }));
}
function Endpoint({ method, path, auth = true, description, body, response, }) {
    const [open, setOpen] = useState(false);
    return (_jsxs("div", { style: {
            border: "1px solid #2a2a2a",
            borderRadius: 8,
            marginBottom: 12,
            overflow: "hidden",
            backgroundColor: "#0d0d0d",
        }, children: [_jsxs("button", { onClick: () => setOpen(o => !o), style: {
                    all: "unset",
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    padding: "12px 16px",
                    cursor: "pointer",
                    gap: 0,
                }, children: [_jsx(MethodBadge, { method: method }), _jsx("code", { style: { fontFamily: "monospace", fontSize: "0.9rem", color: "#e2e2e2", flex: 1 }, children: path }), auth && (_jsx("span", { style: { fontSize: "0.7rem", color: "#555", marginRight: 12, fontFamily: "monospace" }, children: "\uD83D\uDD12 auth" })), _jsx("span", { style: { color: "#555", fontSize: "0.75rem" }, children: open ? "▲" : "▼" })] }), open && (_jsxs("div", { style: { padding: "16px", borderTop: "1px solid #2a2a2a" }, children: [_jsx("p", { style: { color: "#a1a1aa", fontSize: "0.9rem", margin: "0 0 16px" }, children: description }), body && (_jsxs(_Fragment, { children: [_jsx("p", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#555", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }, children: "Request Body" }), _jsx(CodeBlock, { lang: "json", children: body })] })), response && (_jsxs(_Fragment, { children: [_jsx("p", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#555", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }, children: "Response" }), _jsx(CodeBlock, { lang: "json", children: response })] }))] }))] }));
}
function SectionHeading({ title, subtitle }) {
    return (_jsxs("div", { style: { marginBottom: 32, paddingBottom: 20, borderBottom: "1px solid #1f1f1f" }, children: [_jsx("h1", { style: { fontFamily: "monospace", fontSize: "1.9rem", fontWeight: 700, margin: 0, letterSpacing: "-0.5px" }, children: title }), subtitle && _jsx("p", { style: { color: "#71717a", fontSize: "1rem", margin: "8px 0 0", lineHeight: 1.6 }, children: subtitle })] }));
}
function H2({ children }) {
    return _jsx("h2", { style: { fontFamily: "monospace", fontSize: "1.2rem", fontWeight: 600, margin: "36px 0 16px", color: "#e4e4e7" }, children: children });
}
function Note({ children }) {
    return (_jsx("div", { style: {
            border: "1px solid #2a2a2a",
            borderLeft: "3px solid #9333ea",
            backgroundColor: "rgba(147, 51, 234, 0.05)",
            borderRadius: "0 8px 8px 0",
            padding: "12px 16px",
            marginBottom: 20,
            fontSize: "0.9rem",
            color: "#a1a1aa",
            lineHeight: 1.6,
        }, children: children }));
}
function ConfigRow({ name, required, description, example }) {
    return (_jsxs("tr", { children: [_jsxs("td", { style: { padding: "12px 16px", fontFamily: "monospace", fontSize: "0.85rem", color: "#c084fc", verticalAlign: "top" }, children: [name, required && _jsx("span", { style: { marginLeft: 6, fontSize: "0.65rem", color: "#ef4444", textTransform: "uppercase" }, children: "required" })] }), _jsx("td", { style: { padding: "12px 16px", color: "#a1a1aa", fontSize: "0.85rem", lineHeight: 1.5, verticalAlign: "top" }, children: description }), _jsx("td", { style: { padding: "12px 16px", fontFamily: "monospace", fontSize: "0.8rem", color: "#555", verticalAlign: "top" }, children: example })] }));
}
// ── Sections ─────────────────────────────────────────────────────────────────
function Overview() {
    return (_jsxs(_Fragment, { children: [_jsx(SectionHeading, { title: "SlothOps Engine", subtitle: "A closed-loop, production-aware automation engine that converts live application crashes into reviewed code fixes." }), _jsx("p", { style: { color: "#a1a1aa", lineHeight: 1.75, marginBottom: 20 }, children: "SlothOps sits between your observability layer (Sentry) and your source control (GitHub). When an exception fires in production, SlothOps:" }), _jsxs("ol", { style: { color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }, children: [_jsx("li", { children: "Receives the Sentry webhook, deduplicates and fingerprints the issue." }), _jsx("li", { children: "Fetches the exact source code context from GitHub." }), _jsx("li", { children: "Generates a targeted fix using an LLM with a configurable provider chain." }), _jsx("li", { children: "Opens a pull request with the fix and a full explanation." }), _jsx("li", { children: "Runs 6 automated QA agents against the fix PR." }), _jsx("li", { children: "If the deploy fails, plans or executes a governed rollback." })] }), _jsx(Note, { children: "No environment API keys are strictly required to start the engine. The LLM and GitHub flows are skipped gracefully when keys are absent \u2014 useful for local exploration." }), _jsx(H2, { children: "Stack" }), _jsx("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 24 }, children: [
                    ["Backend", "FastAPI · SQLModel · asyncpg · Alembic"],
                    ["Database", "PostgreSQL 16"],
                    ["Frontend", "React 18 · Vite · TanStack Query · React Router"],
                    ["LLM", "Provider chain (Groq / Together / Mistral / OpenRouter / …)"],
                    ["Integrations", "GitHub App · Sentry webhooks · SMTP"],
                    ["Infra", "Docker Compose · multi-stage build"],
                ].map(([label, value]) => (_jsxs("div", { style: { padding: "14px 16px", border: "1px solid #2a2a2a", borderRadius: 8, backgroundColor: "#0d0d0d" }, children: [_jsx("div", { style: { fontFamily: "monospace", fontSize: "0.7rem", color: "#555", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }, children: label }), _jsx("div", { style: { fontSize: "0.88rem", color: "#d4d4d8" }, children: value })] }, label))) })] }));
}
function QuickStart() {
    return (_jsxs(_Fragment, { children: [_jsx(SectionHeading, { title: "Quick Start (Docker)", subtitle: "Bring the full stack up in one command. Requires Docker Desktop 27+." }), _jsx(H2, { children: "1. Clone & configure" }), _jsx(CodeBlock, { lang: "bash", children: `git clone https://github.com/your-org/slothops-engine
cd slothops-engine
cp .env.example .env   # fill in API keys (optional for exploration)` }), _jsx(H2, { children: "2. Spin up" }), _jsx(CodeBlock, { lang: "bash", children: `docker compose up --build` }), _jsx("p", { style: { color: "#a1a1aa", lineHeight: 1.75, marginBottom: 20 }, children: "What happens under the hood:" }), _jsxs("ol", { style: { color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }, children: [_jsx("li", { children: "Postgres 16 starts; healthcheck waits until it accepts connections." }), _jsxs("li", { children: [_jsx(Code, { children: "web-builder" }), " stage \u2014 Bun installs ", _jsx(Code, { children: "web/package.json" }), " and runs ", _jsx(Code, { children: "bun run build" }), ", producing ", _jsx(Code, { children: "web/dist/" }), "."] }), _jsxs("li", { children: [_jsx(Code, { children: "runtime" }), " stage \u2014 Python 3.13 slim, pip installs ", _jsx(Code, { children: "requirements.txt" }), ", copies source."] }), _jsxs("li", { children: ["Container CMD runs ", _jsx(Code, { children: "alembic upgrade head" }), " then ", _jsx(Code, { children: "uvicorn main:app" }), "."] })] }), _jsx(H2, { children: "3. Verify" }), _jsx(CodeBlock, { lang: "bash", children: `# Health
curl http://localhost:8000/health

# Create an account
curl -X POST http://localhost:8000/api/auth/signup \\
  -H 'content-type: application/json' \\
  -d '{"email":"you@example.com","password":"hunter2","workspace_name":"demo"}'

# Store the token
export TOKEN=<access_token from above>

# Dashboard
curl http://localhost:8000/api/dashboard/overview \\
  -H "authorization: Bearer $TOKEN"` }), _jsx(H2, { children: "Useful URLs" }), _jsx("div", { style: { overflowX: "auto", marginBottom: 24 }, children: _jsxs("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }, children: [_jsx("thead", { children: _jsxs("tr", { style: { borderBottom: "1px solid #2a2a2a" }, children: [_jsx("th", { style: { padding: "10px 16px", textAlign: "left", fontFamily: "monospace", color: "#555", fontWeight: 500, fontSize: "0.75rem", textTransform: "uppercase" }, children: "URL" }), _jsx("th", { style: { padding: "10px 16px", textAlign: "left", fontFamily: "monospace", color: "#555", fontWeight: 500, fontSize: "0.75rem", textTransform: "uppercase" }, children: "What" })] }) }), _jsx("tbody", { children: [
                                ["http://localhost:8000/", "React dashboard"],
                                ["http://localhost:8000/docs", "Swagger UI (OpenAPI)"],
                                ["http://localhost:8000/health", "Engine liveness"],
                                ["http://localhost:8000/stream?token=…", "SSE log + issue events"],
                                ["http://localhost:8000/webhook/sentry/{ws_id}", "Sentry webhook receiver"],
                                ["http://localhost:8000/webhook/github", "GitHub App webhook receiver"],
                                ["postgres://slothops:slothops_dev@localhost:5432/slothops", "PostgreSQL (dev creds)"],
                            ].map(([url, what]) => (_jsxs("tr", { style: { borderBottom: "1px solid #1a1a1a" }, children: [_jsx("td", { style: { padding: "10px 16px", fontFamily: "monospace", fontSize: "0.82rem", color: "#c084fc" }, children: url }), _jsx("td", { style: { padding: "10px 16px", color: "#a1a1aa", fontSize: "0.88rem" }, children: what })] }, url))) })] }) })] }));
}
function DevMode() {
    return (_jsxs(_Fragment, { children: [_jsx(SectionHeading, { title: "Dev Mode (no Docker)", subtitle: "Postgres stays in Docker; engine and React dev server run on the host for fast reloads." }), _jsx(H2, { children: "1. Start Postgres only" }), _jsx(CodeBlock, { lang: "bash", children: `docker compose up -d postgres` }), _jsx(H2, { children: "2. Run the engine" }), _jsx(CodeBlock, { lang: "bash", children: `python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000` }), _jsxs(Note, { children: [_jsx(Code, { children: "--reload" }), " watches every ", _jsx(Code, { children: ".py" }), " file in the project. Each save is picked up in under a second \u2014 no container rebuild needed."] }), _jsx(H2, { children: "3. Run the React dev server" }), _jsx(CodeBlock, { lang: "bash", children: `cd web
bun install
bun run dev    # http://localhost:5173 — proxies /api/* to :8000` }), _jsx(H2, { children: "Migrations" }), _jsx(CodeBlock, { lang: "bash", children: `alembic upgrade head                         # apply pending migrations
alembic revision --autogenerate -m "add X"   # generate migration from model changes
alembic downgrade -1                         # roll back one revision` }), _jsxs("p", { style: { color: "#a1a1aa", fontSize: "0.9rem", lineHeight: 1.7 }, children: ["Alembic targets ", _jsx(Code, { children: "DIRECT_DATABASE_URL" }), " (the ", _jsx(Code, { children: "psycopg" }), " sync driver). The async ", _jsx(Code, { children: "DATABASE_URL" }), " (asyncpg) is used by the engine at runtime."] })] }));
}
function Configuration() {
    return (_jsxs(_Fragment, { children: [_jsx(SectionHeading, { title: "Configuration", subtitle: "Environment variables read from .env at the repo root." }), _jsxs(Note, { children: ["Copy ", _jsx(Code, { children: ".env.example" }), " \u2192 ", _jsx(Code, { children: ".env" }), " and fill in what you need. The engine starts without any keys set; features that require a missing key are skipped gracefully."] }), [
                {
                    category: "Database",
                    rows: [
                        { name: "DATABASE_URL", required: true, description: "asyncpg URL used by the engine at runtime.", example: "postgresql+asyncpg://slothops:slothops_dev@localhost:5432/slothops" },
                        { name: "DIRECT_DATABASE_URL", required: true, description: "psycopg (sync) URL used by Alembic migrations.", example: "postgresql+psycopg://slothops:slothops_dev@localhost:5432/slothops" },
                    ],
                },
                {
                    category: "Auth",
                    rows: [
                        { name: "JWT_SECRET", required: true, description: "Signing key for dashboard JWTs. Change this in any non-local environment.", example: "change-me-in-prod" },
                    ],
                },
                {
                    category: "GitHub App",
                    rows: [
                        { name: "GITHUB_APP_ID", description: "Numeric App ID from GitHub → Settings → Developer settings.", example: "123456" },
                        { name: "GITHUB_APP_PRIVATE_KEY", description: "PEM contents (newlines as \\n) or path to a .pem file.", example: "-----BEGIN RSA PRIVATE KEY-----…" },
                        { name: "GITHUB_WEBHOOK_SECRET", description: "HMAC secret configured on the GitHub App webhook.", example: "supersecret" },
                    ],
                },
                {
                    category: "Sentry",
                    rows: [
                        { name: "SENTRY_WEBHOOK_SECRET", description: "Per-workspace secret stored in the Integration row. Set automatically when you link a workspace via the dashboard.", example: "auto-generated" },
                    ],
                },
                {
                    category: "LLM Providers",
                    rows: [
                        { name: "LLM_PROVIDER_CHAIN", description: "Comma-separated list of providers tried in order. Falls back to the next when a call fails.", example: "groq,together,mistral,openrouter" },
                        { name: "GROQ_API_KEY", description: "Groq API key (optional; provider skipped if absent).", example: "gsk_…" },
                        { name: "TOGETHER_API_KEY", description: "Together AI key.", example: "…" },
                        { name: "MISTRAL_API_KEY", description: "Mistral key.", example: "…" },
                        { name: "OPENROUTER_API_KEY", description: "OpenRouter key.", example: "…" },
                        { name: "GITHUB_MODELS_TOKEN", description: "GitHub Models inference token.", example: "ghp_…" },
                    ],
                },
                {
                    category: "Email (optional)",
                    rows: [
                        { name: "SMTP_HOST", description: "SMTP server for QA / rollback notification emails.", example: "smtp.gmail.com" },
                        { name: "SMTP_PORT", description: "SMTP port.", example: "587" },
                        { name: "SMTP_USER", description: "SMTP username.", example: "you@example.com" },
                        { name: "SMTP_PASS", description: "SMTP password or app token.", example: "…" },
                    ],
                },
                {
                    category: "General",
                    rows: [
                        { name: "BASE_URL", description: "Public URL of the engine, used when registering Sentry webhook paths.", example: "https://slothops.example.com" },
                        { name: "LOG_LEVEL", description: "Python log level.", example: "INFO" },
                    ],
                },
            ].map(({ category, rows }) => (_jsxs("div", { style: { marginBottom: 32 }, children: [_jsx("p", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#555", textTransform: "uppercase", letterSpacing: 1, margin: "0 0 12px" }, children: category }), _jsx("div", { style: { border: "1px solid #2a2a2a", borderRadius: 8, overflow: "hidden" }, children: _jsxs("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }, children: [_jsx("thead", { children: _jsxs("tr", { style: { backgroundColor: "#111", borderBottom: "1px solid #2a2a2a" }, children: [_jsx("th", { style: { padding: "10px 16px", textAlign: "left", color: "#555", fontWeight: 500, fontSize: "0.75rem", textTransform: "uppercase", fontFamily: "monospace" }, children: "Variable" }), _jsx("th", { style: { padding: "10px 16px", textAlign: "left", color: "#555", fontWeight: 500, fontSize: "0.75rem", textTransform: "uppercase", fontFamily: "monospace" }, children: "Description" }), _jsx("th", { style: { padding: "10px 16px", textAlign: "left", color: "#555", fontWeight: 500, fontSize: "0.75rem", textTransform: "uppercase", fontFamily: "monospace" }, children: "Example" })] }) }), _jsx("tbody", { children: rows.map((r) => _jsx(ConfigRow, { ...r }, r.name)) })] }) })] }, category)))] }));
}
function ApiAuth() {
    return (_jsxs(_Fragment, { children: [_jsx(SectionHeading, { title: "Auth", subtitle: "JWT-based authentication. All protected routes require Authorization: Bearer <token>." }), _jsx(Endpoint, { method: "POST", path: "/api/auth/signup", auth: false, description: "Create a new user account and workspace. Returns a JWT access token.", body: `{
  "email": "you@example.com",
  "password": "hunter2",
  "workspace_name": "my-org"
}`, response: `{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}` }), _jsx(Endpoint, { method: "POST", path: "/api/auth/login", auth: false, description: "Authenticate an existing user. Returns a JWT access token.", body: `{
  "email": "you@example.com",
  "password": "hunter2"
}`, response: `{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}` }), _jsx(Endpoint, { method: "GET", path: "/api/auth/session", auth: true, description: "Returns the current user's email and workspace_id from the JWT.", response: `{
  "email": "you@example.com",
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000"
}` }), _jsx(Endpoint, { method: "GET", path: "/api/auth/workspaces", auth: true, description: "List all workspaces the current user belongs to.", response: `[
  { "id": "550e8400-…", "name": "my-org", "created_at": "2026-05-01T10:00:00Z" }
]` })] }));
}
function ApiDashboard() {
    return (_jsxs(_Fragment, { children: [_jsx(SectionHeading, { title: "Dashboard", subtitle: "Aggregated metrics, activity feeds, and health for the workspace." }), _jsx(Endpoint, { method: "GET", path: "/api/dashboard/overview", auth: true, description: "Full overview payload: metrics (open issues, QA failures, pending rollbacks), recent activity, repo cards, and integration health.", response: `{
  "workspace_id": "550e8400-…",
  "metrics": [
    { "name": "open_issues", "value": 3 },
    { "name": "prs_created", "value": 12 },
    { "name": "qa_failed", "value": 1 },
    { "name": "rollbacks_pending", "value": 0 }
  ],
  "repos": [...],
  "recent_activity": [...],
  "health": {
    "github": "connected",
    "sentry": "connected",
    "llm": "groq",
    "database": "ok"
  }
}` }), _jsx(Endpoint, { method: "GET", path: "/api/dashboard/activity", auth: true, description: "Last 50 audit events for the workspace, newest first." }), _jsx(Endpoint, { method: "GET", path: "/api/dashboard/metrics", auth: true, description: "Issue counts by status, QA pass/fail rates, and rollback counts for the workspace." }), _jsx(Endpoint, { method: "GET", path: "/api/dashboard/repos", auth: true, description: "All repos linked to the workspace with their current policy settings." }), _jsx(Endpoint, { method: "GET", path: "/api/dashboard/health", auth: true, description: "Live check of GitHub App connectivity, LLM provider availability, and DB reachability." })] }));
}
function ApiRepos() {
    return (_jsxs(_Fragment, { children: [_jsx(SectionHeading, { title: "Repos", subtitle: "Manage repository policies and integration settings." }), _jsx(Endpoint, { method: "GET", path: "/api/repos", auth: true, description: "List all repos linked to the workspace." }), _jsx(Endpoint, { method: "POST", path: "/api/repos/{repo_full_name}/policy", auth: true, description: "Create or update the automation policy for a repo. Controls LLM fix generation, QA enforcement, and rollback behaviour.", body: `{
  "auto_fix_enabled": true,
  "qa_required": true,
  "rollback_mode": "APPROVAL_REQUIRED",
  "rollback_strategy": "ROLLBACK_PR",
  "max_fix_attempts": 3
}` }), _jsx(Endpoint, { method: "POST", path: "/api/repos/{repo_full_name}/preflight", auth: true, description: "Run a pre-flight check on a repo: verifies GitHub App permissions, branch protection rules, and that webhooks are reachable." })] }));
}
function ApiQA() {
    return (_jsxs(_Fragment, { children: [_jsx(SectionHeading, { title: "QA Reports", subtitle: "Inspect, bypass, or auto-resolve QA failures on pull requests." }), _jsx(Endpoint, { method: "GET", path: "/api/qa-reports", auth: true, description: "List all QA reports for the workspace, newest first. Accepts ?status= filter." }), _jsx(Endpoint, { method: "GET", path: "/api/qa-reports/{id}", auth: true, description: "Full QA report: per-agent verdicts, logs, and the overall pass/fail decision.", response: `{
  "id": "…",
  "pr_url": "https://github.com/org/repo/pull/42",
  "status": "failed",
  "agents": {
    "static_analysis": { "passed": true,  "log": "…" },
    "functionality":   { "passed": false, "log": "…" },
    "regression":      { "passed": true,  "log": "…" },
    "performance":     { "passed": true,  "log": "…" },
    "stress_test":     { "passed": true,  "log": "…" },
    "vapt":            { "passed": true,  "log": "…" }
  }
}` }), _jsx(Endpoint, { method: "POST", path: "/api/qa-bypass/{id}", auth: true, description: "Manually override a failed QA report. Marks the report as 'bypassed' and sets the GitHub commit status to success. Requires a reason in the body.", body: `{ "reason": "Flaky test — network unavailable in CI" }` }), _jsx(Endpoint, { method: "POST", path: "/api/qa-resolve/{id}", auth: true, description: "Trigger the LLM-driven auto-fix flow. Reads the failing agent logs, generates corrective commits, pushes them to the PR branch, and re-runs QA." })] }));
}
function ApiRollbacks() {
    return (_jsxs(_Fragment, { children: [_jsx(SectionHeading, { title: "Rollbacks", subtitle: "Inspect the rollback queue and approve pending reverts." }), _jsx(Endpoint, { method: "GET", path: "/api/rollbacks", auth: true, description: "List all rollback records for the workspace. Accepts ?status= filter (pending_approval, approved, executing, completed, failed)." }), _jsx(Endpoint, { method: "GET", path: "/api/rollbacks/{id}", auth: true, description: "Full rollback record: target SHA, strategy, approver, and execution log." }), _jsx(Endpoint, { method: "POST", path: "/api/rollbacks/{id}/approve", auth: true, description: "Approve a pending rollback. Triggers immediate execution (direct revert or rollback PR depending on policy)." })] }));
}
function ApiHealth() {
    return (_jsxs(_Fragment, { children: [_jsx(SectionHeading, { title: "Health", subtitle: "Liveness and readiness probes." }), _jsx(Endpoint, { method: "GET", path: "/health", auth: false, description: "Simple liveness probe. Returns 200 immediately.", response: `{ "status": "ok", "service": "slothops-engine" }` }), _jsx(Endpoint, { method: "GET", path: "/api/health/engine", auth: true, description: "Checks database connectivity and reports engine uptime." }), _jsx(Endpoint, { method: "GET", path: "/api/health/llm", auth: true, description: "Tests the configured LLM provider chain and returns which providers responded successfully." })] }));
}
function Webhooks() {
    return (_jsxs(_Fragment, { children: [_jsx(SectionHeading, { title: "Webhooks", subtitle: "Configure Sentry and GitHub to send events to SlothOps." }), _jsx(H2, { children: "Sentry" }), _jsx("p", { style: { color: "#a1a1aa", lineHeight: 1.75, marginBottom: 16 }, children: "SlothOps receives Sentry webhooks at a per-workspace URL. Each workspace gets its own HMAC secret, scoped to your Sentry project." }), _jsx(CodeBlock, { lang: "bash", children: `POST /webhook/sentry/{workspace_id}` }), _jsxs("p", { style: { color: "#a1a1aa", lineHeight: 1.75, marginBottom: 16 }, children: ["In Sentry \u2192 Project Settings \u2192 Integrations \u2192 WebHooks, add the URL above and tick ", _jsx("strong", { children: "Issue" }), " events. Copy the secret from the Integration row in your SlothOps workspace settings and paste it into Sentry's ", _jsx("strong", { children: "Secret" }), " field."] }), _jsxs(Note, { children: ["Signature verification uses ", _jsx(Code, { children: "X-Sentry-Hook-Signature" }), ". Requests that fail HMAC are rejected with ", _jsx(Code, { children: "401" }), "."] }), _jsx(H2, { children: "GitHub App" }), _jsx(CodeBlock, { lang: "bash", children: `POST /webhook/github` }), _jsxs("p", { style: { color: "#a1a1aa", lineHeight: 1.75, marginBottom: 16 }, children: ["The GitHub App webhook fires on ", _jsx(Code, { children: "pull_request" }), " (opened / synchronize) and ", _jsx(Code, { children: "deployment_status" }), " (failure / error) events."] }), _jsxs("ol", { style: { color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }, children: [_jsx("li", { children: "Create a GitHub App in your org \u2192 Settings \u2192 Developer settings \u2192 GitHub Apps." }), _jsxs("li", { children: ["Set the Webhook URL to ", _jsx(Code, { children: "{BASE_URL}/webhook/github" }), "."] }), _jsxs("li", { children: ["Generate a Webhook Secret and set it as ", _jsx(Code, { children: "GITHUB_WEBHOOK_SECRET" }), " in your ", _jsx(Code, { children: ".env" }), "."] }), _jsxs("li", { children: ["Download the private key and set it as ", _jsx(Code, { children: "GITHUB_APP_PRIVATE_KEY" }), "."] }), _jsx("li", { children: "Install the App on the repos you want SlothOps to manage." })] })] }));
}
function Pipelines() {
    return (_jsxs(_Fragment, { children: [_jsx(SectionHeading, { title: "Pipeline Flows", subtitle: "Four autonomous flows that run in the background when triggered by a webhook." }), [
                {
                    title: "1. Sentry Issue → Fix PR",
                    steps: [
                        ["Receive", "POST /webhook/sentry/{ws_id}", "HMAC-verified Sentry webhook payload arrives."],
                        ["Parse", "app/integrations/sentry_parser.py", "Extracts IssueRecord + CallFrame[] from the payload."],
                        ["Dedupe", "app/code_analysis/fingerprint.py", "Computes a fingerprint; skips the issue if it was seen recently."],
                        ["Classify", "app/llm/classifier.py", "Labels the issue: code / infra / dependency / unknown."],
                        ["Fetch context", "app/code_analysis/code_fetcher.py", "Pulls the relevant source files from GitHub."],
                        ["Generate fix", "app/llm/fixer.py", "Sends context + stack trace to the LLM; parses a structured LLMFixResponse."],
                        ["Open PR", "app/integrations/github_automation.py", "Commits the fix to a new branch and opens a pull request."],
                    ],
                },
                {
                    title: "2. Pull Request → QA Report",
                    steps: [
                        ["Receive", "POST /webhook/github", "GitHub sends pull_request opened/synchronize event."],
                        ["Triage", "app/pipelines/qa_triage.py", "Determines which of the 6 agents are required vs advisory for this repo's stack."],
                        ["Run agents", "app/qa_agents/*", "Six agents run concurrently: static_analysis, functionality, regression, performance, stress_test, vapt."],
                        ["Aggregate", "app/pipelines/qa_pipeline.py", "Collects pass/fail + logs per agent; writes QAReport row."],
                        ["Set status", "GitHub Commit Status API", "Flips the PR's commit status to success or failure."],
                    ],
                },
                {
                    title: "3. Deploy Failure → Rollback",
                    steps: [
                        ["Receive", "POST /webhook/github", "GitHub sends deployment_status failure event."],
                        ["Plan", "app/pipelines/rollback.py", "Finds the last-known-good SHA; consults repo policy (mode + strategy)."],
                        ["Gate", "Policy: APPROVAL_REQUIRED", "Creates RollbackRecord(status=pending_approval); operator approves via POST /api/rollbacks/{id}/approve."],
                        ["Execute", "app/pipelines/rollback.py", "DIRECT_REVERT: force-pushes a revert commit. ROLLBACK_PR: opens a PR with the revert."],
                    ],
                },
                {
                    title: "4. QA Failure → Auto-Resolve",
                    steps: [
                        ["Trigger", "POST /api/qa-resolve/{id}", "Operator triggers LLM-driven auto-fix."],
                        ["Analyse", "app/pipelines/qa_resolution.py", "Reads failing agent logs; builds a structured prompt."],
                        ["Generate", "app/llm/client.py", "LLM produces corrective commits targeting the failing tests."],
                        ["Push", "GitHub API", "Commits pushed to the PR branch; triggers a new QA cycle automatically."],
                    ],
                },
            ].map(({ title, steps }) => (_jsxs("div", { style: { marginBottom: 40 }, children: [_jsx("h2", { style: { fontFamily: "monospace", fontSize: "1.1rem", fontWeight: 600, margin: "0 0 16px", color: "#c084fc" }, children: title }), _jsx("div", { style: { border: "1px solid #2a2a2a", borderRadius: 8, overflow: "hidden" }, children: steps.map(([stage, where, what], i) => (_jsxs("div", { style: {
                                display: "grid",
                                gridTemplateColumns: "90px 1fr 2fr",
                                gap: 0,
                                borderBottom: i < steps.length - 1 ? "1px solid #1a1a1a" : "none",
                                alignItems: "start",
                            }, children: [_jsx("div", { style: { padding: "12px 16px", fontFamily: "monospace", fontSize: "0.75rem", color: "#9333ea", fontWeight: 600 }, children: stage }), _jsx("div", { style: { padding: "12px 16px", fontFamily: "monospace", fontSize: "0.78rem", color: "#7dd3fc", borderLeft: "1px solid #1a1a1a" }, children: where }), _jsx("div", { style: { padding: "12px 16px", fontSize: "0.85rem", color: "#a1a1aa", borderLeft: "1px solid #1a1a1a" }, children: what })] }, i))) })] }, title)))] }));
}
function Contributing() {
    return (_jsxs(_Fragment, { children: [_jsx(SectionHeading, { title: "Contributing", subtitle: "SlothOps is open source. Here's how to extend and improve it." }), _jsx(H2, { children: "Adding a new API route" }), _jsxs("ol", { style: { color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }, children: [_jsxs("li", { children: ["Create or edit a router file in ", _jsx(Code, { children: "app/api/" }), "."] }), _jsxs("li", { children: ["Define your endpoint using ", _jsx(Code, { children: "@router.get/post/\u2026" }), " with a ", _jsx(Code, { children: "Depends(get_current_workspace)" }), " guard."] }), _jsxs("li", { children: ["Add business logic in ", _jsx(Code, { children: "app/services/" }), " (keep routers thin)."] }), _jsxs("li", { children: ["Register the router in ", _jsx(Code, { children: "main.py" }), ": ", _jsx(Code, { children: "app.include_router(your_router)" }), "."] }), _jsxs("li", { children: ["Add a Pydantic response schema to ", _jsx(Code, { children: "app/schemas/" }), " if needed."] })] }), _jsx(H2, { children: "Adding a new QA agent" }), _jsxs("ol", { style: { color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }, children: [_jsxs("li", { children: ["Create ", _jsx(Code, { children: "app/qa_agents/my_agent.py" }), " with a single async function ", _jsx(Code, { children: "run_my_agent(pr_url, repo_dir) → { passed, log }" }), "."] }), _jsxs("li", { children: ["Import and call it in ", _jsx(Code, { children: "app/pipelines/qa_pipeline.py" }), " alongside the other agents."] }), _jsxs("li", { children: ["Update the triage logic in ", _jsx(Code, { children: "app/pipelines/qa_triage.py" }), " if the agent should be advisory for some stacks."] })] }), _jsx(H2, { children: "Adding an LLM provider" }), _jsxs("ol", { style: { color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }, children: [_jsxs("li", { children: ["Add a new ", _jsx(Code, { children: "ProviderConfig" }), " entry in ", _jsx(Code, { children: "app/llm/client.py" }), " with the provider name, base URL, and API key env var."] }), _jsxs("li", { children: ["Add the key to ", _jsx(Code, { children: ".env.example" }), "."] }), _jsxs("li", { children: ["Add the provider name to ", _jsx(Code, { children: "LLM_PROVIDER_CHAIN" }), " in your ", _jsx(Code, { children: ".env" }), "."] })] }), _jsx(H2, { children: "Running tests" }), _jsx(CodeBlock, { lang: "bash", children: `source venv/bin/activate
pytest -x tests/    # stop on first failure

# DB-dependent tests require Postgres — skip them locally:
pytest --ignore=tests/test_database_repo_config.py tests/` }), _jsx(H2, { children: "Submitting a pull request" }), _jsxs("ol", { style: { color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }, children: [_jsxs("li", { children: ["Fork the repo and create a branch: ", _jsx(Code, { children: "git checkout -b feat/my-feature" }), "."] }), _jsx("li", { children: "Write your change \u2014 keep it focused; one PR per concern." }), _jsxs("li", { children: ["Add or update tests in ", _jsx(Code, { children: "tests/" }), " if the change is testable without external services."] }), _jsxs("li", { children: ["Run ", _jsx(Code, { children: "pytest -x tests/" }), " and confirm no new failures."] }), _jsxs("li", { children: ["Open a PR describing ", _jsx("em", { children: "what" }), " changed and ", _jsx("em", { children: "why" }), "."] })] }), _jsx(Note, { children: "The engine has no linter configured yet. Keep formatting consistent with the surrounding code (4-space indent for Python, monospace strings for logging)." })] }));
}
// ── Section registry ─────────────────────────────────────────────────────────
const SECTIONS = {
    overview: Overview,
    quickstart: QuickStart,
    devmode: DevMode,
    configuration: Configuration,
    "api-auth": ApiAuth,
    "api-dashboard": ApiDashboard,
    "api-repos": ApiRepos,
    "api-qa": ApiQA,
    "api-rollbacks": ApiRollbacks,
    "api-health": ApiHealth,
    webhooks: Webhooks,
    pipelines: Pipelines,
    contributing: Contributing,
};
// ── Page shell ───────────────────────────────────────────────────────────────
export default function DocsPage() {
    const [active, setActive] = useState("overview");
    const Section = SECTIONS[active];
    return (_jsxs("div", { style: { display: "flex", flexDirection: "column", minHeight: "100vh", backgroundColor: "#0a0a0a", color: "#ededed" }, children: [_jsx("header", { style: {
                    position: "sticky",
                    top: 0,
                    zIndex: 40,
                    borderBottom: "1px solid #1f1f1f",
                    backgroundColor: "rgba(10, 10, 10, 0.9)",
                    backdropFilter: "blur(12px)",
                }, children: _jsxs("div", { style: { maxWidth: 1200, margin: "0 auto", display: "flex", height: 56, alignItems: "center", justifyContent: "space-between", padding: "0 24px" }, children: [_jsxs(Link, { to: "/", style: { fontFamily: "monospace", fontSize: "1.05rem", fontWeight: 600, letterSpacing: "-0.5px", color: "#ededed", textDecoration: "none" }, children: ["SlothOps ", _jsx("span", { style: { color: "#555", fontSize: "0.8rem", fontWeight: "normal" }, children: "[Docs]" })] }), _jsxs("div", { style: { display: "flex", gap: 20, alignItems: "center" }, children: [_jsx("a", { href: "/docs", style: { fontFamily: "monospace", fontSize: "0.8rem", color: "#a1a1aa", textDecoration: "none" }, children: "API Reference" }), _jsx(Link, { to: "/login", style: {
                                        backgroundColor: "#9333ea",
                                        color: "#fff",
                                        padding: "5px 14px",
                                        borderRadius: 4,
                                        fontFamily: "monospace",
                                        fontSize: "0.8rem",
                                        fontWeight: 600,
                                        textDecoration: "none",
                                    }, children: "Sign In \u2192" })] })] }) }), _jsxs("div", { style: { display: "flex", flex: 1, maxWidth: 1200, margin: "0 auto", width: "100%" }, children: [_jsx("aside", { style: {
                            width: 240,
                            flexShrink: 0,
                            position: "sticky",
                            top: 56,
                            height: "calc(100vh - 56px)",
                            overflowY: "auto",
                            borderRight: "1px solid #1f1f1f",
                            padding: "32px 0",
                        }, children: NAV.map((group) => (_jsxs("div", { style: { marginBottom: 28 }, children: [_jsx("p", { style: {
                                        fontFamily: "monospace",
                                        fontSize: "0.65rem",
                                        textTransform: "uppercase",
                                        letterSpacing: 1.5,
                                        color: "#444",
                                        padding: "0 20px",
                                        margin: "0 0 10px",
                                    }, children: group.label }), group.items.map((item) => {
                                    const isActive = active === item.id;
                                    return (_jsx("button", { onClick: () => setActive(item.id), style: {
                                            all: "unset",
                                            display: "block",
                                            width: "100%",
                                            padding: "7px 20px",
                                            fontFamily: "monospace",
                                            fontSize: "0.85rem",
                                            cursor: "pointer",
                                            color: isActive ? "#c084fc" : "#6b7280",
                                            backgroundColor: isActive ? "rgba(147,51,234,0.08)" : "transparent",
                                            borderLeft: isActive ? "2px solid #9333ea" : "2px solid transparent",
                                            transition: "color 0.15s, background 0.15s",
                                            boxSizing: "border-box",
                                        }, onMouseEnter: (e) => { if (!isActive)
                                            e.currentTarget.style.color = "#d4d4d8"; }, onMouseLeave: (e) => { if (!isActive)
                                            e.currentTarget.style.color = "#6b7280"; }, children: item.label }, item.id));
                                })] }, group.label))) }), _jsx("main", { style: { flex: 1, padding: "48px 56px", minWidth: 0, overflowY: "auto" }, children: _jsx(Section, {}) })] })] }));
}
