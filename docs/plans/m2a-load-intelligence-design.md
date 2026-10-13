# M2A-1 completed-exposure load intelligence design

Status: owner-authorized implementation under the 2026-10-06 task, following
M2B PR #76 merge/0021 activation. This bounded design does not accept Proposed
ADRs, numerical doctrine, all M2A, or deployment of an M2A migration.
Base: `f7a6ca5eba48f66800fe5d183ee8edf153ea3e4e`.

## Outcome and authority

Authored load guidance uses effective completed exercise occurrences instead of
submitted sets. Preserve source exercise, set count, per-set reps/effort,
techniques, order, relationships and block. Generated progression retains its
existing owner. Core decisions are deterministic; there is no runtime LLM.

One exposure is one workout/exercise occurrence with exact required effective
working-set coverage. Warm-ups, child sets, voids and retries cannot add
exposures. Partial work remains incomplete. Completed count and qualified
comparable count are distinct. Actual recorded load/reps/RPE are evidence;
planned or recommended values are not. Missing RPE remains unknown.

Use frozen source lineage (source SHA, importer/artifact version), original
source session/slot position, normalized typed prescription/technique,
performed variant and explicit unit/basis/equipment context as the comparison
key. Occurrence IDs identify evidence; source week is excluded from the key so
compatible later weeks can learn. Repeated source slots remain distinct.
Unknown legacy context, unresolved RIR/text effort, AMRAP/bodyweight/assistance,
contradictory semantics and mixed incomparable working loads yield monitor.
No old per-set counter or baseline becomes completed evidence.

## Deterministic decision owner

New pure `core_engine.load_intelligence` summarizes occurrences and returns
next-exposure and remaining-set decisions. Canonical authored rules already
declare top-of-range increase 2.5%, in-range hold, and under-target reduction
2.5% after two exposures. Apply that last gate to consecutive comparable
completed failures; one poor exposure cannot trigger long-term decrease.
Do not invent a two-success threshold or borrow Generated RIR policy.
Explicit per-set RPE targets qualify actual effort; no RPE/RIR conversion.
Unknown dimensions abstain. Hard source load directives constrain coaching.

For current partial work, a below-target set with actual RPE above its explicit
source upper target may offer a temporary load-only reduction using the named
canonical reduction percentage. This is separate from long-term exposure
progression. No authored rep/set/effort/technique change is permitted.

User-declared increments produce attainable rounding in their declared unit.
Without inventory/increment data, retain the existing 0.5 kg compatibility
semantics with an explicit feasibility limitation; never claim plate inventory.
Source rules, evidence IDs/digests, action, actual RPE coverage, completed and
qualified counts, consecutive failures, feasibility and explanations are traced.
Confidence means evidence sufficiency/comparability, not training outcomes.

## Persistence and API

Derive exposure summaries from owner-bound effective receipts and frozen source
snapshots; no separate exposure history table is needed. Add one
`AuthoredLoadState` table with unique `(user_id, comparison_key)` and versioned
JSON state/evidence. This reconstructible authored ExerciseState replacement
avoids contaminating the existing unnamespaced Generated `ExerciseState`.
Migration 0022 is additive, isolated-only and does not backfill unknowns.

Use the existing user-row lock and command ledger. Log/undo/correction flush,
rebuild affected authored cohorts and feedback, retain response and commit once.
Dispatch captured replay v1 to its original owner and authored v2 to the new
owner. Preserve absent-field normalization for old command hashes. Old retries
return original receipts and cannot resurrect voids. Rebuild later affected
recommendations when earlier evidence changes, retaining original receipt and
amendment provenance. Reads/preview do not persist load decisions.

Existing receipt `replay_context` JSON retains explicit load context, offered
recommendation/trace, actual chosen load and override reason. No recommendation
becomes performed history. Actual RPE already has a nullable persisted field.
Expose authoritative effective receipt IDs/reps/load/RPE for correction UI.
No phase-oriented CoachingRecommendation repurposing or telemetry is needed.

API `load_intelligence` feedback contains `next_exposure`, nullable
`remaining_sets`, resolved `load_context`, and `effective_sets`. Decisions add
content-bound `id`, `evidence_revision`, `scope`, nullable canonical-kg
`recommended_weight`, separate `known_baseline_weight`, `prefill_available`,
`action`, explanations, reasons, evidence, feasibility and trace. Optional
logging fields are `load_context`, `load_recommendation_id`, and
`load_override_reason`. A no-write load-guidance preview accepts an exercise
occurrence and explicit context; logging rechecks offered evidence under lock.

## Today and qualification

Optional actual-RPE entry is independent of source target, resets only after
acknowledgement, and remains in exact retry payloads. Explicit load-basis and
optional increment controls describe recorded context without guessing from
exercise names. Render server explanations. Prefill an untouched draft from
qualified server advice; preserve explicit user edits/pending commands. Display
conversion cannot invent rounding or change canonical recommended load.
Show effective receipts with correction/undo; authoritative refresh clears
stale advice. Preserve M2B local-date, rest, resume and consent behavior.

Tests cover the owner's 24 behavior boundaries, Generated/source negatives,
reconstruction, stale advice and retries. PostgreSQL independently qualifies
simultaneous final sets, duplicate commands, corrections and unique projection
state, plus additive legacy preservation. Playwright uses synthetic isolated
desktop/mobile users. Broad suites run once per final stable revision with the
known 4 core/8 API/1 web baseline reported separately. Push an unmerged PR and
own CI/Codex threads. No M2A migration or feature deployment is authorized.
