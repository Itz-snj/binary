import { useState } from "react";
import { Link } from "react-router-dom";

// ── Types ────────────────────────────────────────────────────────────────────

type SectionId =
  | "overview"
  | "quickstart"
  | "devmode"
  | "configuration"
  | "api-auth"
  | "api-dashboard"
  | "api-repos"
  | "api-qa"
  | "api-rollbacks"
  | "api-health"
  | "webhooks"
  | "pipelines"
  | "contributing";

interface NavGroup {
  label: string;
  items: { id: SectionId; label: string }[];
}

// ── Nav tree ─────────────────────────────────────────────────────────────────

const NAV: NavGroup[] = [
  {
    label: "Getting Started",
    items: [
      { id: "overview",    label: "Overview" },
      { id: "quickstart",  label: "Quick Start (Docker)" },
      { id: "devmode",     label: "Dev Mode (no Docker)" },
      { id: "configuration", label: "Configuration" },
    ],
  },
  {
    label: "API Reference",
    items: [
      { id: "api-auth",      label: "Auth" },
      { id: "api-dashboard", label: "Dashboard" },
      { id: "api-repos",     label: "Repos" },
      { id: "api-qa",        label: "QA Reports" },
      { id: "api-rollbacks", label: "Rollbacks" },
      { id: "api-health",    label: "Health" },
    ],
  },
  {
    label: "Architecture",
    items: [
      { id: "webhooks",   label: "Webhooks" },
      { id: "pipelines",  label: "Pipeline Flows" },
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

function Code({ children }: { children: string }) {
  return (
    <code style={{
      fontFamily: "monospace",
      fontSize: "0.85rem",
      backgroundColor: "#1a1a1a",
      border: "1px solid #2a2a2a",
      borderRadius: 4,
      padding: "2px 6px",
      color: "#c084fc",
    }}>
      {children}
    </code>
  );
}

function CodeBlock({ children, lang = "bash" }: { children: string; lang?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div style={{ position: "relative", marginBottom: 24 }}>
      <div style={{
        backgroundColor: "#111",
        border: "1px solid #2a2a2a",
        borderRadius: 8,
        overflow: "hidden",
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 16px",
          borderBottom: "1px solid #2a2a2a",
          backgroundColor: "#161616",
        }}>
          <span style={{ fontFamily: "monospace", fontSize: "0.7rem", color: "#555", textTransform: "uppercase", letterSpacing: 1 }}>{lang}</span>
          <button
            onClick={copy}
            style={{
              all: "unset",
              cursor: "pointer",
              fontFamily: "monospace",
              fontSize: "0.7rem",
              color: copied ? "#4ade80" : "#555",
              transition: "color 0.2s",
            }}
          >
            {copied ? "copied!" : "copy"}
          </button>
        </div>
        <pre style={{
          margin: 0,
          padding: "16px",
          fontFamily: "monospace",
          fontSize: "0.85rem",
          lineHeight: 1.65,
          color: "#d4d4d8",
          overflowX: "auto",
          whiteSpace: "pre",
        }}>
          {children}
        </pre>
      </div>
    </div>
  );
}

function MethodBadge({ method }: { method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE" }) {
  const COLORS: Record<string, string> = {
    GET:    "#2563eb",
    POST:   "#16a34a",
    PUT:    "#d97706",
    PATCH:  "#7c3aed",
    DELETE: "#dc2626",
  };
  return (
    <span style={{
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
    }}>
      {method}
    </span>
  );
}

function Endpoint({
  method,
  path,
  auth = true,
  description,
  body,
  response,
}: {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  auth?: boolean;
  description: string;
  body?: string;
  response?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{
      border: "1px solid #2a2a2a",
      borderRadius: 8,
      marginBottom: 12,
      overflow: "hidden",
      backgroundColor: "#0d0d0d",
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          all: "unset",
          width: "100%",
          display: "flex",
          alignItems: "center",
          padding: "12px 16px",
          cursor: "pointer",
          gap: 0,
        }}
      >
        <MethodBadge method={method} />
        <code style={{ fontFamily: "monospace", fontSize: "0.9rem", color: "#e2e2e2", flex: 1 }}>
          {path}
        </code>
        {auth && (
          <span style={{ fontSize: "0.7rem", color: "#555", marginRight: 12, fontFamily: "monospace" }}>🔒 auth</span>
        )}
        <span style={{ color: "#555", fontSize: "0.75rem" }}>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div style={{ padding: "16px", borderTop: "1px solid #2a2a2a" }}>
          <p style={{ color: "#a1a1aa", fontSize: "0.9rem", margin: "0 0 16px" }}>{description}</p>
          {body && (
            <>
              <p style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#555", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Request Body</p>
              <CodeBlock lang="json">{body}</CodeBlock>
            </>
          )}
          {response && (
            <>
              <p style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#555", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Response</p>
              <CodeBlock lang="json">{response}</CodeBlock>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function SectionHeading({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div style={{ marginBottom: 32, paddingBottom: 20, borderBottom: "1px solid #1f1f1f" }}>
      <h1 style={{ fontFamily: "monospace", fontSize: "1.9rem", fontWeight: 700, margin: 0, letterSpacing: "-0.5px" }}>{title}</h1>
      {subtitle && <p style={{ color: "#71717a", fontSize: "1rem", margin: "8px 0 0", lineHeight: 1.6 }}>{subtitle}</p>}
    </div>
  );
}

function H2({ children }: { children: string }) {
  return <h2 style={{ fontFamily: "monospace", fontSize: "1.2rem", fontWeight: 600, margin: "36px 0 16px", color: "#e4e4e7" }}>{children}</h2>;
}

function Note({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      border: "1px solid #2a2a2a",
      borderLeft: "3px solid #9333ea",
      backgroundColor: "rgba(147, 51, 234, 0.05)",
      borderRadius: "0 8px 8px 0",
      padding: "12px 16px",
      marginBottom: 20,
      fontSize: "0.9rem",
      color: "#a1a1aa",
      lineHeight: 1.6,
    }}>
      {children}
    </div>
  );
}

function ConfigRow({ name, required, description, example }: { name: string; required?: boolean; description: string; example: string }) {
  return (
    <tr>
      <td style={{ padding: "12px 16px", fontFamily: "monospace", fontSize: "0.85rem", color: "#c084fc", verticalAlign: "top" }}>
        {name}
        {required && <span style={{ marginLeft: 6, fontSize: "0.65rem", color: "#ef4444", textTransform: "uppercase" }}>required</span>}
      </td>
      <td style={{ padding: "12px 16px", color: "#a1a1aa", fontSize: "0.85rem", lineHeight: 1.5, verticalAlign: "top" }}>{description}</td>
      <td style={{ padding: "12px 16px", fontFamily: "monospace", fontSize: "0.8rem", color: "#555", verticalAlign: "top" }}>{example}</td>
    </tr>
  );
}

// ── Sections ─────────────────────────────────────────────────────────────────

function Overview() {
  return (
    <>
      <SectionHeading
        title="SlothOps Engine"
        subtitle="A closed-loop, production-aware automation engine that converts live application crashes into reviewed code fixes."
      />
      <p style={{ color: "#a1a1aa", lineHeight: 1.75, marginBottom: 20 }}>
        SlothOps sits between your observability layer (Sentry) and your source control (GitHub). When an exception fires in production, SlothOps:
      </p>
      <ol style={{ color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }}>
        <li>Receives the Sentry webhook, deduplicates and fingerprints the issue.</li>
        <li>Fetches the exact source code context from GitHub.</li>
        <li>Generates a targeted fix using an LLM with a configurable provider chain.</li>
        <li>Opens a pull request with the fix and a full explanation.</li>
        <li>Runs 6 automated QA agents against the fix PR.</li>
        <li>If the deploy fails, plans or executes a governed rollback.</li>
      </ol>
      <Note>
        No environment API keys are strictly required to start the engine. The LLM and GitHub flows are skipped gracefully when keys are absent — useful for local exploration.
      </Note>
      <H2>Stack</H2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 24 }}>
        {[
          ["Backend", "FastAPI · SQLModel · asyncpg · Alembic"],
          ["Database", "PostgreSQL 16"],
          ["Frontend", "React 18 · Vite · TanStack Query · React Router"],
          ["LLM", "Provider chain (Groq / Together / Mistral / OpenRouter / …)"],
          ["Integrations", "GitHub App · Sentry webhooks · SMTP"],
          ["Infra", "Docker Compose · multi-stage build"],
        ].map(([label, value]) => (
          <div key={label} style={{ padding: "14px 16px", border: "1px solid #2a2a2a", borderRadius: 8, backgroundColor: "#0d0d0d" }}>
            <div style={{ fontFamily: "monospace", fontSize: "0.7rem", color: "#555", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>{label}</div>
            <div style={{ fontSize: "0.88rem", color: "#d4d4d8" }}>{value}</div>
          </div>
        ))}
      </div>
    </>
  );
}

function QuickStart() {
  return (
    <>
      <SectionHeading title="Quick Start (Docker)" subtitle="Bring the full stack up in one command. Requires Docker Desktop 27+." />
      <H2>1. Clone & configure</H2>
      <CodeBlock lang="bash">{`git clone https://github.com/your-org/slothops-engine
cd slothops-engine
cp .env.example .env   # fill in API keys (optional for exploration)`}</CodeBlock>
      <H2>2. Spin up</H2>
      <CodeBlock lang="bash">{`docker compose up --build`}</CodeBlock>
      <p style={{ color: "#a1a1aa", lineHeight: 1.75, marginBottom: 20 }}>
        What happens under the hood:
      </p>
      <ol style={{ color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }}>
        <li>Postgres 16 starts; healthcheck waits until it accepts connections.</li>
        <li><Code>web-builder</Code> stage — Bun installs <Code>web/package.json</Code> and runs <Code>bun run build</Code>, producing <Code>web/dist/</Code>.</li>
        <li><Code>runtime</Code> stage — Python 3.13 slim, pip installs <Code>requirements.txt</Code>, copies source.</li>
        <li>Container CMD runs <Code>alembic upgrade head</Code> then <Code>uvicorn main:app</Code>.</li>
      </ol>
      <H2>3. Verify</H2>
      <CodeBlock lang="bash">{`# Health
curl http://localhost:8000/health

# Create an account
curl -X POST http://localhost:8000/api/auth/signup \\
  -H 'content-type: application/json' \\
  -d '{"email":"you@example.com","password":"hunter2","workspace_name":"demo"}'

# Store the token
export TOKEN=<access_token from above>

# Dashboard
curl http://localhost:8000/api/dashboard/overview \\
  -H "authorization: Bearer $TOKEN"`}</CodeBlock>
      <H2>Useful URLs</H2>
      <div style={{ overflowX: "auto", marginBottom: 24 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #2a2a2a" }}>
              <th style={{ padding: "10px 16px", textAlign: "left", fontFamily: "monospace", color: "#555", fontWeight: 500, fontSize: "0.75rem", textTransform: "uppercase" }}>URL</th>
              <th style={{ padding: "10px 16px", textAlign: "left", fontFamily: "monospace", color: "#555", fontWeight: 500, fontSize: "0.75rem", textTransform: "uppercase" }}>What</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["http://localhost:8000/", "React dashboard"],
              ["http://localhost:8000/docs", "Swagger UI (OpenAPI)"],
              ["http://localhost:8000/health", "Engine liveness"],
              ["http://localhost:8000/stream?token=…", "SSE log + issue events"],
              ["http://localhost:8000/webhook/sentry/{ws_id}", "Sentry webhook receiver"],
              ["http://localhost:8000/webhook/github", "GitHub App webhook receiver"],
              ["postgres://slothops:slothops_dev@localhost:5432/slothops", "PostgreSQL (dev creds)"],
            ].map(([url, what]) => (
              <tr key={url} style={{ borderBottom: "1px solid #1a1a1a" }}>
                <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: "0.82rem", color: "#c084fc" }}>{url}</td>
                <td style={{ padding: "10px 16px", color: "#a1a1aa", fontSize: "0.88rem" }}>{what}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function DevMode() {
  return (
    <>
      <SectionHeading title="Dev Mode (no Docker)" subtitle="Postgres stays in Docker; engine and React dev server run on the host for fast reloads." />
      <H2>1. Start Postgres only</H2>
      <CodeBlock lang="bash">{`docker compose up -d postgres`}</CodeBlock>
      <H2>2. Run the engine</H2>
      <CodeBlock lang="bash">{`python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000`}</CodeBlock>
      <Note>
        <Code>--reload</Code> watches every <Code>.py</Code> file in the project. Each save is picked up in under a second — no container rebuild needed.
      </Note>
      <H2>3. Run the React dev server</H2>
      <CodeBlock lang="bash">{`cd web
bun install
bun run dev    # http://localhost:5173 — proxies /api/* to :8000`}</CodeBlock>
      <H2>Migrations</H2>
      <CodeBlock lang="bash">{`alembic upgrade head                         # apply pending migrations
alembic revision --autogenerate -m "add X"   # generate migration from model changes
alembic downgrade -1                         # roll back one revision`}</CodeBlock>
      <p style={{ color: "#a1a1aa", fontSize: "0.9rem", lineHeight: 1.7 }}>
        Alembic targets <Code>DIRECT_DATABASE_URL</Code> (the <Code>psycopg</Code> sync driver). The async <Code>DATABASE_URL</Code> (asyncpg) is used by the engine at runtime.
      </p>
    </>
  );
}

function Configuration() {
  return (
    <>
      <SectionHeading title="Configuration" subtitle="Environment variables read from .env at the repo root." />
      <Note>Copy <Code>.env.example</Code> → <Code>.env</Code> and fill in what you need. The engine starts without any keys set; features that require a missing key are skipped gracefully.</Note>

      {[
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
      ].map(({ category, rows }) => (
        <div key={category} style={{ marginBottom: 32 }}>
          <p style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#555", textTransform: "uppercase", letterSpacing: 1, margin: "0 0 12px" }}>{category}</p>
          <div style={{ border: "1px solid #2a2a2a", borderRadius: 8, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
              <thead>
                <tr style={{ backgroundColor: "#111", borderBottom: "1px solid #2a2a2a" }}>
                  <th style={{ padding: "10px 16px", textAlign: "left", color: "#555", fontWeight: 500, fontSize: "0.75rem", textTransform: "uppercase", fontFamily: "monospace" }}>Variable</th>
                  <th style={{ padding: "10px 16px", textAlign: "left", color: "#555", fontWeight: 500, fontSize: "0.75rem", textTransform: "uppercase", fontFamily: "monospace" }}>Description</th>
                  <th style={{ padding: "10px 16px", textAlign: "left", color: "#555", fontWeight: 500, fontSize: "0.75rem", textTransform: "uppercase", fontFamily: "monospace" }}>Example</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => <ConfigRow key={r.name} {...r} />)}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </>
  );
}

function ApiAuth() {
  return (
    <>
      <SectionHeading title="Auth" subtitle="JWT-based authentication. All protected routes require Authorization: Bearer <token>." />
      <Endpoint
        method="POST"
        path="/api/auth/signup"
        auth={false}
        description="Create a new user account and workspace. Returns a JWT access token."
        body={`{
  "email": "you@example.com",
  "password": "hunter2",
  "workspace_name": "my-org"
}`}
        response={`{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}`}
      />
      <Endpoint
        method="POST"
        path="/api/auth/login"
        auth={false}
        description="Authenticate an existing user. Returns a JWT access token."
        body={`{
  "email": "you@example.com",
  "password": "hunter2"
}`}
        response={`{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}`}
      />
      <Endpoint
        method="GET"
        path="/api/auth/session"
        auth={true}
        description="Returns the current user's email and workspace_id from the JWT."
        response={`{
  "email": "you@example.com",
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000"
}`}
      />
      <Endpoint
        method="GET"
        path="/api/auth/workspaces"
        auth={true}
        description="List all workspaces the current user belongs to."
        response={`[
  { "id": "550e8400-…", "name": "my-org", "created_at": "2026-05-01T10:00:00Z" }
]`}
      />
    </>
  );
}

function ApiDashboard() {
  return (
    <>
      <SectionHeading title="Dashboard" subtitle="Aggregated metrics, activity feeds, and health for the workspace." />
      <Endpoint
        method="GET"
        path="/api/dashboard/overview"
        auth={true}
        description="Full overview payload: metrics (open issues, QA failures, pending rollbacks), recent activity, repo cards, and integration health."
        response={`{
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
}`}
      />
      <Endpoint method="GET" path="/api/dashboard/activity" auth={true} description="Last 50 audit events for the workspace, newest first." />
      <Endpoint method="GET" path="/api/dashboard/metrics" auth={true} description="Issue counts by status, QA pass/fail rates, and rollback counts for the workspace." />
      <Endpoint method="GET" path="/api/dashboard/repos" auth={true} description="All repos linked to the workspace with their current policy settings." />
      <Endpoint method="GET" path="/api/dashboard/health" auth={true} description="Live check of GitHub App connectivity, LLM provider availability, and DB reachability." />
    </>
  );
}

function ApiRepos() {
  return (
    <>
      <SectionHeading title="Repos" subtitle="Manage repository policies and integration settings." />
      <Endpoint method="GET" path="/api/repos" auth={true} description="List all repos linked to the workspace." />
      <Endpoint
        method="POST"
        path="/api/repos/{repo_full_name}/policy"
        auth={true}
        description="Create or update the automation policy for a repo. Controls LLM fix generation, QA enforcement, and rollback behaviour."
        body={`{
  "auto_fix_enabled": true,
  "qa_required": true,
  "rollback_mode": "APPROVAL_REQUIRED",
  "rollback_strategy": "ROLLBACK_PR",
  "max_fix_attempts": 3
}`}
      />
      <Endpoint method="POST" path="/api/repos/{repo_full_name}/preflight" auth={true} description="Run a pre-flight check on a repo: verifies GitHub App permissions, branch protection rules, and that webhooks are reachable." />
    </>
  );
}

function ApiQA() {
  return (
    <>
      <SectionHeading title="QA Reports" subtitle="Inspect, bypass, or auto-resolve QA failures on pull requests." />
      <Endpoint method="GET" path="/api/qa-reports" auth={true} description="List all QA reports for the workspace, newest first. Accepts ?status= filter." />
      <Endpoint method="GET" path="/api/qa-reports/{id}" auth={true} description="Full QA report: per-agent verdicts, logs, and the overall pass/fail decision." response={`{
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
}`} />
      <Endpoint method="POST" path="/api/qa-bypass/{id}" auth={true} description="Manually override a failed QA report. Marks the report as 'bypassed' and sets the GitHub commit status to success. Requires a reason in the body." body={`{ "reason": "Flaky test — network unavailable in CI" }`} />
      <Endpoint method="POST" path="/api/qa-resolve/{id}" auth={true} description="Trigger the LLM-driven auto-fix flow. Reads the failing agent logs, generates corrective commits, pushes them to the PR branch, and re-runs QA." />
    </>
  );
}

function ApiRollbacks() {
  return (
    <>
      <SectionHeading title="Rollbacks" subtitle="Inspect the rollback queue and approve pending reverts." />
      <Endpoint method="GET" path="/api/rollbacks" auth={true} description="List all rollback records for the workspace. Accepts ?status= filter (pending_approval, approved, executing, completed, failed)." />
      <Endpoint method="GET" path="/api/rollbacks/{id}" auth={true} description="Full rollback record: target SHA, strategy, approver, and execution log." />
      <Endpoint method="POST" path="/api/rollbacks/{id}/approve" auth={true} description="Approve a pending rollback. Triggers immediate execution (direct revert or rollback PR depending on policy)." />
    </>
  );
}

function ApiHealth() {
  return (
    <>
      <SectionHeading title="Health" subtitle="Liveness and readiness probes." />
      <Endpoint method="GET" path="/health" auth={false} description="Simple liveness probe. Returns 200 immediately." response={`{ "status": "ok", "service": "slothops-engine" }`} />
      <Endpoint method="GET" path="/api/health/engine" auth={true} description="Checks database connectivity and reports engine uptime." />
      <Endpoint method="GET" path="/api/health/llm" auth={true} description="Tests the configured LLM provider chain and returns which providers responded successfully." />
    </>
  );
}

function Webhooks() {
  return (
    <>
      <SectionHeading title="Webhooks" subtitle="Configure Sentry and GitHub to send events to SlothOps." />
      <H2>Sentry</H2>
      <p style={{ color: "#a1a1aa", lineHeight: 1.75, marginBottom: 16 }}>
        SlothOps receives Sentry webhooks at a per-workspace URL. Each workspace gets its own HMAC secret, scoped to your Sentry project.
      </p>
      <CodeBlock lang="bash">{`POST /webhook/sentry/{workspace_id}`}</CodeBlock>
      <p style={{ color: "#a1a1aa", lineHeight: 1.75, marginBottom: 16 }}>
        In Sentry → Project Settings → Integrations → WebHooks, add the URL above and tick <strong>Issue</strong> events. Copy the secret from the Integration row in your SlothOps workspace settings and paste it into Sentry's <strong>Secret</strong> field.
      </p>
      <Note>
        Signature verification uses <Code>X-Sentry-Hook-Signature</Code>. Requests that fail HMAC are rejected with <Code>401</Code>.
      </Note>
      <H2>GitHub App</H2>
      <CodeBlock lang="bash">{`POST /webhook/github`}</CodeBlock>
      <p style={{ color: "#a1a1aa", lineHeight: 1.75, marginBottom: 16 }}>
        The GitHub App webhook fires on <Code>pull_request</Code> (opened / synchronize) and <Code>deployment_status</Code> (failure / error) events.
      </p>
      <ol style={{ color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }}>
        <li>Create a GitHub App in your org → Settings → Developer settings → GitHub Apps.</li>
        <li>Set the Webhook URL to <Code>{"{BASE_URL}/webhook/github"}</Code>.</li>
        <li>Generate a Webhook Secret and set it as <Code>GITHUB_WEBHOOK_SECRET</Code> in your <Code>.env</Code>.</li>
        <li>Download the private key and set it as <Code>GITHUB_APP_PRIVATE_KEY</Code>.</li>
        <li>Install the App on the repos you want SlothOps to manage.</li>
      </ol>
    </>
  );
}

function Pipelines() {
  return (
    <>
      <SectionHeading title="Pipeline Flows" subtitle="Four autonomous flows that run in the background when triggered by a webhook." />

      {[
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
      ].map(({ title, steps }) => (
        <div key={title} style={{ marginBottom: 40 }}>
          <h2 style={{ fontFamily: "monospace", fontSize: "1.1rem", fontWeight: 600, margin: "0 0 16px", color: "#c084fc" }}>{title}</h2>
          <div style={{ border: "1px solid #2a2a2a", borderRadius: 8, overflow: "hidden" }}>
            {steps.map(([stage, where, what], i) => (
              <div key={i} style={{
                display: "grid",
                gridTemplateColumns: "90px 1fr 2fr",
                gap: 0,
                borderBottom: i < steps.length - 1 ? "1px solid #1a1a1a" : "none",
                alignItems: "start",
              }}>
                <div style={{ padding: "12px 16px", fontFamily: "monospace", fontSize: "0.75rem", color: "#9333ea", fontWeight: 600 }}>{stage}</div>
                <div style={{ padding: "12px 16px", fontFamily: "monospace", fontSize: "0.78rem", color: "#7dd3fc", borderLeft: "1px solid #1a1a1a" }}>{where}</div>
                <div style={{ padding: "12px 16px", fontSize: "0.85rem", color: "#a1a1aa", borderLeft: "1px solid #1a1a1a" }}>{what}</div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}

function Contributing() {
  return (
    <>
      <SectionHeading title="Contributing" subtitle="SlothOps is open source. Here's how to extend and improve it." />
      <H2>Adding a new API route</H2>
      <ol style={{ color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }}>
        <li>Create or edit a router file in <Code>app/api/</Code>.</li>
        <li>Define your endpoint using <Code>@router.get/post/…</Code> with a <Code>Depends(get_current_workspace)</Code> guard.</li>
        <li>Add business logic in <Code>app/services/</Code> (keep routers thin).</li>
        <li>Register the router in <Code>main.py</Code>: <Code>app.include_router(your_router)</Code>.</li>
        <li>Add a Pydantic response schema to <Code>app/schemas/</Code> if needed.</li>
      </ol>
      <H2>Adding a new QA agent</H2>
      <ol style={{ color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }}>
        <li>Create <Code>app/qa_agents/my_agent.py</Code> with a single async function <Code>{"run_my_agent(pr_url, repo_dir) → { passed, log }"}</Code>.</li>
        <li>Import and call it in <Code>app/pipelines/qa_pipeline.py</Code> alongside the other agents.</li>
        <li>Update the triage logic in <Code>app/pipelines/qa_triage.py</Code> if the agent should be advisory for some stacks.</li>
      </ol>
      <H2>Adding an LLM provider</H2>
      <ol style={{ color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }}>
        <li>Add a new <Code>ProviderConfig</Code> entry in <Code>app/llm/client.py</Code> with the provider name, base URL, and API key env var.</li>
        <li>Add the key to <Code>.env.example</Code>.</li>
        <li>Add the provider name to <Code>LLM_PROVIDER_CHAIN</Code> in your <Code>.env</Code>.</li>
      </ol>
      <H2>Running tests</H2>
      <CodeBlock lang="bash">{`source venv/bin/activate
pytest -x tests/    # stop on first failure

# DB-dependent tests require Postgres — skip them locally:
pytest --ignore=tests/test_database_repo_config.py tests/`}</CodeBlock>
      <H2>Submitting a pull request</H2>
      <ol style={{ color: "#a1a1aa", lineHeight: 2, paddingLeft: 24, marginBottom: 24 }}>
        <li>Fork the repo and create a branch: <Code>git checkout -b feat/my-feature</Code>.</li>
        <li>Write your change — keep it focused; one PR per concern.</li>
        <li>Add or update tests in <Code>tests/</Code> if the change is testable without external services.</li>
        <li>Run <Code>pytest -x tests/</Code> and confirm no new failures.</li>
        <li>Open a PR describing <em>what</em> changed and <em>why</em>.</li>
      </ol>
      <Note>
        The engine has no linter configured yet. Keep formatting consistent with the surrounding code (4-space indent for Python, monospace strings for logging).
      </Note>
    </>
  );
}

// ── Section registry ─────────────────────────────────────────────────────────

const SECTIONS: Record<SectionId, () => JSX.Element> = {
  overview:      Overview,
  quickstart:    QuickStart,
  devmode:       DevMode,
  configuration: Configuration,
  "api-auth":      ApiAuth,
  "api-dashboard": ApiDashboard,
  "api-repos":     ApiRepos,
  "api-qa":        ApiQA,
  "api-rollbacks": ApiRollbacks,
  "api-health":    ApiHealth,
  webhooks:    Webhooks,
  pipelines:   Pipelines,
  contributing: Contributing,
};

// ── Page shell ───────────────────────────────────────────────────────────────

export default function DocsPage() {
  const [active, setActive] = useState<SectionId>("overview");
  const Section = SECTIONS[active];

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", backgroundColor: "#0a0a0a", color: "#ededed" }}>
      {/* ── Header ── */}
      <header style={{
        position: "sticky",
        top: 0,
        zIndex: 40,
        borderBottom: "1px solid #1f1f1f",
        backgroundColor: "rgba(10, 10, 10, 0.9)",
        backdropFilter: "blur(12px)",
      }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", height: 56, alignItems: "center", justifyContent: "space-between", padding: "0 24px" }}>
          <Link to="/" style={{ fontFamily: "monospace", fontSize: "1.05rem", fontWeight: 600, letterSpacing: "-0.5px", color: "#ededed", textDecoration: "none" }}>
            SlothOps <span style={{ color: "#555", fontSize: "0.8rem", fontWeight: "normal" }}>[Docs]</span>
          </Link>
          <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
            <a href="/docs" style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "#a1a1aa", textDecoration: "none" }}>API Reference</a>
            <Link to="/login" style={{
              backgroundColor: "#9333ea",
              color: "#fff",
              padding: "5px 14px",
              borderRadius: 4,
              fontFamily: "monospace",
              fontSize: "0.8rem",
              fontWeight: 600,
              textDecoration: "none",
            }}>
              Sign In →
            </Link>
          </div>
        </div>
      </header>

      {/* ── Body ── */}
      <div style={{ display: "flex", flex: 1, maxWidth: 1200, margin: "0 auto", width: "100%" }}>
        {/* Sidebar */}
        <aside style={{
          width: 240,
          flexShrink: 0,
          position: "sticky",
          top: 56,
          height: "calc(100vh - 56px)",
          overflowY: "auto",
          borderRight: "1px solid #1f1f1f",
          padding: "32px 0",
        }}>
          {NAV.map((group) => (
            <div key={group.label} style={{ marginBottom: 28 }}>
              <p style={{
                fontFamily: "monospace",
                fontSize: "0.65rem",
                textTransform: "uppercase",
                letterSpacing: 1.5,
                color: "#444",
                padding: "0 20px",
                margin: "0 0 10px",
              }}>
                {group.label}
              </p>
              {group.items.map((item) => {
                const isActive = active === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActive(item.id)}
                    style={{
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
                    }}
                    onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.color = "#d4d4d8"; }}
                    onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.color = "#6b7280"; }}
                  >
                    {item.label}
                  </button>
                );
              })}
            </div>
          ))}
        </aside>

        {/* Content */}
        <main style={{ flex: 1, padding: "48px 56px", minWidth: 0, overflowY: "auto" }}>
          <Section />
        </main>
      </div>
    </div>
  );
}
