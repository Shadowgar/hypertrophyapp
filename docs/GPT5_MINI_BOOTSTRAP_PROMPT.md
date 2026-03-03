# GPT-5-mini Bootstrap Prompt

Use this prompt at the start of every mini session:

---
You are GPT-5-mini continuing work in this repository.

Before writing code:
1. Read `docs/GPT5_MINI_HANDOFF.md`, `docs/GPT5_MINI_EXECUTION_BACKLOG.md`, and `docs/GPT5_MINI_RUNBOOK.md`.
2. Run `./scripts/mini_preflight.sh`.
3. Pick exactly one backlog task.
4. Do not edit forbidden areas (core engine, migrations, auth/security semantics).

After coding:
1. Run `./scripts/mini_validate.sh`.
2. If any failure touches locked contracts, stop and escalate to GPT-5.3-Codex.
3. Summarize changes with file paths and acceptance criteria.

Operating constraints:
- Preserve deterministic runtime rules.
- No runtime PDF/XLSX parsing.
- Keep PR scope small and testable.
---
