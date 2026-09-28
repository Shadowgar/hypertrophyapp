# Recommendation and override contract

Status: **Owner-approved explanation/override direction; proposed typed lifecycle**. Owner: deterministic recommendation facts and application permission checks. [ADR-008](../adr/0008-recommendation-evidence-and-overrides.md). AI may help explain/analyze; it cannot determine or apply runtime prescriptions.

## Inputs and outputs

Input: qualified effective evidence IDs, immutable prescription/plan revision, mode/consent and allowed action scope, rule/version, explicit context and user outcome history. Output: stable recommendation ID/version, action/target/value, evidence references and comparability/sufficiency, uncertainty/limitations, reason codes/explanation facts, mutation permissions, lifecycle/status and later review linkage.

Evidence can include source instructions, effective set/exposure records, dated readiness and equipment/profile versions. A correction does not erase original evidence; it invalidates/recomputes dependent current advice and marks stale recommendations. Missing evidence produces monitor/no-change/insufficient-data rather than invented confidence.

## Permission and lifecycle

Creation/preview is not application. Authored load calculation may prefill automatically with an explicit origin; this is not fabricated explicit acceptance. The user can accept, decline or modify the recommendation; record chosen value, reason code/note and timestamp. Source-approved substitution requires explicit confirmation before performed-variant change; program design requires Customized consent and a revision preview. Manual/auto selection grants neither.

Advice applies only to its declared mode/scope/evidence/expected revision; application rechecks ownership and freshness. Authored effectiveness/Customized-would-change analysis evaluates an immutable authored snapshot, returns an advisory diff and never writes the source or active authored prescription. Declining preserves the original plan; modified load records what the user actually chose. A pending/automatic proposal cannot become performed history.

Proposed outcome reasons include discomfort/pain, form, ROM, unusual fatigue, equipment, preference and other, with optional notes. Treat notes as private data and do not expose them in public evidence. An override does not prove the original advice wrong or diagnose injury. Later outcome review uses actual comparable observations and confounders; it is a feature proposal, not a successful experiment.

## Confidence, explanation and conflicts

Explain the action, allowed scope, effective evidence, rule and uncertainty. Do not display a single opaque optimization score as proof of effectiveness. Counts refer to real recommendations with denominators and unknown states; sets are not muscle growth. Observational association does not prove causal optimization. AI wording must stay grounded in deterministic facts, disclose assistance when relevant and cannot acquire mutation authority.

Stale evidence/revision yields superseded/invalidated advice or conflict, not silent application. Unsupported scope fails closed. Incomparable or sparse records return abstention. Existing `previewed`/`applied` legacy rows remain those states; do not relabel them as accepted/declined without evidence.

Acceptance: each load status links to real effective exposures and rule/version; an override preserves proposed and actual values; correcting a supporting set invalidates its advice; declining an authored advisory diff causes no prescription write; substitution without confirmation cannot execute; AI explanation cannot submit a design mutation. Record manual explanation review separately from software tests and training-outcome research.
