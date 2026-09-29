# M0-HIST-B correction and reconstruction

Status: primary implementation merged as PR #40 and owner-authorized deployment completed.
[Activation and remaining qualification](../evidence/2026-09-28-m0-hist-b-activation.md)
records the subsequent task authorization and rollout. Original implementation
criteria and pre-merge evidence below retain their dated scope.
Owner authorization: explicit 2026-09-28 task to implement this package, rehearse
its migration on disposable PostgreSQL, and open an unmerged PR. Deployment of
HIST-B was **not authorized by that implementation task**. The subsequent explicit
merge/deployment task authorized only live 0020 and affected API/web activation. Base: `e763c8392e3c1bf4c5b6367382c5a3d8ab04348c`.
Branch: `m0/hist-correction-reconstruction`.

Related: [ADR-005](../adr/0005-training-history-identity-and-correction.md),
[execution contract](../contracts/execution-plan.md),
[load contract](../contracts/load-progression.md),
[data model](../architecture/data-model.md),
[HIST requirements](../requirements/catalog.md#hist),
[roadmap](../roadmap/milestones.md),
[qualification](../evidence/2026-09-28-m0-hist-b.md).
These links retain their separate approval/acceptance status.

## Bounded behavior

Undo voids the effective record and retains its performance. Correction creates
a replacement linked to its predecessor; original performance never changes.
History calculations read effective records. An owner-scoped audit endpoint
returns the lineage, receipt/correction/void times, reason and action source.

The API records the actual pre-log projection and deterministic decision inputs
for new logs. Correction replays the existing core load policy in original
receipt order, starting from the first captured baseline. It rebuilds all five
progression fields and the effective-history timestamp, then reconstructs the
requested occurrence/exercise session from effective qualifying work sets.
This package fixes stale projections; it does not replace the M2A algorithm.
Earlier missing context stays an explicit boundary. Unsupported legacy or
intersecting uncaptured history conflicts without committing a partial edit.

Logging, correction and undo share the PostgreSQL user-row lock and command
ledger. Old log retries return their original receipt without resurrecting a
voided record. Action retries return the original action result; changed inputs
conflict. Modern Today keeps an undo command through lost acknowledgements,
waits for confirmation, and refreshes authoritative counts/load guidance.

Later cached previews/review summaries are conservatively invalidated while
retaining payloads and already applied decisions. Future consumers exclude those
invalidated summaries. Applied decisions and existing authored/generated plans
are not retrospectively rewritten.

## Criteria and rollout boundary

HIST-001/002/003 retry, ownership and occurrence boundaries remain in force.
HIST-004 is covered for captured-context undo/correction and deterministic
reconstruction; HIST-005 preserves unknown legacy identity and effort. Tests
cover original/replacement audit, effective views, prior/later exposures,
week/repeated-slot isolation, rollback and PostgreSQL log/correction and log/undo
races. [Evidence](../evidence/2026-09-28-m0-hist-b.md) records actual results and limits.

Migration `0020_workout_set_amendments` is additive and preserves legacy NULLs.
It must precede any future HIST-B activation. It was rehearsed only on synthetic
targets and deliberately refuses an automatic data-discarding downgrade. A live
backup, recovery plan, migration/activation approval and review disposition remain
future gates. No HIST-B migration or deployment occurs in this package.

Remaining M0-HIST: explicit exposure/finalization semantics, occurrence revision
transitions, performed-variant/unit evidence, historical replay coverage policy,
correction UI, occupied/gapped set-slot runner behavior, wider concurrency and
real-browser/device qualification. Metadata-v2 scoring stays frozen. SEC-S2,
ADR acceptance, whole-M0 acceptance and release owner acceptance remain separate.
