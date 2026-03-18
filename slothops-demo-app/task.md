# slothops-demo-app — Task Guide

This is the **target Node.js + TypeScript app** that SlothOps watches.  
It contains 3 intentional bugs for the demo. The existing test suite must PASS on `main` (bugs live in untested code paths).

---

## Repo Checklist

### Root Setup
- [ ] `package.json` with scripts: `dev`, `build`, `test`, `lint`, `typecheck`
- [ ] `tsconfig.json` — strict mode on
- [ ] `.env.example` with `SENTRY_DSN`, `JWT_SECRET`, `PORT`
- [ ] `eslint` configured

### `src/index.ts` — Express App Entry Point
- [ ] Initialize Express app
- [ ] Initialize Sentry SDK (`@sentry/node`) with DSN from env — MUST be the first import
- [ ] Register Sentry request handler middleware (before routes)
- [ ] Register Sentry error handler middleware (after routes)
- [ ] Mount routes: `/users`, `/orders`, `/auth`
- [ ] Start server on `process.env.PORT || 3000`

---

## Bug Implementation Checklist

### Bug 1: Null Reference (`src/routes/users.ts`)
- [ ] `GET /users/:id/profile` route
- [ ] `user.profile` can be `null` for new users who haven't completed onboarding
- [ ] Code MUST crash with `TypeError: Cannot read properties of null (reading 'displayName')`
- [ ] This code path is NOT covered by `tests/users.test.ts`
- [ ] Fix expected: optional chaining (`user.profile?.displayName`) or null guard

### Bug 2: Array on Undefined (`src/services/orderService.ts`)
- [ ] `getOrderSubtotal(orderId)` function
- [ ] `order.items` is `undefined` when order was just created (no items yet)
- [ ] Code MUST crash with `TypeError: Cannot read properties of undefined (reading 'reduce')`
- [ ] This code path is NOT covered by existing tests
- [ ] Fix expected: `(order.items ?? []).reduce(...)`

### Bug 3: Unhandled Auth Error (`src/middleware/auth.ts`)
- [ ] JWT verification middleware
- [ ] `req.headers.authorization` can be `undefined`
- [ ] `jwt.verify()` throws on invalid/expired tokens — not caught
- [ ] Code MUST crash with `TypeError` on missing header or `JsonWebTokenError` on bad token
- [ ] This code path is NOT covered by existing tests
- [ ] Fix expected: header existence check + `try/catch` with proper 401 response

---

## Services Checklist

### `src/services/userService.ts`
- [ ] `getUserById(id: string) -> User | null`
- [ ] Returns `null` for non-existent users (triggers Bug 1)
- [ ] Mock/in-memory data store for demo purposes

### `src/services/orderService.ts`
- [ ] `getOrderById(id: string) -> Order`
- [ ] Some orders have `items: undefined` (triggers Bug 2)
- [ ] Mock/in-memory data store

---

## Tests Checklist (`tests/`)

- [ ] `tests/users.test.ts` — test happy path for user routes (MUST PASS, NOT cover the bug path)
- [ ] `tests/orders.test.ts` — test happy path for order routes (MUST PASS, NOT cover the bug path)
- [ ] All tests pass on `main` branch with `npm test`

---

## CI Checklist (`.github/workflows/validate.yml`)

- [ ] Trigger on: `push` and `pull_request` to `main`
- [ ] Steps:
  - [ ] `npm ci`
  - [ ] `npm run lint`
  - [ ] `npm run typecheck`
  - [ ] `npm run test`
- [ ] GitHub Actions badge shows green for `main`
- [ ] When SlothOps opens a Draft PR, all CI steps must still pass

---

## Sentry Setup Checklist

- [ ] Create Sentry project (Node.js platform)
- [ ] Add DSN to `.env` as `SENTRY_DSN`
- [ ] Verify Sentry captures an error (check Sentry dashboard after triggering a bug)
- [ ] Configure Sentry webhook:
  - Dashboard: **Settings → Integrations → Webhooks**
  - URL: `https://your-engine-url/webhook/sentry`
  - Enable: `issue` events
- [ ] Test webhook delivery using Sentry's built-in test tool

---

## Definition of Done

- [ ] `GET /users/999/profile` → crashes → Sentry captures it
- [ ] Sentry fires webhook to engine within 30 seconds
- [ ] Bug 1, 2, 3 are all triggerable on demand
- [ ] All existing tests (`npm test`) pass on `main`
- [ ] GitHub Actions CI is green on `main`
- [ ] A SlothOps-generated PR passes CI checks
