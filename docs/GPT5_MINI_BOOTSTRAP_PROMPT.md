# GPT-5-mini Bootstrap Prompt

Use this prompt at the start of every mini session:

---
You are GPT-5-mini continuing work in this repository.

Before writing code:
1. Read `docs/GPT5_MINI_HANDOFF.md`, `docs/GPT5_MINI_EXECUTION_BACKLOG.md`, `docs/GPT5_MINI_RUNBOOK.md`, and `docs/GPT5_MINI_SUCCESS_PLAN.md`.
2. Run `./scripts/mini_preflight.sh`.
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
