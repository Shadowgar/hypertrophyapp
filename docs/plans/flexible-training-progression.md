# Flexible training progression — contract gate and bounded implementation plan

Status: **Investigation/proposal prepared; runtime implementation blocked pending
owner contract approval**, 2026-10-30. Base protected main:
`dca2dc3ebebfbde26cae0333c9db0d050ca44dff`. Related to
[#105](https://github.com/Shadowgar/hypertrophyapp/issues/105); #103/#105 stay open.

## Scope and authority

Owner authorizes a completion-driven Flexible first version and one focused PR,
but explicitly requires stopping the cross-week/source progression portion if it
needs a substantial new contract. That condition is met: placement owns legacy
performed dates, source advancement owns adjacent calendar reservations and there
is no explicit session Start/Finish state. Merely removing a date filter/week
freeze would misdate or reinterpret history. No independently honest onboarding-
only or button-only change delivers the requested execution behavior.

The owner separately selected original source workouts for new Flexible programs,
allowing a source block to span more than seven calendar days. The detailed
[proposed contract](../contracts/flexible-training-sequence-proposal.md) names the
API, two new tables, additive occurrence/log changes, state transitions and
remaining approval decisions. Existing contracts/ADR statuses remain unchanged.

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
- [ ] Obtain final-head normal PR qualification.
- [ ] Owner accepts/amends completion, multi-day rest/dating, correction after
  advancement, cross-enrollment reopening, legacy enrollment scope and advisory
  frequency range.

No migration file or runnable new Start/Resume API is implemented by this PR.
No merge, deployment, production container build, reset or release-control change.

## Minimum coherent vertical slice after contract approval

Implement in this same focused PR only after approved decisions are recorded.

1. Add the reviewed additive migration/models with explicit disposable PostgreSQL
   target checks and old-schema/old-history compatibility qualification. Do not
   infer legacy actual dates or active enrollments from calendar rows.
2. Implement the deterministic next decision, enrollment/source adapter and
   idempotent Start/Resume/Finish commands under User/sequence locks. Expected
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

Acceptance matrix and precise unresolved decisions are in the proposed contract.
A design approval does not authorize production DDL, data adoption, deployment,
merging or release automation.
