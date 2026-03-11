# Governance Constitution

## Purpose

This document is the master constitutional authority for the runtime governance model of this repository.

It defines:

- illegal architectural states
- the scope of authoritative coaching decisions
- trace completeness requirements
- explanation classification rules
- truth budget limits
- shadow-authority rules
- sovereignty scopes
- promotion, demotion, and release-blocking rules
- enforcement classes

If another document conflicts with this one, this document wins.

## Scope

This constitution applies to every first-class path.

A first-class path is any user-facing flow that:

- is intended for real use
- is not hidden or explicitly experimental
- produces coaching decisions or coaching-relevant explanations
- influences user training behavior

This includes:

- onboarding-generated plan
- generated week
- today workout
- substitutions
- progression and deload outcomes
- weekly review
- recommendation and switch surfaces
- analytics or history insights that appear to explain coaching behavior

## Illegal States

The following repo states are architecturally illegal even if the app still runs and tests still pass.

- A presentation surface implies coaching rationale that is neither trace-derived nor clearly labeled as non-authoritative display text.
- An execution module invents doctrine that is not present in canonical artifacts or explicit policy-owner logic.
- A semantically insufficient artifact is used to justify a first-class coaching decision.
- A bounded-trust path is surfaced with global-trust language.
- `intelligence.py`, any orchestrator, any router, or any UI component changes the meaning of a coaching outcome rather than forwarding or rendering it.
- A non-gold program is exposed as equal to the gold benchmark without passing its maturity gate.
- A first-class coaching surface emits an authoritative coaching decision without a sufficiently complete `decision_trace`.
- A summary surface presents explanation-like language for a coaching outcome without authoritative rationale behind it.
- Documentation, tests, naming, status language, or UI copy imply sovereignty or doctrine completeness that the runtime does not actually have.
- A path is promoted despite known semantic insufficiency in a visible first-class behavior.

## Authoritative Coaching Decision Definition

An authoritative coaching decision is any runtime output that changes or explains:

- what session gets performed
- what exercise gets selected, retained, dropped, merged, or replaced
- what order or structure is used
- what progression action occurs
- what deload action occurs
- what recommendation or switch advice occurs
- what adaptation or compression occurs
- what user-facing explanation is presented as the reason for those outcomes

If a code path changes or explains one of those outcomes, it is under this constitution.

## Semantic Insufficiency

Semantic insufficiency is a formal warning category.

An artifact or flow is semantically insufficient when it is:

- structurally valid
- technically load-valid
- but still does not preserve enough meaning to justify the coaching behaviors currently exposed to the user

Examples:

- workout shape is preserved, but effort semantics are lost
- exercise identity is preserved, but substitution meaning is missing
- week structure is preserved, but progression intent is flattened
- recommendation is possible, but doctrine coverage is too shallow to justify strategic claims

No semantically insufficient artifact may be treated as authoritative on a first-class path.

## Trace Completeness Law

Every authoritative coaching decision must emit a complete enough `decision_trace` to explain why that outcome happened from canonical inputs.

A minimally valid `decision_trace` must contain fields equivalent to:

- `owner_family`
- `canonical_inputs`
- `policy_basis`
- `execution_steps`
- `outcome`
- `reason_summary`
- `alternative_resolution`
- `trust_scope` when bounded trust applies

The exact field names may vary. The semantic content may not.

A trace may be compact, but it may not be too thin to answer:

- which canonical inputs mattered
- which policy owner acted
- which execution step transformed the result
- why this outcome happened
- why alternatives lost, if alternatives existed

No first-class coaching output is authoritative unless its trace is sufficiently complete to justify the outcome.

## Explanation Law

All user-visible text that appears to explain behavior must be classified as exactly one of the following:

### Authoritative Rationale

Trace-derived and safe to present as the reason something happened.

### Descriptive Summary

Non-rationale text that summarizes already-known facts but does not explain why a decision happened.

### Generic Fallback

Placeholder or humanizing copy that exists only to avoid blank UI.

Generic fallback may not be presented as rationale.

Examples:

- "You trained chest twice this week." -> descriptive summary
- "You trained chest twice this week because recovery supported more volume." -> authoritative rationale and requires trace support
- "Keep following the plan." -> generic fallback

This law applies to:

- Today
- Week
- coach preview and apply
- recommendation reasons
- weekly review summaries
- progress feedback
- deload rationale
- history summaries
- analytics insights

## Truth Budget Law

A surface may only claim as much intelligence, coaching depth, or explanation authority as its compiled doctrine, canonical state, and trace completeness can support.

Polished UI does not increase truth budget.

Local green tests do not increase truth budget.

Structural fidelity alone does not increase truth budget.

One strong gold path does not increase the truth budget of weaker paths.

No surface may claim more intelligence than the compiled doctrine and canonical state behind it can justify.

## Shadow Authority

Shadow authority is any code path, helper, execution surface, summary layer, or UI layer that is not declared as a policy owner but still changes or explains a coaching outcome in a way that affects runtime behavior or user understanding.

