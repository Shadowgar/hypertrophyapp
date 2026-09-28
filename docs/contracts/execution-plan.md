# Execution-plan contract

Status: **Owner-approved authority direction; proposed identity/application mechanisms**. Owners: deterministic execution/scheduling decisions; API transactions; faithful web runner. Related [ADR-002](../adr/0002-mode-authority-and-consent.md), [ADR-005](../adr/0005-training-history-identity-and-correction.md) and [domain](../architecture/domain-model.md).

## Inputs and outputs

Input: explicit mode/consent, immutable program/prescription version, normalized profile/constraints, selected dates/timezone, source relationship groups, effective history and expected revision. Output: plan revision, dated workout/exercise occurrences, typed set prescriptions, load recommendations, unresolved/conflict outcomes and decision trace. Existing manual/auto selection is not consent.

Authored output preserves every required source slot exactly once per intended execution, including nonnumeric and set-specific targets. Redistribution changes placement/grouping while retaining dose and relationships; repeated exercise IDs do not collapse. Customized may redesign only under explicit constraints/consent and never mutate authored artifacts. Unsupported hard constraints yield visible infeasibility, not disguised source fallback.

## Substitution and load behavior

When equipment, safety, pain or another constraint prevents an authored exercise, identify the affected slot and reason. Offer an evidenced source-approved alternative when present; require explicit confirmation before changing performed exercise. Store original slot/prescription, confirmed variant, source permission, user decision and time. Decline/missing permission leaves an unresolved slot; it does not delete source work or unlock unrelated exercise/set/rep/RPE/volume changes. No silent substitute on regeneration, repeat failure or equipment change.

Qualified load coaching may calculate/prefill next or current comparable working load and expose increase/hold/decrease/monitor, evidence and override. It cannot alter authored exercise, sets, rep range, effort target, technique or progression/block structure. Unknown effort remains unknown. A safety stop is a scoped unresolved/paused outcome, not automatic redesign.

## History, revisions and failure

Starting binds the execution prescription snapshot. Completed data remains linked to that snapshot and performed variant even when plans/source versions later change. A new plan revision explicitly retains, moves, cancels or replaces unstarted occurrences. No read route silently overwrites started/completed work. Changes recheck ownership, mode and expected revision; stale commands return conflict without mutation.

Log commands have stable user/occurrence/logical-set identity and retry digest; same retry returns the original result, differing payload conflicts. Concurrent valid records survive; records/projections change atomically or under a qualified reconstructible protocol. Correction/undo retains an audit trail and rebuilds all affected guidance/progression, not just session counts. Legacy ambiguous identity is explicitly unresolved.

Acceptance examples: a compressed authored week retains every slot/set and pair/primer; missing equipment waits for confirmed source-approved substitution; same exercise twice yields two occurrences; an automatic load-prefill override retains both recommendation and actual load; regeneration after a completed workout preserves its prescription/logs. Tue/Fri/Sun placements equal chosen dates. Interrupted or closed-partial work is not labeled fully completed. Detailed [date](selected-date-scheduling.md), [load](load-progression.md) and [recommendation](recommendations.md) contracts own their semantics; exact persistence and started-work exception policy remain Proposed.
