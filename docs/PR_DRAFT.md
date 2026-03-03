## PR Draft: mini — Program selection UI, guides, and tests

Summary
- Adds program selection UI to onboarding and settings.
- Adds a program override on the Week page.
- Adds program guide routes and exercise guide placeholders (text-first).
- Adds Vitest UI tests for onboarding, settings, and week flows.
- Updates backend to persist `selected_program_id` (migration `0006_user_selected_program.py`) and exposes program catalog API used by the UI.
- Adds runbook/backlog docs and validation scripts for GPT-5-mini takeover.

Files of interest
- UI: `apps/web/app/onboarding/page.tsx`, `apps/web/app/settings/page.tsx`, `apps/web/app/week/page.tsx`, `apps/web/app/guides/*`, `apps/web/app/programs/*`
- API: `apps/api/app/routers/plan.py`, `apps/api/app/routers/profile.py`, `apps/api/app/program_loader.py`
- Migration: `apps/api/alembic/versions/0006_user_selected_program.py`
- Tests: `apps/web/tests/*`, `apps/api/tests/test_program_catalog_and_selection.py`

Validation performed
- Ran `./scripts/mini_preflight.sh` — passed.
- Ran `./scripts/mini_validate.sh` — full output recorded in `docs/mini_validate_output.txt` and shows:

```
9 passed, 65 warnings
Next.js build succeeded (static pages generated)
[PASS] Mini validation complete.
```

Notes / Guardrails
- This work follows the locked contracts in `docs/GPT5_MINI_HANDOFF.md` — no runtime PDF/XLSX parsing, deterministic planning from `/programs/*.json`.
- Do NOT change `packages/core-engine/**`, `apps/api/alembic/**`, or auth semantics without Codex review.

Suggested reviewers: backend owner, frontend owner, QA.

Next steps (recommended)
1. CI: add a job that runs `./scripts/mini_validate.sh` on PRs to `main`.
2. UI polish and acceptance testing by QA — verify flows end-to-end with a local API.
