# GPT-5-mini Runbook

## Preflight
1. Read:
   - `docs/GPT5_MINI_HANDOFF.md`
   - `docs/GPT5_MINI_EXECUTION_BACKLOG.md`
   - `docs/GPT5_MINI_SUCCESS_PLAN.md`
   - `docs/Master_Plan.md`
2. Confirm current repository state is clean and reproducible.
3. Run automated preflight:

```bash
cd /home/rocco/hypertrophyapp
./scripts/mini_preflight.sh
```

## Working Agreement
- Keep implementation focused: complete one backlog task at a time, end-to-end.
- GPT-5-mini is authorized for full-stack implementation in this repository.
- GPT-5-mini can modify backend, frontend, tests, scripts, and docs as needed.
- Push directly to `main` after validations pass.

## Mini Execution Loop (Required)
1. Choose one not-started item from `docs/GPT5_MINI_EXECUTION_BACKLOG.md`.
2. Implement that task across all required files.
3. Run `./scripts/mini_validate.sh`.
4. If validation fails, fix issues and re-run until green.
5. Update docs/checklist notes and continue with next priority task.

## Quick Commands

### One-command session flow
```bash
cd /home/rocco/hypertrophyapp
./scripts/mini_session.sh
```

### Session start (pick next backlog task)
```bash
cd /home/rocco/hypertrophyapp && awk '/^### Task/{task=$0} /^ Status:/{if($0 !~ /COMPLETED/){print task; exit}}' docs/GPT5_MINI_EXECUTION_BACKLOG.md
```

Use the printed task as the starting target for the current mini session.

### One-command validation
```bash
cd /home/rocco/hypertrophyapp
./scripts/mini_validate.sh
```

### API regression checks
```bash
cd /home/rocco/hypertrophyapp
docker compose exec -T api sh -lc 'cd /app/apps/api && PYTHONPATH=. pytest tests -q'
```

### Web compile check
```bash
cd /home/rocco/hypertrophyapp/apps/web
npm run build
```

## Failure Handling

### If API test fails
- Re-run only failing test first.
- Fix root cause and re-run full validation.

### If web build fails
- Fix TS/ESLint/local UI logic errors.
- Do not change backend to bypass compile issues.

## Definition of Safe Completion
- Target task acceptance criteria met.
- API regression command passes.
- Web build passes.
- Web test suite passes.
- Working tree is clean after commit.

## Completion Checklist

- Run `./scripts/mini_preflight.sh`.
- Run `./scripts/mini_validate.sh`.
- Add or update tests for changed behavior.
- Commit with clear message and push to `main`.
