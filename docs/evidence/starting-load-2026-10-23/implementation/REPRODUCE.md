# Reproduce the bounded application journeys

Read repository `AGENTS.md` and `DB_SAFETY_LOCK.md` first. This is synthetic local
qualification, not a production procedure. Never use inherited database or
Compose defaults. Do not run these seed helpers against live data.

The recorded run used a loopback-only postgres:16-alpine container with tmpfs data
and no mounts. Its explicitly verified database/user was
`initial_load_migration_1023` / `m2a_test` on 127.0.0.1:55418. A full additive
Alembic upgrade reached `0026_initial_calibration`; the preservation evidence is
linked from [IMPLEMENTATION](../IMPLEMENTATION.md). No database reset was used.

1. Prepare an isolated checkout and a verified disposable database. Supply a
   clean environment with explicit `DATABASE_URL`, matching `TEST_DATABASE_URL`,
   synthetic-only JWT secret and isolated temporary paths. Confirm SQL
   `current_database(), current_user` and container mount/port details **before
   app imports or migrations**. The seed helpers intentionally refuse a different
   target tuple; adapt only after independently verifying a new disposable target.
2. Install the pinned frontend dependencies and existing API/core test dependencies.
   Build and start only the isolated web app on 127.0.0.1:3020 with
   `SERVER_API_BASE_URL=http://127.0.0.1:8020`. Start its isolated API on
   127.0.0.1:8020. Never build into a running production checkout.
3. Run [seed-browser.py](seed-browser.py), then [seed-history.py](seed-history.py)
   from the checkout root under that explicit isolated Python environment.
   Each creates unique synthetic records; neither wipes prior records. The first
   writes private synthetic bearer credentials to the ignored
   `.qualification/browser-accounts.json`. Do not publish this file.
4. Run [journeys.cjs](journeys.cjs) with Playwright available. `PLAYWRIGHT_MODULE`
   and `CHROMIUM_EXECUTABLE` can select the locally installed module/browser.
   It uses the real application and API. `route.fetch()` commits requests and
   `route.abort()` discards their responses; it does not invent server responses.
   The script writes screenshots and assertion measurements into this directory.
5. Run [verify-browser-db.py](verify-browser-db.py) in the same isolated Python
   environment. It verifies source preservation, one calibration per command,
   retained correction/undo rows and unchanged qualified history. It exports
   only synthetic observations, without bearer tokens or password values.

Use fresh synthetic accounts for a complete rerun. The final recorded run passes
A–D and correction/undo/reload; earlier harness failures were discarded as failed
attempts. Re-running on a different application revision requires updating the
recorded revision fields, and does not inherit the prior run's result.

The browser run covers transport loss after commit. Fail-before-commit,
changed-payload conflict, pending actual edits, account isolation, stale context,
and further eligibility/numerical boundaries are exercised by the new API,
core and component regression suites. Browser evidence is supplementary.

A physical iPhone has not been tested. Follow the existing
[synthetic-device procedure](../../unified-ux-gym/correction-pass/REMAINING.md#safe-physical-iphone-procedure-pending-execution)
on an isolated reachable test deployment. Chromium viewport captures do not
qualify Safari keyboard, background suspension or device-specific behavior.
