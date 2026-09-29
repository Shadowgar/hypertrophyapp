# M1-B authored constraint authority and explicit substitutions

Status: PR #42 merged and API/web activated under owner authorization; see
[activation evidence](../evidence/2026-09-29-m1-authored-constraints-activation.md).
Base main: `32865d4f36ca11538e5762dab3029d5bafd5d517`.
Branch: `m1/authored-constraint-authority`. The owner subsequently authorized
fixing the three PR #42 review defects, merging after fresh review/qualification,
and activating API/web without a migration. ADR and whole-M1/release acceptance
remain separate.

Governing [product](../requirements/product-contract.md),
[ADR-002](../adr/0002-mode-authority-and-consent.md),
[ADR-003](../adr/0003-authored-source-immutability-and-compilation.md),
[source](../contracts/authored-source.md), [execution](../contracts/execution-plan.md),
[AUTH-FID-002/004](../requirements/catalog.md#auth-fid),
[runtime authority](../architecture/runtime-authority.md),
[roadmap](../roadmap/milestones.md).

## Bounded behavior

Recognized authored templates always retain passthrough protection, including
restriction and frequency-adaptation fallback branches. The deterministic
`core_engine.authored_constraints` owner annotates only conflicting source slots
using declared movement/equipment metadata. No generic weak-point/review, set,
rep, effort, technique, dose or block redesign is unlocked. Generated paths retain
the existing behavior; metadata-v2 scoring remains frozen.

Loader source permission comes only from the exact slot's raw substitution
options, uniquely resolved canonical names/aliases, source/artifact hashes and
slot lineage. Generic library similarities do not grant permission. Unknown,
ambiguous or incompatible metadata yields no qualified executable choice; the
raw source remains intact and the slot stays visibly unresolved/infeasible.
Empty equipment profiles remain unknown, not a claim of missing every item.
Equipment tags are conservatively required together for feasibility.

Occurrence report/confirm/decline commands use the existing user write lock and
retry ledger, pin occurrence/source identity and consent revision, and reject
stale/foreign/unsupported requests without mutation. Confirmation alone adds a
separate performed variant, original prescription, source permission, user/time
and conflict reason to the frozen occurrence JSON. The source exercise/slot and
occurrence UUIDs are unchanged. Decline does not delete work. Regeneration never
transfers consent. Started occurrences cannot silently replace variants; a new
pain/safety/profile conflict pauses execution without rewriting receipts.

Today requires deliberate confirmation and disables unresolved logging; generic
local authored swaps are disabled. History/day receipts expose frozen source,
variant and consent identity. Correction/undo preserves it. Variant receipts do
not update original exercise progression, weekly numeric load advice or original
exercise PR/trend comparisons. Actual load is recorded; comparable variant load
advice is explicitly unavailable. This is not a new M2 exposure/load model.
Legacy slots without source permission can report/retain conflicts, but cannot
invent a qualified alternative or historical consent.

## Qualification and remaining boundaries

[Scoped evidence](../evidence/2026-09-29-m1-authored-constraints.md) and its
[manifest](../evidence/2026-09-29-m1-authored-constraints.manifest.json) bind the
candidate tests/files. Eleven owner cases plus retry, stale/ownership, equipment,
pain, correction/undo and variant comparability negatives are covered by isolated
API/core/web tests. No schema/artifact/source migration. No M1-B live operations.

Review must assess metadata completeness and conservative feasibility, real
browser/background behavior, PostgreSQL concurrent consent qualification and
source relationship/order fidelity. Unknown source alternatives remain unresolved,
not silently mapped. Actual-date scheduling, load/exposure intelligence, personal
response modeling and generated redesign remain later separately approved work.
