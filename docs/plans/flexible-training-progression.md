# Flexible training progression — bounded implementation plan

Status: **Owner approved implementation with amendments**, 2026-10-30. Base protected main:
`dca2dc3ebebfbde26cae0333c9db0d050ca44dff`. Related to
[#105](https://github.com/Shadowgar/hypertrophyapp/issues/105); #103/#105 stay open.

## Approval and implementation scope

On 2026-10-30 the owner approved implementation in PR #133 at reviewed proposal
31bc5315c58832adf209b84424becef1384ce4fe, with End Early, multi-day execution,
non-rewinding historical amendments, finite account-level reconciliation and
explicit unstarted-only Switch to Flexible. Those decisions supersede the
proposal's full-coverage-only advancement and conservative global-stop defaults.

## Original investigation and authority

The original task authorized a completion-driven Flexible first version and one focused PR,
but explicitly requires stopping the cross-week/source progression portion if it
needed a substantial new contract. That condition was met: placement owns legacy
performed dates, source advancement owns adjacent calendar reservations and there
is no explicit session Start/Finish state. Merely removing a date filter/week
freeze would misdate or reinterpret history. No independently honest onboarding-
only or button-only change delivers the requested execution behavior.

The owner separately selected original source workouts for new Flexible programs,
allowing a source block to span more than seven calendar days. The detailed
[approved contract](../contracts/flexible-training-sequence-proposal.md) names the
API, two new tables, additive occurrence/log changes, state transitions and
owner's amended decisions. Existing unrelated contracts/ADR statuses remain unchanged.

## Completed investigation slice

- [x] Verify exact protected base and isolate the worktree; no production records.
- [x] Trace onboarding/count, calendar/source successor, identity, performed date,
  working-set coverage and consent/snapshot authorities.
- [x] Record the explicit grouping choice without treating other policies as accepted.
- [x] Add focused disposable-target boundary characterizations for missed dates,
  completed earlier work, Monday rollover, consent-only snapshots, history dating
  and saved-successor versus completion. These verify existing legacy behavior;
  they are not future Flexible acceptance tests.
- [x] Obtain independent proposal review; record cross-enrollment reopening as
  an additional approval-blocking decision.
- [x] Proposal head qualified: CI 41080018960, CodeQL 41080013259, GitGuardian passed.
- [ ] Qualify the final implementation review head.
- [x] Owner approved/amended lifecycle, reconciliation, conversion and optional
  advisory frequency 1–7; controlling contract updated before runtime work.

The proposal head had no runtime implementation. Implementation evidence follows
the approved contract and is recorded as each bounded task is qualified.
No merge, deployment, production container build, reset or release-control change.

## Implementation tasks

Implement in this same draft PR under the amended approved contract.

1. Add the reviewed additive migration/models with explicit disposable PostgreSQL
   target checks and old-schema/old-history compatibility qualification. Do not
   infer legacy actual dates or active enrollments from calendar rows.
2. Implement the deterministic next decision, enrollment/source adapter and
   idempotent Start/Pause/Resume/Finish/End Early/reconciliation commands under User/sequence locks. Expected
   frequency cannot affect source grouping or advance a block. No second logger.
3. Update actual-date receipt/history/load consumers together. Preserve old
   identities/snapshots, typed doses and legacy provenance; qualify correction and
   source-rest boundaries before enabling off-date execution.
4. Connect onboarding and Home/Today to the accepted server contract, retaining
   explicit dates mode, pending recovery/account guards, confirmations, workload
   warnings and Customized consent. Do not advertise unavailable actions.
5. Focused progression/date/race/history tests during development, isolated real
   API/browser qualification and one normal full qualification at final PR head.
   Real iPhone/gym acceptance stays open under #103/#105.

Acceptance matrix and bounded implementation limitations are in the approved contract.
A design approval does not authorize production DDL, data adoption, deployment,
merging or release automation.

## Implemented scope and qualification boundary

The implementation uses `flexible_training.py` as the deterministic lifecycle
owner and the existing logger/User lock for all performance writes. Migration
0027 adds sequence/command ownership and optional actual-date receipt fields;
it does not adopt, rewrite or backfill legacy plans or performance. Native source
sessions are frozen once at enrollment. Full Finish and explicit incomplete End
Early have separate immutable advancement receipts. Corrections project current
coverage without rewinding historical advancement or successor identity.

Focused isolated tests cover native admission, conversion, completion, actual
dates, history/load consumers, stale/idempotent commands and reconciliation.
An isolated PostgreSQL 16 rehearsal preserved all original columns/rows in the
22 populated application tables, advanced only Alembic schema state, and checked
ownership/current-sequence constraints. Real PostgreSQL User-lock races cover
enrollment, duplicate starts and both End Early/performance orderings. Browser,
security and final-head CI results are recorded on draft PR #133; no historical
proposal check is implementation qualification.

V1 limitations remain explicit:

- Switch to Flexible supports one entirely unstarted Authored reservation of
  source block 1. A later source block needs an audited mapping from completed
  legacy source work and reliable actual-date evidence before conversion can be
  admitted. Partially started, consent-bearing or ambiguous reservations reject.
- Dates remain optional through distinct Flexible and existing Calendar modes.
  Flexible v1 does not add tentative-date reservations within the sequence.
- Current admitted source artifacts declare no mandatory minimum-rest edges.
  The evaluator qualifies declared edges, unknown evidence and cross-block rest
  with synthetic boundary fixtures; it does not claim complete recovery coverage
  or medically qualified safety from absent metadata.
- Calendar-based weekly review/adaptation and coaching program replacement are
  unavailable for Flexible sequences. Their planned-week denominator and dose
  allocation require a separate sequence-aware contract. Optional check-ins and
  actual-date History remain available; no calendar frequency is fabricated.
- Saved duration is a goal, not an accurate estimate. Native Authored dose stays
  unchanged; Pause/Resume can spread one workout across visits. Customized is
  the explicit route to a different prescription.
- Physical iPhone/gym and production migration/release acceptance remain pending
  under open Issues #103/#105.
