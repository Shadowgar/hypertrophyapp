# M2B-1 live activation

Date: 2026-10-06. Status: **M2B-1 LIVE**, not whole-M2B completion.
Owner authorization: explicit merge/deploy-0021 task after review of PR #76.
Approved head: `3f836474a9f260889d4feed14600d299edd12bbc`.
Merge and resulting main: `f7a6ca5eba48f66800fe5d183ee8edf153ea3e4e`.
[PR #76](https://github.com/Shadowgar/hypertrophyapp/pull/76) and
[activation record](https://github.com/Shadowgar/hypertrophyapp/pull/76#issuecomment-6025036171).

Before merge, current head/mergeability, resolved eight review threads,
exact-head Codex no-additional-major-issues review and final checks were verified.
CI retained only recorded four core/eight API/one web failures; lint, typecheck,
build, docs/workflows, CodeQL and GitGuardian passed. The merge tree exactly
matches the reviewed feature tree. Earlier qualification and managed-security
artifact retention limitations remain in the
[implementation evidence](2026-10-06-m2b-actual-date-scheduling.md).

Production checkout advanced by fast-forward. The unrelated tracked
`logs/app-debug.log` stayed byte-identical, SHA-256
`e920b78d4b45854dbbc14579574b9195205c6a5bbad4684ee2bad13398001f22`.
API/web were rebuilt as `hypertrophyapp-api:m2b-f7a6ca5` and
`hypertrophyapp-web:m2b-f7a6ca5`, preserving effective environment and API
startup command. No unrelated services or production configuration were changed.

API writes were stopped for final backup/migration/integrity verification.
A fresh private custom-format PostgreSQL backup succeeded, size 102,083 bytes,
mode 0600 in a private directory. SHA-256
`63912a71dc7e670895869a1cd6d89cc9730aba5f118ec4832f9a600ea5ab0115`.
Archive-list and complete read/decompression checks passed. No actual restore
or broader RPO/RTO qualification is claimed; no credentials/private rows are
published. An initial read-only fingerprint SQL quoting error occurred before
migration, was corrected, and did not change data or schema.

Only `0021_selected_workout_dates` was applied live. Alembic revision afterward
matches it. Across all 13 original public tables, row counts and hashes of all
original columns are unchanged. Aggregate SHA-256 before/after:
`407e423078f34c0b1958bf3a90bbb4b4f6ca9f2bbc99b88aa2fe25f42172244c`.
All six new legacy date/timezone/revision values remain NULL; no backfill.
PostgreSQL kept its original start time and was not restarted.

API/web restarted on the new images. Public `/api/health` returns status `ok`,
version `f7a6ca5`; both services completed startup with zero detected error lines.
Playwright desktop 1440×900 and mobile 390×844: home/login rendered; Today,
Week and History redirected to login. All ten pages had no horizontal overflow,
page/runtime errors or HTTP error responses. Two representative screenshots
were additionally inspected during integration. No safe authenticated session
was available, so authenticated Today/Week/existing-history rendering remains
unverified. Migration integrity confirms stored history is preserved, separately
from that browser limit. No account/login/history writes were made.

The read-only browser guard blocked Cloudflare RUM/challenge POSTs, producing
52 classified client-blocked console errors; other console errors/warnings
were zero. An initial network-idle timeout is retained; the completed pass used
DOM/visible-form readiness. This is not represented as entirely silent console
output. Sanitized screenshots/JSON and private command results are retained in
the host qualification artifacts; backups and production records are not in Git.

Live DB was not reset, reseeded or wiped; no real history was deleted. Only
0021 was applied live. Remaining M2B: timezone-change policy, missed-workout
carryover, future/recurring selection, adjacent-week context, duration calibration
and external calendar work only if separately approved. M2A is a separate
implementation/qualification package and has no deployment authorization.
