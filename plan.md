# SlothOps Dashboard And Codebase Restructure Plan

## Summary
Turn SlothOps into a clean, client-ready product by replacing the static dashboard with a real React app, exposing stable dashboard APIs, and restructuring the backend into understandable modules. The goal is a smoother operator flow: clear login, workspace-aware data, repo-level control, useful stats, and fewer “where do I click next?” moments.

This plan excludes `slothops-demo-app` and focuses only on `slothops-engine`.

## Product Goal
The dashboard should feel like an operations console, not a demo page. A new user should be able to:

1. Sign in.
2. See workspace health at a glance.
3. Connect GitHub and Sentry.
4. Inspect repos, policies, QA runs, rollbacks, and audit history.
5. Approve or bypass actions with clear permissions and traceability.

The backend should support that flow with predictable API contracts, workspace scoping, and data that is already shaped for the frontend.

## Current Problems To Fix
- `main.py` is too large and mixes auth, dashboard, webhooks, QA, rollback, and health logic.
- The dashboard is a static HTML page, so it is hard to build a dynamic UI on top of it.
- Several APIs return raw records instead of dashboard-ready responses.
- Auth exists, but the authorization model is not clearly surfaced for the frontend.
- Repo-specific data is present, but the UI has no clean way to browse it.
- The project layout is flat, which makes it hard for new contributors to understand where things live.

## Target Architecture

### Backend
Use a layered structure:

```text
slothops-engine/
  app/
    main.py
    api/
      auth.py
      dashboard.py
      repos.py
      qa.py
      rollbacks.py
      webhooks.py
      health.py
    core/
      config.py
      security.py
      deps.py
    services/
      dashboard_service.py
      auth_service.py
      repo_policy_service.py
      audit_service.py
    schemas/
      dashboard.py
      auth.py
      repos.py
  db/
  qa_agents/
  tests/
  web/
```

Keep root-level compatibility shims during migration so existing imports do not break immediately.

### Frontend
Create a real React dashboard in `slothops-engine/web/`:

```text
web/
  src/
    app/
    components/
    pages/
    hooks/
    lib/
    api/
```

Use it as the main operator UI instead of `static/index.html`.

## Backend API Changes

