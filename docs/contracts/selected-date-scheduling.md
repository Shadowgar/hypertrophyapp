# Selected-date scheduling contract

Status: **Owner-approved actual-date direction; allocator/exception policy Proposed**. Owner: deterministic scheduler and API date/revision validation. M2B runs alongside M2A after relevant identity/fidelity foundations. [ADR-007](../adr/0007-selected-date-scheduling.md).

## Initial scope and inputs

Initial scope is manual selection of actual training dates during the current local week, without Google/Apple/external calendar integration. Input: explicit planning instant, valid IANA timezone, local week start, distinct selected local calendar dates, mode/consent, versioned prescriptions/relationship groups, previous/next-week effective or planned context, duration/constraints, occurrence status and expected revision. Do not read server `date.today()` inside the decision owner.

The owner-authorized [M2B-2 package](../plans/m2b-next-week-scheduling.md), requested on 2026-10-15, extends placement to the current or next local Monday–Sunday week. Each week retains its own saved plan and placement revision. A new next-week Authored plan requires a unique dated predecessor in the same timezone, matching admitted source lineage and an available successor source week; missing, conflicting, exhausted or inconsistent progression requires explicit reconciliation. Preview reserves nothing. Activation binds the reviewed prescription, predecessor, adjacent schedules and the persisted evidence inputs used for generation. Subsequent current-week activity does not rewrite an activated next-week plan. Today continues to use the actual current local date. This bounded implementation authorization does not accept ADR-007 or authorize deployment.

Next-week activation requires the preview content digest, including for direct API clients. Current-week activation compatibility remains unchanged. On local Monday, profile presentation, training-state/recommendation inputs and frequency-adaptation/coach previews derive the effective current date count and program binding from the uniquely active dated plan. Profile's `effective_days_available` and `effective_program_id` are read-only fields, separate from stored writable preferences. Explicit Auto retains a null preference; it cannot be silently saved as Phase 1 by a profile round-trip. Reads do not synchronize or overwrite preferences or plans; weeks without a dated plan retain stored availability/binding.

Proposed local-week convention is Monday–Sunday in the selected timezone, matching existing week-start concepts; this convention is not a new scientific rule. Validate timezone/week membership/count, duplicate dates and invalid local-date values before allocation. Time-of-day selection is not required initially. Date-only input remains date-only; do not manufacture an exact UTC workout time. A past/started-date policy needs explicit product approval.

Output: selected-date placements, stable occurrence/placement revision identities, ordered source units/relationships, duration range, spacing/conflict results, infeasibility or feasible plan and deterministic trace.

Current intelligence uses that same current plan and excludes later reservations from its prior-plan count. Once dated scheduling is enabled, legacy generation endpoints cannot advance or replace reservations; Check-in directs the user to Week after saving the review. Converting an existing legacy future row requires its ordinal and source lineage to match the established successor. A later live reservation blocks new source generation for an earlier week pending reconciliation, including when it appears between preview and activation.

## Allocation and relationships

Authored allocation is lossless: all required slots/sets and meaningful order/pairs/primers survive. Treat inseparable relationships as units; do not deduplicate distinct occurrences sharing an exercise ID. Selected dates equal output dates. Overlong sessions are shown with uncertainty and workload, never shortened by unapproved pruning. Source mandatory rest/sequence constraints are hard where explicit; inferred recovery spacing is labeled policy/advisory with a version, not source authority.

Evaluate actual calendar gaps and muscle/relationship context across week boundaries using available evidence. Missing neighbor context is unknown and disclosed; it is not a guaranteed safe-spacing result. Customized may use dates as hard feasibility inputs and optimize only under its separate consent. A conflict never unlocks generic authored volume changes.

Proposed deterministic ordering: preserve source precedence; enumerate feasible allocations in selected-date order; compare a versioned declared objective; break equal scores using stable source-slot/occurrence IDs. Numerical weights/spacing thresholds need explicit policy review. Same input/version/context returns same placement and trace; dictionary iteration or current clock cannot decide ties.

## Rescheduling and failure

Unstarted reschedule preserves occurrence identity and source dose with a new placement revision, re-evaluating neighbors and expected revision. Starting freezes the prescription; do not regenerate started/completed work or rewrite performed dates. Proposed default is no automatic movement/regeneration of started work; explicit continuation/carryover or replacement policy remains unresolved. Cancelling/partial closure is visible, not a silent source deletion or full completion.

Invalid dates return validation error without persistence. No relationship-preserving allocation returns explicit infeasibility with affected units/dates and alternatives requiring user action. Insufficient neighbor evidence returns a qualified limitation. Stale revision conflicts without overwriting a newer placement.

Acceptance: Tue/Fri/Sun placements exactly match inputs; duplicates/out-of-week dates fail; DST changes do not shift local dates; previous Sunday/next Monday appear in spacing context; two identical exercises remain separate slots; paired/primer work stays together/ordered; compressed dose remains unchanged; no feasible schedule reports a reason rather than trimming. Trace includes local week/timezone/date input, source/rule hashes, context completeness, candidates/objective/tie-break and conflicts. Browser qualification demonstrates selection, preview, reschedule and overlong-session warnings.

### Customized active placement extension, 2026-10-20

The existing `/customized` lifecycle uses this same local-week validator and lossless placer for explicitly confirmed date-only amendments. It retains stable plan/slot identities and advances placement revision atomically. A mixed started/unstarted Customized week can retain frozen slots while moving only other slots; retained placement history and unchanged date/prescription qualify older frozen snapshot revisions. Authored still uses its existing week-freeze behavior and permitted occurrence receipt overlays. Same-week replacement is a separate explicit Customized consent operation, never permission granted by this scheduling endpoint. [Scope and evidence](../evidence/2026-10-20-m4-active-lifecycle.md).

### Confirmed next-session option and workload correction, 2026-10-30

The owner-authorized [flexible Today package](../plans/flexible-today-workload.md)
adds a read-only next-unstarted dated-session preview. A separate confirmed command
binds the reviewed account-owned plan, occurrence, original date, current local
date, placement revision and prescription/dependency digest. It delegates to the
existing Authored selected-date command under the same User lock. Only same-week,
source-order-preserving moves admitted by its entirely-unstarted-week rules are
allowed. Execution/consent snapshots still freeze that week. An existing workout
today, changed preview/date, cross-week work, source minimum-rest conflict or
Customized consent boundary blocks the move without changing history. Missing
outstanding work returns no candidate; it never implies completion.

For newly reviewed selected-date allocations, the declared advisory objective is
`selected-date-workload-first-v2`: minimize working-set range, then squared
working-set target deviation, then consecutive-day declared-muscle overlap, then
source cuts. Hard source relationships and minimum rest remain mandatory. This
corrects overlap-first allocations that could push most of a week into one visit;
there is no automatic rewrite of an existing placement. Counts and a saved time
goal are disclosed without a claimed duration estimate. An entirely unstarted
week can be explicitly previewed across more of its existing 2–5 selected visits.
Splitting a started occurrence, using more than five visits, or carrying work to
another source/calendar week requires a separate qualified contract; this package
does not silently enable any of them. See the [allocation audit](../evidence/flexible-training-workload-2026-10-30.md).
