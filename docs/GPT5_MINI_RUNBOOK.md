# GPT-5-mini Runbook

## Preflight
1. Read:
   - `docs/GPT5_MINI_HANDOFF.md`
   - `docs/GPT5_MINI_EXECUTION_BACKLOG.md`
   - `docs/Master_Plan.md` (Model Ownership section)
2. Confirm no locked-contract file edits are required.
3. Run automated preflight:

```bash
cd /home/rocco/hypertrophyapp
./scripts/mini_preflight.sh
```

## Working Agreement
- Keep implementation scope small: one backlog task at a time.
- If uncertain, stop and route to GPT-5.3-Codex.
- Preserve existing API routes and payload structure.
- GPT-5-mini does not open, manage, or troubleshoot PRs; PR operations are handled by a human or GPT-5.3-Codex.

## Mini Execution Loop (Required)
1. Choose one not-started item from `docs/GPT5_MINI_EXECUTION_BACKLOG.md`.
2. Implement only that task in allowed files.
3. Run `./scripts/mini_validate.sh`.
4. If validation passes, update docs/checklist notes and stop.
5. If validation fails in locked-contract areas, escalate to GPT-5.3-Codex immediately.

## Quick Commands

### One-command validation
```bash
cd /home/rocco/hypertrophyapp
./scripts/mini_validate.sh
```

### API regression checks
```bash
cd /home/rocco/hypertrophyapp
docker compose exec -T api sh -lc 'cd /app/apps/api && PYTHONPATH=. pytest tests/test_program_catalog_and_selection.py tests/test_profile_schema.py tests/test_workout_resume.py tests/test_program_loader.py -q'
```

### Web compile check
```bash
cd /home/rocco/hypertrophyapp/apps/web
npm run build
```

## Failure Handling

### If API test fails
- Re-run only failing test first.
- Check whether failure touches locked contracts.
- If locked contracts are involved, escalate to GPT-5.3-Codex.

### If web build fails
- Fix TS/ESLint/local UI logic errors.
- Do not change backend to bypass compile issues.

## Definition of Safe Completion
- Target task acceptance criteria met.
- API regression command passes.
- Web build passes.
- No edits to forbidden zones.

## Handoff Checklist (for human/Codex PR owner)

- Run `./scripts/mini_preflight.sh` and include its output in PR description.
- Run `./scripts/mini_validate.sh` locally or in CI and attach the logs.
- Ensure `apps/web` `npm run build` completes without errors.
- Add or update unit tests for UI behavior where applicable.
- Confirm no changes to `packages/core-engine` or `apps/api/alembic`.
- Add brief testing notes and any manual verification steps in PR description.

Note: GPT-5-mini should not perform PR creation or review workflow tasks.
