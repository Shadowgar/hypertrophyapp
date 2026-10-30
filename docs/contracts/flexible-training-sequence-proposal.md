# Completion-driven flexible training — proposed server contract

Status: **Proposed mechanism, awaiting owner approval**. Base:
`dca2dc3ebebfbde26cae0333c9db0d050ca44dff`. Related: [#105](https://github.com/Shadowgar/hypertrophyapp/issues/105),
[bounded plan](../plans/flexible-training-progression.md). No runtime activation,
DDL, production operation, source rewrite or release acceptance is granted here.

## Owner decisions and requested behavior

On 2026-10-30 the owner requested tentative calendar dates, expected training
frequency without weekdays, explicit Start/Resume, missed-work retention and
completion-driven source progression. In the subsequent question the owner chose:
**retain original source workouts and let a source block span more than seven
days**. Do not redistribute a new Flexible Authored block into the expected
number of calendar-week visits. Existing saved prescriptions remain unchanged.

Authored Phase 1 and Phase 2 remain separate bindings. A source block retains its
original source-week ordinal, sessions, exercise/set identities, dose, order,
relationships, effort targets and constraints; it is not renamed or regenerated
because Monday arrives. Expected frequency is an expectation, not a quota,
week-boundary cursor, exercise/set budget or guarantee about duration. Optional
calendar placement is a separate projection. Customized remains an explicit,
consent-bound choice for designing a different time-constrained prescription.

## Why the current date contract cannot implement this safely

| Current owner | Verified current behavior | Consequence |
| --- | --- | --- |
| `apps/web/app/onboarding/setup-draft.ts::setupPayload` | Stores a count without weekdays, but that count also maps split preference and feeds `days_available`. | Renaming it does not create a separate expectation or an undated training program. |
| `apps/web/app/onboarding/page.tsx::saveSetup` | Saves the profile, then sends Authored/Auto to Week; no workout is created by profile save. | Skipping the date page alone leaves no runnable workout. |
| `apps/api/app/selected_date_plans.py::current_scheduling_profile` / `selected_week_command` | Effective/current date count is calendar-derived; activation can overwrite `User.days_available`. | This field cannot be the new persistent expectation/cursor. |
| `apps/api/app/next_planned_workout.py::_review` | Every execution/consent snapshot is occupied, irrespective of completion; earliest dated unoccupied work wins. | Occupied is not completed; consent-only and undone work need a different selector. |
| `apps/api/app/selected_date_plans.py::selected_week_command` | Any execution/consent snapshot freezes the Authored week. | Removing this check would grant prescription/placement mutation beyond an explicit Start command. |
| `apps/api/app/selected_date_plans.py::resolve_source_successor` | An admitted adjacent saved source block can reserve its successor without any performed sets. | Saved reservations cannot serve as a completion cursor. |
| `apps/api/app/history_dates.py::performed_log_query` | `WorkoutOccurrence.scheduled_date` owns the linked legacy receipt's performed date. | Off-date execution would be misdated by a date-filter-only fix. |
| `apps/api/app/workout_identity.py::identified_sessions` | IDs incorporate the original plan, calendar week and slot. | Moving unfinished work into a new plan/week changes identity; carryover must retain the original occurrence. |
| `packages/core-engine/core_engine/history_status.py::calendar_statuses` | Computes coverage from effective working receipts, but expects their performed date to equal placement. | Useful existing evidence; not yet an accepted date-independent advancement lifecycle. |

These seams cross scheduling, source progression, execution identity, history,
load evidence, consent and migrations. The existing [date contract](selected-date-scheduling.md)
explicitly leaves continuation/carryover unresolved. This proposal follows the
owner's instruction to stop that implementation portion when a substantial new
contract is necessary. It does not replace the existing contract by implication.

## Proposed minimum data/state change

Use the existing User lock and immutable occurrence/receipt authorities; no
parallel workout logger, generic workflow engine or new runtime AI service.
Names below are concrete proposals, not implemented models or a migration file.

1. **`training_sequences` (new table).** Account-owned enrollment with ID, explicit
   `program_mode=authored`, `schedule_mode=flexible`, explicit consent, canonical program binding, admitted source/artifact/version
   digests, timezone, nullable expected sessions per week, policy version,
   revision and `active | attention_required | finished` state. Permit at most
   one active/attention-required sequence per account. Proposed expectation
   range: 1–7, optional and advisory; unlike the date planner's 2–5 visit bound,
   it cannot prune, regroup, skip, advance or change source work.
2. **Extend `workout_occurrences` additively.** Nullable sequence FK, source-block
   ordinal, source-session ordinal, immutable prescription digest, execution
   state and start/completion receipt timestamps. Enforce unique sequence/source
   position and account ownership. New Flexible rows must not fabricate calendar
   `plan_id`/`week_start`: those legacy anchors must become nullable only for an
   explicitly sequence-bound row. Existing rows and original anchors stay intact.
   Existing consent snapshots do not become started merely because they exist.
3. **`training_sequence_commands` (new table).** Unique `(user_id, command_id)`,
   operation, request digest, sequence, nullable occurrence, expected sequence
   revision, result and audit time for Enroll/Start/Resume/Finish. Enrollment has
   no occurrence until the transaction materializes the source block. Existing
   `WorkoutLogCommand` already retains set/history, correction, undo and
   substitution commands; retain its legacy scopes and add versioned execution
   context to new Flexible receipt handling. Exact retries return the original receipt; a changed
   payload under the same ID conflicts. Never infer idempotence from a browser flag.
4. **Extend `workout_set_logs` with actual-date authority.** Nullable explicit
   performed-local date, timezone and execution context/version. New Flexible
   working, warm-up and technique receipts capture actual local performance day
   server-side; correction retains the original receipt's performance day.
   `created_at` remains audit time. Legacy rows retain the current placement/
   timestamp fallback and its disclosed provenance; no invented historical date
   backfill. One occurrence may therefore contain work recorded on multiple days.

Occurrence IDs for new Flexible work derive from enrollment/source-block/source-
session identity, never calendar date. Exercise IDs keep the existing derivation
from occurrence and execution-slot index (preserving source-slot lineage
separately). Any explicitly adopted existing occurrence keeps
its original ID and prescription byte-for-byte. `WorkoutOccurrence.payload`
remains the prescription snapshot; the sequence must not store a competing dose.

The implementation must migrate the history, calendar, adherence and load-evidence
consumers together. A source block's completion date is not every set's performed
date. Existing completed-exposure/load logic keeps its evidence/variant semantics;
no new progression-load algorithm is authorized by this proposal.

## Profile/onboarding and compatibility changes required

A new validated Flexible intake/enrollment payload must accept the expectation
separately from the legacy required `ProfileUpsert.days_available`. Do not insert
a hidden date count or derive a split from the expected count merely to satisfy
that old DTO. `User.days_available` is already nullable in storage, but current
profile/setup response validation and setup-completion logic assume a count; they
must become explicitly mode-aware. Old date-based clients keep their existing
contract. New profile data exposes `schedule_mode`, `expected_sessions_per_week`
and a separately nullable selected-date count, with provenance, rather than
aliasing `effective_days_available`.

Flexible enrollment/intake must preserve the current account/initial-setup guard,
require explicit admitted program selection and timezone, and bind any new basic
profile/equipment answers to the reviewed enrollment. Questionnaire answers still
map through declared typed inputs; expected frequency is excluded from Authored
prescription construction. A saved expected frequency alone does not start a
program. The new source adapter requests the admitted original source-session
layout explicitly, rather than fabricating a five-day user preference to trick
the old generator. Equipment constraints and source-approved substitution consent
remain qualified existing authorities.

Every legacy generation/replacement/switch/date endpoint must reject or explicitly
hand off an active Flexible enrollment; it cannot create another source cursor. Enrollment must reject any unresolved/unknown/partial
legacy dated work or future reservations under the User lock; completed history
is retained and does not by itself forbid a new program. Do not auto-archive or
abandon work, reset an account, or run the old and new live planners concurrently.
Existing complete-history correction/undo remains available; if it reopens a
legacy predecessor while a Flexible sequence is active, enter the same attention
policy described below rather than pretending the legacy work disappeared.
Calendar weekly-review frequency edits cannot overwrite the new expectation or
regroup an active sequence. Initial-setup recovery must not treat an enrolled
Flexible account's null legacy day count as permission to overwrite its profile.
No old client gets implicit permission to modify a mode it does not understand.

The migration also affects the scoped reset/recovery inventory, which currently
recognizes exactly 23 tables. New tables/columns must make old reset manifests
fail closed; do not widen that allowlist without a separately reviewed ownership
inventory, disposable restoration/reset rehearsal and fresh operator authority.
No clean-start reset is authorized by this design or its implementation approval.

## Server decision contract

Owner: a small deterministic sequence decision module, with authenticated API
transactions as persistence owner. Inputs: explicit clock/timezone, enrollment
revision, stable ordered source positions, immutable prescription digests,
effective receipts and amendments, actual execution dates, source hard-rest
relations and existing consent/constraint state. No raw onboarding answers,
current browser date or independently maintained frontend cursor owns decisions.

- `GET /training/next`: read-only result with sequence/occurrence/source position,
  prescription, recorded coverage, `start | resume | finish | none | blocked`, original
  optional planned date, actual execution context, dependency digest, workload
  and precise blockers. Reads never instantiate an execution or advance source.
- `POST /training/enroll/preview`: a read-only deterministic source/profile
  adapter returns admitted original sessions, source/profile dependency digest,
  timezone, expectation and explicit eligibility/conflict reasons. It creates no
  enrollment, execution snapshot or reserved source position. Digest excludes
  future allocated IDs but binds every reviewed source/prescription/input field.
- `POST /training/enroll`: explicit confirmed preview/digest creates a new Flexible
  enrollment from admitted original source sessions. Rebuild/compare the preview
  under the User lock before persistence. An exact command retry returns the
  original enrollment; same ID/different payload conflicts; two competing new
  enrollments have one winner and no duplicate source items. Reject outstanding
  legacy work/reservations, unknown source coverage or another active enrollment.
  A frequency alone is not consent. Date-based scheduling remains a separate mode.
- `POST /training/{sequence_id}/start`: confirmed command binds expected revision,
  occurrence/prescription/dependency digests, expected local day and command ID.
  Recheck under User/sequence locks after waiting. Persist one start/actual-date
  receipt; do not move dates or regenerate any other saved session.
- `POST /training/{sequence_id}/resume`: uses the same frozen occurrence and a
  confirmed actual-day context. It does not create another workout or erase prior
  days. Recheck applicable hard rest/consent requirements before more work.
- `POST /training/{sequence_id}/finish`: require the proposed completion rule
  below, then record one completion and make the next source position eligible.
  No week regeneration and no completion from elapsed dates. The common command
  envelope binds ownership, operation/command ID, expected revision and reviewed
  occurrence/prescription/evidence digest for Finish as well as Start/Resume.
  The Finish acknowledgment time stays distinct from the last actual work date.

Proposed state transitions:

| State/evidence | Decision/result |
| --- | --- |
| No effective work/start receipt | Next required source session; confirmed Start only if current source/consent/rest checks admit it. |
| Explicit start, incomplete required work | Resume the same occurrence. A missed date or Monday does not change its state. |
| All required work recorded | Offer Finish; do not silently declare source advancement from an unrelated count or saved reservation. |
| Finish acknowledged with full coverage | Next original source session becomes eligible; advance source-block ordinal only after all its required sessions complete. |
| Stale/replayed command | Same command/same payload returns its receipt; otherwise conflict, without another start or advancement. |
| Unknown source identity/coverage or conflicting active work | Block with an explicit reconciliation reason. |
| Correction reopens completed work, no later work started | Retain the old Finish receipt, reopen coverage/state at the same identity and revision the sequence. Resume that item; block starting its successor until Finish passes again. Keep any reserved later items unchanged. |
| Correction reopens earlier work after later work started | Preserve every receipt and enter attention-required. Proposed conservative v1 blocks new Start/Resume/performance writes, including later active work, while reads and corrections remain available. No automatic rewind or fabricated coverage. |
| Source exhausted | Show finished/review; never silently repeat a block or switch Authored phases. |

**Existing writers must enforce the contract too.** Every new Flexible
working/warm-up/technique write, including direct calls to the existing workout
routes, must validate the active enrollment, exact started/resumed occurrence,
immutable prescription and confirmed current-local-day execution context under
the User/sequence lock. A saved snapshot or prior preview is not start authority.
Reject missing/stale/day-changed context, planned/finished occurrence writes and
attention-blocked performance before persistence. Exact retries look up and
return their original receipt/date without performing another write or relabeling
history as today. Corrections/undo retain their distinct history authority; they
must not be treated as a new performance or bypass the resulting sequence gate.

A separate optional date-plan projection can attach tentative visits to sequence
positions. It does not own source advancement and may not independently reserve
another copy of a successor. Missing dates cannot delete or skip anything. Two
clients cannot create the same source successor because source position is unique
and eligibility is rechecked under the same lock/revision.

## Proposed defaults needing approval

**Grouping is already owner-selected:** retain original source sessions for new
Flexible enrollments; expected frequency does not compress them. No approval is
inferred for converting existing regrouped plans.

The remaining proposed defaults are:

1. **Completion:** require an explicit Finish with all prescribed required working
   set keys covered by valid effective receipts. Warm-ups/technique children do
   not substitute for parent working sets. Unknown coverage blocks advancement.
   Partial work is paused/resumable; there is no v1 “skip remainder and advance”.
2. **Resume and rest:** allow one occurrence to span actual performance days.
   Evaluate explicit source rest against actual work, using the last relevant
   performed day for multi-day work; qualify cross-block relations. Missing
   required source-rest evidence blocks, rather than inventing permission. Do not
   add a generic universal recovery interval; advisory uncertainty stays visible.
3. **Undo after advancement:** corrections always preserve history. With no
   later start, reopen the same item and Resume/Finish it before another new
   start; keep later reservations and all old receipts. If later work has already
   started, the proposed conservative v1 enters attention-required and blocks
   **all new Start/Resume/performance writes**, including that later active work.
   Reads/corrections remain available; there is no automatic rewind, duplicate
   occurrence, deletion or partial-dose acceptance. This deliberately has no
   automatic escape if the original required work is genuinely missing. The
   owner must explicitly accept this v1 stop or approve an alternative audited
   continuation/reconciliation rule before implementation. Do not promise a
   self-service recovery path until its exact policy is approved and tested.
4. **Cross-enrollment reopening remains approval-blocking:** a completed
   Flexible sequence A may have been followed by enrollment B. Corrections to A
   must remain available, but reopening A into `attention_required` alongside an
   active B would violate the single-current-sequence constraint. This proposal
   does **not** authorize that transition. Before implementation, approve either
   an account-level reconciliation gate that blocks B while A retains its
   historical identity/finish receipts, or an explicit transactional transfer of
   current ownership with rules for B's started work. Neither option may discard
   receipts, create a second live source cursor or silently reinstate old work.
   The exact schema, resolution authority and recovery transition for this case
   remain unresolved; the new lifecycle cannot ship with this case undefined.
5. **Existing plans and reservations:** first implementation enrolls new Flexible
   programs only, for accounts without outstanding legacy work/reservations.
   Completed legacy history is retained; unresolved work blocks enrollment, not
   silently abandoned. Existing date-based plans remain on their current mode;
   there is no automatic conversion, destructive replacement or reset requirement. Adoption of
   partially started or prebooked future plans needs a reviewed manifest mapping
   every original occurrence/source position, retained grouping, consent and date
   provenance. Duplicate ordinals/conflicting future work block adoption.

Approval should explicitly accept or amend these defaults and the cross-enrollment decision, including whether
v1 may exclude existing-plan adoption. It must also confirm the proposed advisory
frequency range. An implementation approval is separate from merge/migration/
production deployment approval. These defaults have not been accepted yet.

## Workload and UI behavior after approval

Onboarding offers Flexible expected frequency with optional dates, or the existing
explicit date-based mode. It must not change split/program merely because the
expectation changed. Home/Today consume the server's action and receipt, with
Start Next Workout or Resume under the existing pending-undo/account guards.
Confirmation identifies source workout, actual local day and unchanged dose.

Preserved old three-visit allocations can still contain 10–11 exercises and
29–30 working sets. Even native sessions need factual workload warnings: neither
shape proves a 45/60-minute goal is met. Never silently trim or switch modes.
Customized is the explicit alternative for a genuinely different prescription.

## Required implementation evidence, still pending

Isolated PostgreSQL migration/backward-compatibility and ownership probes; new-
account enrollment without weekdays; actual-day/source rest and consent negatives;
missed-day and multi-Monday rollover with no loss/advance; completed-earlier-session
start; duplicate starts/finishes and move/log/undo races; stale local day/digest;
partial coverage, typed/nonnumeric prescription and correction negatives; immutable
old history and per-day receipt provenance; source exhaustion; optional-calendar
coexistence; account/pending-recovery browser cases; mobile/desktop UI and actual
physical-iPhone acceptance. Normal final-head CI is required after implementation.

The current PR supplies **legacy boundary characterizations and a reviewable
proposal**, not an implemented Flexible program or proof that these future gates
pass. No application API, schema, onboarding flow or scheduling behavior is changed.
