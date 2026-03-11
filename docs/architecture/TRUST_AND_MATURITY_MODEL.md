# Trust and Maturity Model

## Purpose

This document defines:

- trust levels
- truth budget rules
- program maturity tiers
- promotion and demotion rules
- claim downgrade rules
- release gates

It governs what the product is allowed to claim at each level of runtime maturity.

## Trust Levels

### Not Trustworthy Yet

A surface or path is not trustworthy yet when:

- it is still mixed in authority
- it depends on semantically insufficient artifacts for visible coaching behavior
- its explanation integrity is incomplete
- its trust language would exceed its truth budget

### Bounded Trust

A surface or path has bounded trust when:

- it is trustworthy only within the exact doctrine and canonical-state coverage currently compiled for it
- it may be internally useful or user-visible with constrained claims
- it must not be presented as globally coach-authoritative

### Global Trust

A surface or path has global trust only when:

- sovereignty requirements hold for the relevant product scope
- doctrine coverage is sufficient for the exposed behaviors
- explanation law holds
- trace completeness holds
- semantic insufficiency is cleared for the claims being made

Most of the repo today has bounded trust.

Almost nothing today has global trust.

## Truth Budget Rules

A feature may only claim as much intelligence, coaching depth, or explanation authority as its compiled doctrine, canonical state, and trace completeness can support.

Truth budget is not increased by:

- polished UI
- local green tests
- structural fidelity alone
- one strong gold path

Truth budget is path-specific.

Bounded trust must not be experienced as global trust.

## Program Maturity Tiers

### Tier 0 - Runtime-Loadable Only

- program loads successfully
- no authority claim is allowed

### Tier 1 - Structurally Canonical

- week, day, and slot structure validated
- sequence shape preserved

### Tier 2 - Exercise-Safe

- exercise IDs validated
- exercise metadata sufficient for safe substitution and compression behavior

### Tier 3 - Doctrine-Backed Bounded

- compiled doctrine is sufficient for the exposed coaching behaviors on that path
- trust remains bounded

### Tier 4A - First-Class Internal

- safe enough for serious internal dogfood
- structurally strong
- doctrine good enough for honest internal use
- still may require qualification externally

### Tier 4B - First-Class Product-Facing

- strong enough to be presented as a real coaching path without qualification
- sovereignty, doctrine, explanation, and trace integrity are all strong enough for product-facing equality within its class

## Promotion Rules

A path may move to a higher tier only when all are true:

- sovereignty requirements hold for that path
- semantic insufficiency is cleared for the exposed behaviors
- explanation law holds
- doctrine coverage is sufficient for the user-visible claims
- trace completeness is sufficient
- any required felt-behavior audit passes

## Demotion Rules

A path must be reduced in tier if any are true:

- stale docs, tests, naming, or UI copy overstate maturity
- semantic insufficiency is discovered
- explanation integrity regresses
- hidden authority reappears
- bounded trust is being experienced or marketed as global trust

## Claim Downgrade Rules

Claim downgrade applies when:

- a path remains acceptable within bounded trust
- but its product language exceeds its truth budget

In that case:

- the path may remain at its current tier
- user-visible claims must be reduced to the highest truthful claim level

Examples:

- recommendation may stay live, but UI copy must say "early deterministic recommendation logic" rather than "strategic coaching intelligence"
- weekly review may stay live, but UI copy must say "bounded readiness/SFR-aware review logic" rather than "complete recovery intelligence"

## Release Gates

### Gate 1 - Internal Dogfood

Before a path is suitable for serious internal use:

- the path is at least Tier 4A
- no mixed-authority seam on that path can change outcome meaning
- explanations are authoritative or clearly non-authoritative
- desktop and mobile flows are validated
- a felt-behavior audit passes:
  - the path feels like a coach, not a planner
  - explanations match visible behavior
  - substitutions feel stimulus-preserving
  - progression and deload behavior feel justified
  - compression preserves intent rather than only compressing volume mechanically

### Gate 2 - Honest Private Beta

Before another lifter uses the path without oversell:

- Gate 1 is complete
- docs match branch reality
- non-gold programs are clearly gated or qualified
- no presentation layer fakes rationale on visible user paths

### Gate 3 - Serious Hypertrophy Coach Claim

Before the product can honestly use that phrase:

- no authoritative coaching decision occurs outside sovereign owners
- `intelligence.py` is harmless orchestration only
- doctrine coverage is sufficient for exposed coaching behavior
- exercise knowledge is coaching-grade, not merely ID-grade
- traces are complete
- the gold path is Tier 4B
- non-gold claims do not exceed non-gold maturity

## Trust-Claim Ceiling by Surface

| Surface | Current maximum truthful claim |
| --- | --- |
| Gold-path generated week | Deterministic generated training week from compiled program structure, canonical user state, and bounded adaptation logic |
| Today workout | Deterministic daily workout selection and live workout guidance for covered runtime paths |
| Substitutions | Deterministic substitutions for covered exercises using compiled exercise metadata, equipment compatibility, and repeat-failure logic |
| Progression | Deterministic progression and hold/reduce behavior for covered families using current state and compiled rules |
| Deload behavior | Deterministic scheduled and bounded recovery-triggered deload behavior for covered paths |
| Weekly review | Readiness- and SFR-aware bounded weekly review and adjustment logic |
| Recommendation and switch | Early deterministic recommendation logic from canonical state and current runtime criteria |
| Coach preview and apply | Deterministic preview and apply logic for covered recommendation families |
| History and analytics | Deterministic summaries and analytics of logged training history |
| Gold path overall | Strong internal benchmark path built from compiled artifacts |
| Non-gold programs | Runtime-supported programs with varying maturity, not equivalent to the validated gold benchmark |

