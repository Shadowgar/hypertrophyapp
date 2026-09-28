# M0-HIST-A merge and live development activation

Recorded 2026-09-28 under the owner's explicit PR #39 merge/deployment task.
This supplements the [pre-merge qualification](2026-09-28-m0-hist-a.md);
it does not convert that historical test snapshot into current HIST-B evidence.

## Revisions and review disposition

[PR #39](https://github.com/Shadowgar/hypertrophyapp/pull/39) merged at
`e763c8392e3c1bf4c5b6367382c5a3d8ab04348c`; resulting main is that revision.
Final source head: `aaf8de7b603ede57fe15058875a1ec178f56f47a`.
Wipe-FK fix: `3bcfa41f0d5928666f129cb2e86069b29770085c`.
The final follow-up prevents distinct commands claiming the same logical set
slot and refreshes the qualification manifest. Both authorized wipe flows were
tested with FK enforcement on SQLite and migrated disposable PostgreSQL,
including preservation of another user's history. These tests wiped synthetic
users only.

All three applicable Codex threads were replied to and resolved. The final head
review completed at 14:29:03 UTC with no major issues. No outstanding P0/P1 or
introduced correctness/data-integrity P2 remained. Final CI had eight known
API baseline/licensed-fixture failures, four core baseline failures, the existing
web calendar test failure and 102 existing test-global TypeScript diagnostics.
Documentation/workflow/classification, web build/lint, CodeQL and GitGuardian
passed. Skipped CodeRabbit/Copilot reviews were not counted as substantive reviews.

## Live procedure and observed results

The development checkout fast-forwarded to merged main, preserving its unrelated
tracked debug-log modification. API/web images were built from a clean Git
archive of the final source head, with immutable source labels. Environment
values were compared in memory to the running services and retained unchanged;
no signing key or other secret was replaced by this task.

The API was stopped before a fresh live PostgreSQL custom-format dump. The dump
command succeeded, the private artifact was non-empty, and `pg_restore --list`
succeeded without publishing its contents. Storage remains private (directory
0700, file 0600). No backup contents, credentials, path or digest are in Git.
This verifies a readable dump, **not** a restore rehearsal or RPO/RTO.

The live target/backend and starting revision were verified before DDL. Only
`0018_choose_for_me_diagnostics` → `0019_workout_occurrence_identity` ran live.
Existing table row counts were unchanged; old log identities remained NULL and
new occurrence/command tables were empty before activation. No data reset,
reseed, history deletion or guessed backfill occurred. An initial migration
probe using `/dev/stdin` failed to import the app before any DDL; the corrected
`python -` invocation completed the approved migration.

Only API/web were recreated with the pinned HIST-A images; PostgreSQL and the
other services were not recreated. API/web stayed running with no restart loop;
PostgreSQL was healthy. API health, homepage and Today/Week/History page responses
were HTTP 200. Protected read-only Today, latest Week, history analytics/calendar
and existing workout progress/summary requests all returned 200. Today/Week
responses included occurrence IDs. No fake real-user workout record was created.

Read-only requests used an ephemeral credential solely in memory. No token,
account identity, private history payload or secret was printed. The startup
signing validator passed, startup logs contained no live signing-key value, and
no smoke request returned 500. These checks do not establish a populated-history
browser journey, every secret's log handling, concurrency in production or full
release qualification.

## Remaining boundary

Production runs HIST-A at schema 0019. HIST-B and migration 0020 are unmerged and
undeployed in the [next package](../plans/m0-hist-correction-reconstruction.md).
ADR-005, whole M0-HIST and release owner acceptance remain unaccepted.
SEC-S2 still covers session/revocation lifecycle, atomic reset consumption,
PostgreSQL concurrency qualification, auth-version migration/cutover and
distributed abuse controls; this history activation changes none of those statuses.
