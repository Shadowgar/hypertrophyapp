# GPT-5-mini Bootstrap Prompt

Use this prompt at the start of every mini session:

---
You are GPT-5-mini continuing work in this repository.

Before writing code:
1. Read `docs/GPT5_MINI_HANDOFF.md`, `docs/GPT5_MINI_EXECUTION_BACKLOG.md`, `docs/GPT5_MINI_RUNBOOK.md`, and `docs/GPT5_MINI_SUCCESS_PLAN.md`.
2. Run `./scripts/mini_session.sh` (preferred) or `./scripts/mini_preflight.sh`.
3. Pick the highest-priority backlog task (command below) and continue until complete.
4. You may edit any repository area required to complete the task.

```bash
cd /home/rocco/hypertrophyapp && awk '/^### Task/{task=$0} /^ Status:/{if($0 !~ /COMPLETED/){print task; exit}}' docs/GPT5_MINI_EXECUTION_BACKLOG.md
```

After coding:
1. Run `./scripts/mini_validate.sh`.
2. Fix failing tests/build issues in-scope until green.
3. Summarize changes with file paths and acceptance criteria.
4. Commit and push to `main` when validation passes.

Operating constraints:
- Preserve deterministic runtime rules.
- No runtime PDF/XLSX parsing.
- Keep code quality high: tests updated, validations passing, and no unrelated churn.
---

## Progress Sync (2026-03-06)
- Repository state synchronized through commit `09ac04e` on `main` (pushed to `origin/main`).
- Validation baseline is green via `./scripts/mini_validate.sh`:
  - API: `60 passed`
  - Web tests: `16 passed`
  - Web build: success
- Latest delivered stabilization work:
  - fixed containerized API test DB resolution to prefer `DATABASE_NAME`
  - added regression coverage for test DB configuration precedence
  - fixed Settings test by mocking `next/navigation` router
  - resolved web lint/build blockers in `today` and `history` routes
  - removed invalid `<center>` nesting from the home page markup
- Known follow-up (non-blocking): Vitest reports `2 obsolete` snapshots in `apps/web/tests/visual.routes.snapshot.test.tsx`.
- Drift prevention protocol for next sessions: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

