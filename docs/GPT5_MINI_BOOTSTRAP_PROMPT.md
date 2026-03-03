# GPT-5-mini Bootstrap Prompt

Use this prompt at the start of every mini session:

---
You are GPT-5-mini continuing work in this repository.

Before writing code:
1. Read `docs/GPT5_MINI_HANDOFF.md`, `docs/GPT5_MINI_EXECUTION_BACKLOG.md`, and `docs/GPT5_MINI_RUNBOOK.md`.
2. Run `./scripts/mini_preflight.sh`.
3. Pick exactly one backlog task (command below).
4. Do not edit forbidden areas (core engine, migrations, auth/security semantics).

```bash
cd /home/rocco/hypertrophyapp && awk '/^### Task/{task=$0} /^ Status:/{if($0 !~ /COMPLETED/){print task; exit}}' docs/GPT5_MINI_EXECUTION_BACKLOG.md
```

After coding:
1. Run `./scripts/mini_validate.sh`.
2. If any failure touches locked contracts, stop and escalate to GPT-5.3-Codex.
3. Summarize changes with file paths and acceptance criteria.
4. Stop after implementation handoff; do not create or manage PR workflows.

Operating constraints:
- Preserve deterministic runtime rules.
- No runtime PDF/XLSX parsing.
- Do not perform PR creation/review/merge steps; hand PR tasks to a human or GPT-5.3-Codex.
---
