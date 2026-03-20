# Decisions

Last updated: 2026-03-20

These decisions are locked unless explicitly replaced by a new decision entry.

- `D-001`
  `/reference` is the sole canonical hypertrophy knowledge corpus.
- `D-002`
  `docs/guides/*` is deterministic build-time diagnostic output derived from `/reference`. It is not canonical runtime input.
- `D-003`
  Runtime never reads raw `/reference`.
- `D-004`
  Runtime consumes only compiled artifacts.
- `D-005`
  Runtime remains deterministic and must not depend on a paid LLM.
- `D-006`
  Authored programs remain first-class selectable products.
- `D-007`
  The app has two first-class modes: `authored` and `optimized_generated`.
- `D-008`
  `/reference` doctrine, `SystemCoachingPolicy`, and the runtime `DecisionEngine` are distinct layers.
- `D-009`
  Policy may rank doctrine-valid choices but may not silently violate hard constraints.
- `D-010`
  Hard constraints and soft preferences are separate contract types.
- `D-011`
  Minimum-viable-program fallback is required.
- `D-012`
  Anti-overadaptation rules are required for later major changes.
- `D-013`
  Data sufficiency rules are required before later major changes unless safety overrides apply.
- `D-014`
  Generated v1 is `Full Body` only.
- `D-015`
  Generated `Upper/Lower`, generated `PPL`, and "best split for me" are future targets, not current-scope features.
- `D-016`
  The current milestone does not change routers, DB models, authored-program behavior, or generated-program logic.
- `D-017`
  For this milestone only, the canonical exercise library may be seeded from onboarding packages as a deterministic foundation stage.
- `D-018`
  Long term, core generation, adaptation, and explanation should be able to run locally or offline from compiled artifacts.
