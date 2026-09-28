# Selected-date scheduling contract

Status: **Owner-approved actual-date direction; allocator/exception policy Proposed**. Owner: deterministic scheduler and API date/revision validation. M2B runs alongside M2A after relevant identity/fidelity foundations. [ADR-007](../adr/0007-selected-date-scheduling.md).

## Initial scope and inputs

Initial scope is manual selection of actual training dates during the current local week, without Google/Apple/external calendar integration. Input: explicit planning instant, valid IANA timezone, local week start, distinct selected local calendar dates, mode/consent, versioned prescriptions/relationship groups, previous/next-week effective or planned context, duration/constraints, occurrence status and expected revision. Do not read server `date.today()` inside the decision owner.

Proposed local-week convention is Monday–Sunday in the selected timezone, matching existing week-start concepts; this convention is not a new scientific rule. Validate timezone/week membership/count, duplicate dates and invalid local-date values before allocation. Time-of-day selection is not required initially. Date-only input remains date-only; do not manufacture an exact UTC workout time. A past/started-date policy needs explicit product approval.

Output: selected-date placements, stable occurrence/placement revision identities, ordered source units/relationships, duration range, spacing/conflict results, infeasibility or feasible plan and deterministic trace.

## Allocation and relationships

Authored allocation is lossless: all required slots/sets and meaningful order/pairs/primers survive. Treat inseparable relationships as units; do not deduplicate distinct occurrences sharing an exercise ID. Selected dates equal output dates. Overlong sessions are shown with uncertainty and workload, never shortened by unapproved pruning. Source mandatory rest/sequence constraints are hard where explicit; inferred recovery spacing is labeled policy/advisory with a version, not source authority.

Evaluate actual calendar gaps and muscle/relationship context across week boundaries using available evidence. Missing neighbor context is unknown and disclosed; it is not a guaranteed safe-spacing result. Customized may use dates as hard feasibility inputs and optimize only under its separate consent. A conflict never unlocks generic authored volume changes.

Proposed deterministic ordering: preserve source precedence; enumerate feasible allocations in selected-date order; compare a versioned declared objective; break equal scores using stable source-slot/occurrence IDs. Numerical weights/spacing thresholds need explicit policy review. Same input/version/context returns same placement and trace; dictionary iteration or current clock cannot decide ties.

## Rescheduling and failure

Unstarted reschedule preserves occurrence identity and source dose with a new placement revision, re-evaluating neighbors and expected revision. Starting freezes the prescription; do not regenerate started/completed work or rewrite performed dates. Proposed default is no automatic movement/regeneration of started work; explicit continuation/carryover or replacement policy remains unresolved. Cancelling/partial closure is visible, not a silent source deletion or full completion.

Invalid dates return validation error without persistence. No relationship-preserving allocation returns explicit infeasibility with affected units/dates and alternatives requiring user action. Insufficient neighbor evidence returns a qualified limitation. Stale revision conflicts without overwriting a newer placement.

Acceptance: Tue/Fri/Sun placements exactly match inputs; duplicates/out-of-week dates fail; DST changes do not shift local dates; previous Sunday/next Monday appear in spacing context; two identical exercises remain separate slots; paired/primer work stays together/ordered; compressed dose remains unchanged; no feasible schedule reports a reason rather than trimming. Trace includes local week/timezone/date input, source/rule hashes, context completeness, candidates/objective/tie-break and conflicts. Browser qualification demonstrates selection, preview, reschedule and overlong-session warnings.
