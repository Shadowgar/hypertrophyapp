# M0-HIST-B activation and remaining qualification

Status: owner-authorized deployment completed on 2026-09-28. This record follows
[pre-merge HIST-B qualification](2026-09-28-m0-hist-b.md); it does not rewrite that
record's revision/environment or grant milestone, ADR or release acceptance.

PR #40 head: `e49d77284e6ee0d778a9c20d62342a48ce26373c`.
Merge and resulting main: `6e9b93ebc2f4570eeb0517131332e135b1d5c566`.
Codex completed on the expected head with no findings; no unresolved threads or
requested changes remained. The red application qualification contained the
previous eight API baseline/fixture failures, four core failures, calendar failure
and 102 TypeScript diagnostics. CodeRabbit and Copilot did not perform reviews.
The owner explicitly authorized merging despite those documented baseline failures.

## Live rollout evidence

The production development checkout was fast-forwarded to the merge while
preserving its pre-existing tracked debug-log modification. API/web images were
built from the exact reviewed source tree; their revision labels and retained
service environments were verified without printing secrets. The exact API
image passed 29 focused SQLite history tests; six PostgreSQL-only cases were
skipped in this image check. Prior PostgreSQL qualification remains separately
recorded against the reviewed HIST-B revision.

The API was stopped before a fresh PostgreSQL custom-format backup. The command
succeeded, the archive was nonempty and `pg_restore --list` could read it. The
private backup is retained outside Git. This is archive-readability evidence,
not a restore rehearsal or a complete disaster-recovery qualification.

The actual database/user/host/port and starting revision 0019 were verified in
memory. Only `0020_workout_set_amendments` was applied. Existing table counts and
all pre-existing fields in the six workout/history/projection tables matched
before and after. New amendment/context fields remained NULL for existing logs.
No schema migration beyond 0020, database reset/reseed/wipe or workout-history
deletion occurred.

Only API/web were recreated. PostgreSQL remained healthy; API/web were running
and the API health endpoint returned 200. No API/web container healthcheck is
configured, so this does not claim a Docker `healthy` status for those services.
The homepage, Today, Week and history page routes returned 200. Read-only requests
using an existing account's in-memory token returned 200 for Today, latest Week,
history analytics/calendar, workout progress and summary. Existing plans were
accessible. No fake workout history or real-account password-reset test was
performed. Tokens, secret values and private record contents were not emitted.

## Remaining M0-HIST work

HIST-001 through HIST-004 received their primary implementation through PR #39
and PR #40. Their whole-criterion acceptance remains separate from the scoped
implementation and qualification evidence. HIST-005 and these follow-ups remain
open and, by the owner's explicit sequencing decision, do not block M1-A:

- Ambiguous legacy replay/mapping coverage; never fabricate historical context.
- Exposure/finalization semantics required before M2A load intelligence.
- Occurrence revisions and reschedule/correction lineage.
- Performed variant and unit evidence/comparability.
- Dedicated correction UI.
- Gapped-slot runner behavior.
- Broader real-browser and PostgreSQL concurrency qualification.

No additional broad HIST implementation loop was started. The next authorized
application package is [M1-A source fidelity](../plans/m1-authored-source-fidelity.md).
M1 changes are review-only and were not included in this activation.