### Auth
Add or formalize these endpoints:
- `POST /api/auth/signup`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/auth/workspaces`

Auth response should include:
- user identity
- workspace id
- role/permissions
- session state

### Dashboard
Add dashboard-ready endpoints instead of forcing the frontend to assemble everything from many raw calls:
- `GET /api/dashboard/overview`
- `GET /api/dashboard/activity`
- `GET /api/dashboard/metrics`
- `GET /api/dashboard/repos`
- `GET /api/dashboard/qa`
- `GET /api/dashboard/rollbacks`
- `GET /api/dashboard/audit`
- `GET /api/dashboard/health`

These should return:
- counts
- status breakdowns
- recent events
- repo cards
- QA summaries
- rollback queue state
- integration health
- timestamped activity

### Repos
Strengthen repo-specific endpoints:
- `GET /api/repos`
- `GET /api/repos/{owner}/{repo}`
- `GET /api/repos/{owner}/{repo}/policy`
- `PUT /api/repos/config`
- `GET /api/repos/{owner}/{repo}/summary`

The repo payload should include:
- active/inactive state
- linked Sentry project
- current policy
- last QA run
- last rollback
- recent issue count

### QA / Rollbacks / Audit
Keep the existing workflows, but expose cleaner summaries for the frontend:
- paginated QA report lists
- rollback history with approval state
- audit trail with filters
- action status endpoints for approvals and bypasses

## Data Model Changes
Add dashboard-facing response schemas so the frontend does not depend on raw DB rows.

Create models for:
- `DashboardOverview`
- `DashboardMetric`
- `DashboardActivityItem`
- `DashboardRepoCard`
- `DashboardHealthStatus`
- `AuthSession`
- `WorkspaceSummary`
- `RepoSummary`

Keep existing core models, but add view-specific wrappers for frontend consumption.

## UX Changes

### Main Dashboard Flow
The new dashboard should have:
- a left nav for Overview, Repos, QA, Rollbacks, Audit, Settings
- a top bar with workspace selector, search, and connection status
- a main overview page with charts and operational summaries
- repo detail pages with policy, events, and recent actions
- action panels for approve/bypass/resolve flows

### UX Rules
- Prefer dense operational layouts over marketing-style cards.
- Show state first, actions second, documentation third.
- Surface approval states clearly.
- Never hide critical status behind nested clicks.
- Make the workflow obvious for a new company user:
  - connect repo
  - inspect policy
  - run QA
  - review failures
  - approve rollback if needed
  - inspect audit history

## Codebase Restructure Plan

### Step 1: Split backend responsibilities
Move logic out of `main.py` into router and service modules.

Exact target files:
- `slothops-engine/main.py` becomes a thin entrypoint or compatibility shim.
- `slothops-engine/app/main.py` owns the FastAPI app factory.
- `slothops-engine/app/api/auth.py`
- `slothops-engine/app/api/dashboard.py`
- `slothops-engine/app/api/repos.py`
- `slothops-engine/app/api/qa.py`
- `slothops-engine/app/api/rollbacks.py`
- `slothops-engine/app/api/webhooks.py`
- `slothops-engine/app/api/health.py`
- `slothops-engine/app/services/dashboard_service.py`
- `slothops-engine/app/services/audit_service.py`
- `slothops-engine/app/services/repo_policy_service.py`
- `slothops-engine/app/core/security.py`
- `slothops-engine/app/core/deps.py`

### Step 2: Preserve compatibility during migration
Keep old imports working while the new structure lands.

Example:
- old module names stay as wrappers
- new code imports the new package paths
- tests are updated gradually

### Step 3: Move frontend out of static HTML
Deprecate `static/index.html` as the main dashboard and replace it with the React app in `web/`.

Keep `static/` only for:
- logos
- favicon/assets
- optional fallback pages

### Step 4: Separate docs from runtime code
Move operator guidance into a clear docs section:
- `KT.md`
- `SLOTHOPS_LOCAL_TESTING.md`
- `docs/dashboard-api.md`
- `docs/frontend-flow.md`
- `docs/repo-onboarding.md`

## Frontend Implementation Plan
Use:
- React
- TypeScript
- React Router
- TanStack Query
- a lightweight component system

Frontend pages:
- Login / signup
- Overview
- Repositories
- QA reports
- Rollbacks
- Audit log
- Settings / integrations

Frontend data flow:
- authenticate once
- fetch workspace-scoped overview
- lazy-load repo/QA/rollback details
- use polling or SSE only where needed
- keep the UI reactive, but not noisy

## Security And Control Plan
- Enforce workspace scoping on every dashboard API.
- Add role checks for destructive actions.
- Return explicit forbidden responses for unauthorized actions.
- Prefer server-side permission checks over frontend-only hiding.
- Make approval actions auditable.
- Do not let the dashboard call raw mutation endpoints without guards.

## Recommended File Changes

### Modify
- `slothops-engine/main.py`
- `slothops-engine/database.py`
- `slothops-engine/models.py`
- `slothops-engine/auth.py`
- `slothops-engine/KT.md`
- `slothops-engine/README.md`
- `slothops-engine/static/index.html`
- `slothops-engine/requirements.txt`

### Add
- `slothops-engine/app/main.py`
- `slothops-engine/app/api/dashboard.py`
- `slothops-engine/app/api/auth.py`
- `slothops-engine/app/api/repos.py`
- `slothops-engine/app/api/qa.py`
- `slothops-engine/app/api/rollbacks.py`
- `slothops-engine/app/api/webhooks.py`
- `slothops-engine/app/services/dashboard_service.py`
- `slothops-engine/app/services/audit_service.py`
- `slothops-engine/app/schemas/dashboard.py`
- `slothops-engine/web/package.json`
- `slothops-engine/web/vite.config.ts`
- `slothops-engine/web/src/...`

### Eventually Remove Or Retire
- static dashboard-specific logic inside `main.py`
- any dashboard-only code in `static/index.html`

## Phased Delivery

### Phase 1: API contract
- extract dashboard data into service functions
- add overview and metrics endpoints
- formalize auth/session endpoints
- add repo summary endpoints

### Phase 2: React dashboard
- build login and workspace shell
- connect overview page
- connect repo detail pages
- wire QA, rollback, and audit views

### Phase 3: Backend cleanup
- split `main.py`
- move route groups into packages
- add API docs and schemas
- remove dead dashboard logic from the monolith

### Phase 4: Hardening
- add pagination/filtering
- add role-based controls
- add frontend smoke tests
- add API contract tests
- add onboarding docs for a new developer

## Acceptance Criteria
- A user can log in and land on a usable dashboard, not a static page.
- The dashboard shows workspace stats, repo state, QA state, rollbacks, and audit history.
- Repo and workspace actions are permissioned and auditable.
- The backend structure is readable for a new contributor.
- The React frontend uses stable APIs and does not depend on internal DB shapes.
- Existing engine workflows still work during migration.

## Short-Term Order
1. Define dashboard API schemas.
2. Extract dashboard service logic.
3. Build React shell.
4. Move `main.py` into router groups.
5. Update docs and tests.