Examples:

- `intelligence.py` shaping generation meaning instead of forwarding it
- `scheduler.py` inventing weak-point doctrine rather than executing it
- UI humanization sounding causal when no trace supports it
- summary text implying "why" rather than only "what"
- helper logic silently constraining decisions outside a named owner

Shadow authority is constitutionally illegal on first-class paths.

## No Silent Authority Transfer Rule

Any new decision-affecting logic introduced outside a named owner must be flagged immediately.

Any owner change must be explicit in:

- `docs/current_state_decision_runtime_map.md`
- tests covering the affected family
- trace contract expectations

Any new decision family must declare:

- owner
- doctrine source
- execution layer
- trace contract
- trust scope

No authority may move by accident through refactor, helper growth, naming drift, or summary-layer wording.

## Sovereignty Scopes

### Path-Scoped Sovereignty

A path has path-scoped sovereignty when, for that specific flow:

- authoritative coaching decisions come only from named policy owners
- canonical artifacts and canonical state are the knowledge source
- execution modules do not invent doctrine
- the explanation law holds
- trace completeness is sufficient for the exposed behavior
- semantic insufficiency has been cleared for the claims that path makes

One path may achieve path-scoped sovereignty before the rest of the repo does.

### Repo-Wide Sovereignty

The repo has repo-wide sovereignty only when:

- no meaningful coaching decisions anywhere occur outside named owners
- `intelligence.py` is harmless orchestration only
- routers and UI never change or explain coaching meaning authoritatively
- active runtime programs do not bypass canonical maturity requirements
- trust language across the product matches actual trust scope

The repo does not have repo-wide sovereignty today.

## Claim Downgrade

If a path is acceptable within bounded trust but its language exceeds its truth budget, the fix may be a claim downgrade rather than a tier demotion.

Examples:

- recommendation may remain usable, but product language must say "early deterministic recommendation logic" rather than "strategic coaching intelligence"
- weekly review may remain live, but product language must say "bounded readiness/SFR-aware review logic" rather than "complete recovery intelligence"

Claim downgrade is required whenever wording exceeds truth budget even if the runtime tier does not change.

## Promotion, Demotion, and Release Block Rules

### Promotion

A path may move to a higher trust or maturity tier only when all are true:

- sovereignty requirements hold for that path
- semantic insufficiency is cleared for the exposed behaviors
- the explanation law holds on visible surfaces
- doctrine coverage is sufficient for the user-visible claims
- traces are complete enough to audit the authoritative decisions
- any required felt-behavior audit passes

### Demotion

A path must be demoted if any are true:

- stale docs, tests, naming, or UI copy overstate maturity
- semantic insufficiency is discovered in exposed behavior
- explanation integrity regresses
- hidden authority reappears in execution, orchestration, or presentation layers
- bounded trust is being experienced or marketed as global trust

### Release Block Rule

Any semantically insufficient artifact or flow on a first-class user path blocks promotion of that path beyond its current trust tier.

Examples:

- if the gold path still lacks effort semantics needed for visible coaching claims, it cannot reach Tier 4B
- if explanation text still ambiguously mixes fallback with rationale, that surface cannot receive global-trust claims
- if recommendation logic remains doctrine-shallow, it cannot be surfaced as strategic coaching authority

## Enforcement Classes

### Must-Fail

- Any real coaching authority remains in `intelligence.py`
- Any router contains coaching policy branches that change or explain authoritative coaching outcomes
- Any first-class coaching surface emits an authoritative coaching decision without a minimally valid `decision_trace`
- Any rationale-like UI text is presented without being classifiable as authoritative rationale, descriptive summary, or generic fallback
- Any semantically insufficient artifact is used to justify a first-class coaching decision
- Any execution module invents doctrine not present in canonical artifacts or named owner policy
- Any bounded-trust path is presented with global-trust language
- Any non-gold path is presented as equal to gold without passing its maturity gate

### Promotion-Blocking

- Gold structural fidelity and doctrinal fidelity gap lists are stale
- Explanation classification is incomplete on the path being promoted
- Trace completeness is partial but not absent
- A required felt-behavior audit has not been completed
- A path still has unresolved shadow-authority seams
- A path has bounded trust but lacks bounded-trust labeling in docs, tests, or product language

### Release-Blocking

- Any must-fail condition exists on a path proposed for release
- Any first-class released path has known semantic insufficiency in a visible coaching behavior
- Any docs, product copy, or status language overclaim the trust tier of a released path
- Any non-gold first-class path is released without explicit trust or maturity qualification
- Any authoritative released surface mixes fallback text with rationale ambiguously

### Advisory

- Legacy wrapper or orchestration code still exists but is not changing coaching meaning
- A surface is structurally strong but still bounded in doctrine depth
- A path is trustworthy internally but not yet ready for public-facing claims
- A module boundary is awkward but is not currently creating shadow authority

