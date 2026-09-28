# M1-A persisted-plan weekly-review identity follow-up

Status: PR #41 correctness candidate awaiting fresh review and owner-authorized
merge/activation; no milestone, ADR or release acceptance.
Parent: `daa612cb5d223c74e9585ceb919d3977cb220897`.
The containing commit and hashes below identify this correction.
[Preceding qualification](2026-09-28-m1-bodyweight-summary.md) remains scoped to
its own procedures and snapshot.

The completed parent Codex review found a P2: stored WorkoutPlan payloads lack
exercise occurrence UUIDs, while serialized receipts have UUIDs. Choosing that
unmatched UUID prevented fallback to frozen source-slot lineage and incorrectly
marked valid numeric receipts ambiguous. Review now considers both identities,
prefers matching occurrence keys, and otherwise matches frozen source-slot keys.
Typed targets stay excluded; unknown legacy receipts stay explicitly ambiguous.
No source dose, weekly numeric fault policy or recommendation threshold changes.

A copied core package under the verified disposable test root, cleared environment,
socket/database guard, explicit SQLite targets and disabled caches/plugin autoload
qualified **5 authored prescription/review tests passed**. The new case calls the
production serializer with raw persisted-plan shape and receipt objects carrying
both occurrence UUIDs and frozen source lineage. Numeric completion and below-target
fault remain; no false missed-set fault or ambiguous count appears. Existing
occurrence-key and legacy-ambiguity cases still pass. This is scoped core/serialization
evidence, not a full API or PostgreSQL concurrency claim.

| Evidence | SHA-256 |
|---|---|
| `packages/core-engine/core_engine/decision_weekly_review.py` | `bf91c9e24e8f7a1e746a250f77e450d922ee72798fee9341f097b85f0334e8cc` |
| `packages/core-engine/tests/test_authored_prescription.py` | `086137a790061e5197920391aa9e88867ab8326709a7f5507512e0ed9ba6854f` |
| Temporary owner test output (not publicly retained) | `3de0922879cc7b6509a3ad1ea40ed1f93b71bfe1a47df2a0588277d5be9a14dd` |

No compiler input changes; existing artifact/source hashes remain unchanged.
No live data, schema, service or production checkout changes occurred for this fix.
