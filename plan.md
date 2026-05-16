# SlothOps MVP Overhaul Plan

## Summary
Turn SlothOps into a controlled operations platform, not a fully autonomous fixer. The MVP should ship three connected workflows: PR QA, deployment rollback with approval, and production error fixing with deep call-chain context. The goal is reliability, auditability, and predictable behavior on real repos so clients can trust the engine before full automation.

## Key Changes
- Reframe the product around policy, not just agents.
  - Add repo/workspace policy config for required checks, warning behavior, rollback mode, allowed environments, and default branch.
  - Require explicit `.slothops.yml` for client repos; use heuristics only as fallback.
  - Make every major action auditable: webhook received, repo resolved, agent run, rollback suggested, rollback approved, fix committed.

- Harden the PR QA pipeline.
  - Replace LLM-driven tool selection with deterministic triage.
  - Make static analysis, regression, and VAPT the default required set.
  - Keep functionality-generation, stress, and performance as optional/advisory based on repo risk.
  - Store structured QA reports, logs, and artifacts per PR.
  - Set GitHub commit status from policy, not hardcoded defaults.

- Make rollback safe by default.
  - Default to approval-first rollback, not silent auto-revert.
  - Validate deployment source, environment, branch, and rollback eligibility before action.
  - Record rollback decisions even when human approval is needed.
  - Add lock/idempotency so repeated deployment failures do not trigger duplicate reversions.

- Separate self-healing into a dedicated build-fix path.
  - Keep rollback and resolution as distinct steps.
  - Use real deployment/CI logs as the main prompt context.
  - Limit resolution attempts to a small, explicit retry budget.
  - Run the same QA gate on the generated resolution branch before considering it usable.

- Tighten the engine architecture.
  - Split `main.py` into route groups for auth, webhooks, QA, and rollback.
  - Split `llm_fixer.py` into separate fixers for code, QA resolution, and build/deploy failures.
  - Standardize GitHub App auth and webhook verification across all modules.
  - Move from SQLite to Postgres before external client rollout.

- Improve product usability.
  - Dashboard should show setup state, repo linkage, last QA run, rollback status, and resolution history.
  - Add explicit bypass/approval workflows with reasons.
  - Add per-repo settings rather than only workspace-wide controls.

## Test Plan
- Run the full engine unit suite and add integration tests for:
  - PR opened/synchronize
  - deployment failure
  - rollback approval flow
  - resolution retry flow
- Add mocked GitHub App webhook tests.
- Add end-to-end pipeline tests on one internal repo first.
- Then validate on one pilot repo with real developer activity.
- Add regression tests for:
  - duplicate webhook delivery
  - rollback loop prevention
  - QA warning handling
  - resolution attempt limit
  - deep call-chain recurrence fixes

## Assumptions
- Rollback default is approval first.
- MVP scope includes QA + rollback + Sentry/error-fixing, but Sentry stays lower priority than QA and deployment safety.
- Validation happens on internal repos and a pilot client repo in parallel, with tighter controls on the pilot.
- The first release should optimize for reliability and traceability over full autonomy.
