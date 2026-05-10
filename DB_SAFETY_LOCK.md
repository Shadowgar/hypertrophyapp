# DB SAFETY LOCK (LOCAL)

This environment contains live user data.

Hard block for assistant/operator workflows:
- Do NOT run `Base.metadata.drop_all(...)`.
- Do NOT run `Base.metadata.create_all(...)` as a reset pair.
- Do NOT run destructive test reset helpers against live compose services.
- Do NOT run `docker compose down -v` for this project.
- Do NOT run destructive SQL (`DROP`, `TRUNCATE`, `DELETE` without explicit user approval).

Required before any test/probe involving persistence:
1. Use isolated test DB/container only.
2. Verify target DB/user context first.
3. If uncertain, stop and ask user before proceeding.

Created: 2026-05-10
Reason: Prevent repeat accidental account/data wipes.
