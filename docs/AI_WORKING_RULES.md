# AI Working Rules (Generated Planning)

Last updated: 2026-04-27
Status: active implementation governance

## Scope
These rules govern AI-assisted implementation for generated onboarding and deterministic generated planning.

## Core Rules
1. Runtime must not use LLM inference.
2. Generator logic must not consume raw onboarding answers directly.
3. A deterministic `GenerationProfile` must be derived first, then consumed.
4. Do not split hypertrophy programming by gender stereotypes.
5. Sex-related physiology is optional and limited to conservative load-seeding/refinement tie-breaks unless doctrine is expanded.
6. Height/limb proportions may change ranking/substitution fit, not core major-muscle volume floors.
7. Weak-point bias is bounded and cannot violate major-muscle floors or fatigue/session-balance limits.
8. Starting load source priority is:
   - logs first,
   - self-reported bests second,
   - conservative seed + RIR calibration third.
9. Movement restrictions must be movement-based and non-diagnostic.
10. Sensitive health-adjacent onboarding fields must be minimized and treated as sensitive.

## Generated/Authored Separation
- Authored templates remain independently maintained products.
- Generated path improvements must not mutate authored behavior unless a regression fix explicitly requires shared infrastructure changes.

## Documentation-to-Implementation Rule
- Before onboarding-related backend or frontend changes, implementation must reference:
  - `docs/ONBOARDING_GENERATED_PLAN_SPEC.md`
  - `docs/GENERATED_PROFILE_SCHEMA.md`
  - `docs/GENERATED_PROGRAM_STRATEGY.md`

If these docs conflict, stop implementation and resolve documentation authority first.
