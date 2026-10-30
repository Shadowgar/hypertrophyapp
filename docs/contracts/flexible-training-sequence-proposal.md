# Completion-driven Flexible training contract

Status: **Owner-approved for bounded implementation in draft PR #133, with the
amendments below, 2026-10-30.** Reviewed proposal:
`31bc5315c58832adf209b84424becef1384ce4fe`; protected base:
`dca2dc3ebebfbde26cae0333c9db0d050ca44dff`. Related: [#105](https://github.com/Shadowgar/hypertrophyapp/issues/105),
[implementation plan](../plans/flexible-training-progression.md).
Approval does not authorize merge, deployment, production DDL/data operations or
release automation. #103/#105 remain open. Implementation and qualification are
recorded separately from this contract.

## Governing owner decisions

Retain original Authored source workouts, exercises, sets, source identities,
order and prescriptions. Phase 1 and Phase 2 remain distinct. A source block may
span calendar weeks; Monday never skips, duplicates, deletes or completes work.
Expected frequency is optional, integer 1–7 weekly, advisory only. It cannot
allocate dose, select a split, change a program or advance the source cursor.
Dates are optional. Existing date-based scheduling retains its separate contract.
Customized remains an explicit consent-bound route to a different prescription.
No count-based estimate claims 29–30 sets fit a 45/60-minute goal.

A full **Finish** requires valid effective coverage of every required working-set
key. Warm-up/technique children do not substitute for working sets. **End Early**
is separate and explicitly confirmed: retain the prescription, exact missing
work and optional reason, label the session incomplete and permit source
progression. No silent closure/skip or fabricated full completion.

**Pause/Resume** may span actual local days with one immutable occurrence. Each
set retains its server-bound actual local performance date/timezone/context;
receipt audit time and amendment time remain distinct. Hard source rest uses
relevant actual evidence, including the latest relevant day of multi-day work
and cross-block dependencies. Unknown mandatory evidence blocks affected work;
advisory uncertainty is never a guarantee of safe recovery.

Corrections retain audit history, effective coverage and the original **as-of
advancement** receipt. They never rewind or invalidate already started successor
workouts. A historical Finish whose required coverage later changes is shown as
amended/incomplete while its original advancement decision remains auditable.
Ordinary coverage amendments, including those in sequence A after B starts, do
not globally freeze training. B remains the sole current sequence; A cannot be
reactivated by an amendment.

## Current owners and root causes

- `history_dates.performed_log_query` historically projects performed dates from
  frozen placement. New explicit receipt dates must take precedence, retaining
  the legacy fallback and its provenance without fictional backfill.
- `selected_date_plans.resolve_source_successor` reserves an adjacent calendar
  source week without requiring completed work. It cannot own Flexible advance.
- `next_planned_workout._review` treats consent snapshots as occupied. A snapshot
  alone is neither Start nor Finish.
- `workout_identity.identified_sessions` keys legacy IDs by plan/week/slot.
  Flexible identity must use enrollment/global source position, never a new date.
- `calendar_statuses` and Authored load consumers assume placement/first receipt
  dating. Multi-day effective coverage and actual chronology require explicit
  integration, separate from per-day activity/window filtering.

## Minimum persistence and authority

Reuse existing User locking, occurrence snapshots, `WorkoutSetLog`, retained
`WorkoutLogCommand` replay and amendment/reconstruction authorities. No parallel
logger, artificial calendar cursor, generic event-store rewrite or runtime LLM.

1. `training_sequences`: account-owned enrollment, explicit source/program
   binding and artifact digest, timezone, optional expected frequency, revision,
   current source position, state and reconciliation evidence. At most one
   current sequence per account. Historical finished/retired enrollments retain
   their identity. Freeze native source items when enrolling; do not regenerate
   their prescriptions on a date, profile, source-import or frequency change.
2. Extend `workout_occurrences` with sequence/global source position, immutable
   prescription digest, explicit execution lifecycle and context. Allow null
   legacy plan/week anchors only for sequence-bound rows. Keep old IDs/anchors
   intact. Prescription payload remains the single dose authority. Distinguish
   planned, active, paused, finished and ended-early states; effective completeness
   and historical advancement are separate facts.
3. `training_sequence_commands`: account/command uniqueness, operation/request
   digest, sequence/occurrence references, immutable result and audit timestamp.
   Enroll/Switch/Start/Pause/Resume/Finish/End Early/reconciliation are idempotent;
   same key/different payload conflicts. Exact retry returns the original result.
4. Extend set receipts with explicit actual local date/timezone/execution context.
   Corrections copy the original date. Old rows preserve legacy date semantics;
   neither migration nor a new UI fabricates historical performance.
5. Retain superseded unstarted dated plans with their original payload and an
   explicit supersession reference. All planner/selection consumers exclude such
   reservations from active ownership while retaining them as historical evidence.

Any new ownership tables make the existing 23-table reset manifest fail closed.
No widening of destructive reset scope or production reset is authorized here.
Migration compatibility and concurrency require an isolated PostgreSQL rehearsal.

## Enrollment, source admission and guarded conversion

A read-only enrollment preview binds source/program digest, native source layout,
profile/equipment/constraints, timezone, advisory frequency, legacy reservations
and account revision. Confirmation revalidates under the User lock and records
explicit consent. New intake accepts expected frequency independently of legacy
`days_available`; it never fabricates a five-day profile to invoke an allocator.
Native source sessions come from the admitted loader, with typed dose, source
lineage, relationships and variants preserved; all positions use global ordinals
because block-local source week/day IDs may repeat.

**Switch to Flexible** is an explicit, separately confirmed conversion for one
entirely unstarted, conflict-free Authored dated reservation. Validate the exact
source identity/version and all source slots/dose against the admitted source.
Reject ambiguous future/duplicate reservations, consent/calibration/execution
snapshots, log commands, session state and any recorded activity. Retain the
redistributed old payload as superseded history; new source-native occurrence
identity is linked through the conversion receipt, never mislabeled as the old
grouping. Existing completed history is preserved. Partially started legacy
adoption is excluded from v1; a new account/reset is not required.

All generation, replacement, program-switch and calendar activation paths must
recheck Flexible ownership under the shared User lock. Old clients cannot create
a competing cursor or regenerate snapshots through a profile/date façade.

## Server commands and decision output

`GET /training/next` is read-only and owns the Home/Today action, source position,
prescription/workload, current effective coverage, as-of advancement, execution
context, optional planned date, revision/digests and precise blockers/resolutions.
Reads do not create source items or advance them. Server action is Start, Resume,
continue active work, Finish, source exhausted or blocked.

`POST /training/enroll/preview` and `POST /training/enroll` provide deterministic
review/confirmation, including explicit Switch to Flexible intent when applicable.
Sequence commands bind authenticated ownership, command ID, expected revision,
occurrence/prescription/evidence digest and the reviewed local day. Revalidate
under the User lock after waiting; simultaneous commands have one serial outcome.

- Start: explicitly confirm the next outstanding native source occurrence.
- Pause: retain active identity/receipts and invalidate new-performance context.
- Resume: confirm a current local-day context on the same frozen occurrence.
- Finish: atomically record full effective required-working coverage and advance.
- End Early: explicitly confirm exact missing work and optional reason; persist
  incomplete closure/advancement without altering source dose or claiming Finish.
- Replay: return the retained receipt before current-day/phase guards; a late
  retry must not relabel a set, resurrect undone work or advance twice.

Every direct working/warm-up/technique writer must validate started/resumed exact
occurrence and current-day context after idempotent replay, before persistence.
A snapshot or preview is not Start authority. Finished/paused/stale contexts reject
new performance. Corrections and undo retain their separate historical authority.
Actual-date history and completed-exposure load evidence must consume effective
receipts across the entire occurrence, not just one calendar query window.

## Account reconciliation and finite resolution

Mandatory dependencies are evaluated using current effective facts, while all
as-of advancement receipts remain immutable. Ordinary historical coverage loss
changes the history label and future load evidence, not the current source cursor.
Only an actual hard source-rest, ownership, source-admission or consent conflict
may gate affected current work; an unrelated amendment cannot globally block B.

The server returns typed conflicts, affected operations, evidence digest and
finite resolution choices. A version-bound reconciliation command re-evaluates
under the User lock and records its outcome:

- Known hard-rest interval: show the earliest eligible day; after it elapses,
  explicit recheck releases the affected gate without changing the rule.
- Correctable erroneous evidence or stale consent: use the existing audited
  correction/consent authority, then recheck the dependency. No synthetic sets,
  invented dates or ignore-rest checkbox may resolve missing evidence.
- Unadmitted/irreconcilable source or ownership: expose a terminal **retire this
  program** option with confirmation. Preserve every item, prescription, receipt
  and incomplete status; retire current ownership and record the exact blocker.
  This is not successful completion or permission to bypass the same mandatory
  dependency in a later enrollment. Invalid source remains inadmissible.

The historical sequence is never made current alongside B. All resolution paths,
including terminal retirement, must be tested before enablement. If a mandatory
invariant cannot be implemented/qualified, stop that specific path and report its
exact blocker; do not expose a permanently retryable no-recovery training lock.

A routine incoming known-rest wait can expose Start after the interval elapses:
the confirmed Start command itself performs the locked eligibility recheck. An
amendment-created attention state persists until explicit reconciliation. Neither
clock passage nor a GET starts or advances a workout.

Current v1 conversion is restricted to source block 1. Later-block conversion
requires an audited completed-source mapping and reliable mandatory actual-date
evidence; it is rejected rather than restarting or fabricating prior source work.
Calendar weekly-review/adaptation is also unavailable for Flexible sequences:
its calendar-week dose denominator does not describe a source block spanning
weeks. Optional check-ins and actual-date History retain their existing scope.

## Required qualification and acceptance

Focused tests cover native source identity/dose, optional frequency/no weekdays,
Finish versus End Early coverage, Pause/Resume/midnight, missed dates/multiple
Mondays, completed earlier work, source exhaustion, stale digests and duplicate
commands, same-account races, cross-account rejection, history amendments,
cross-enrollment reconciliation, actual-date/load evidence and unstarted-only
conversion. Source constraints include synthetic cross-block hard-rest endpoints,
unknown mandatory relationships/evidence and finite reconciliation paths.

The current admitted artifact schema does not declare `minimum_rest` relationships;
absence is not proof that every source recovery instruction has been captured.
Admission must validate declared relationships globally and disclose that limit.
No claim of scientifically established recovery safety is authorized.

Isolated PostgreSQL upgrade/backward compatibility and races, local desktop/mobile
Playwright, security review and normal required CI at the final review head remain
necessary. Actual physical-iPhone/gym acceptance is owner work under #103/#105.
