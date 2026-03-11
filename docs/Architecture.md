# Architecture - Adaptive Coaching Target State

Last updated: 2026-03-10

## Runtime Boundary

Runtime reads only:
- canonical program templates
- canonical coaching rules
- exercise catalog
- user training state

Adaptive gold assets may enter runtime only after they are adapted at the loader boundary into the same canonical runtime template/rule contracts. Runtime does not special-case raw gold schema payloads downstream.

Runtime does not read raw `reference/*.pdf` or `reference/*.xlsx`.
Runtime does not depend on `docs/guides/generated/*.md` text artifacts.

## Runtime Components

1. Template Runtime Service
- Resolves active program/phase/week/day
- Delivers ordered exercise slots and prescriptions

2. Rules Runtime Service
- Loads typed coaching rules per program scope
- Evaluates progression, fatigue, deload, transition, substitution decisions

3. Exercise Catalog Service
- Canonical exercise IDs, aliases, muscles, equipment, default media, substitutions

4. User State Service
- Stores logs and progression state
- Stores profile constraints and canonical `constraint_state`
- Stores weekly-checkin-backed readiness inputs and canonical `readiness_state`
- Stores fatigue/adherence/stall markers

5. Decision Engine
- Inputs: template + rules + user state
- Outputs: today's plan, post-session evaluation, next-session adaptation

## Decision Runtime Sovereignty

The runtime is only correct when the decision engine is the final authority for meaningful coaching decisions.

Sovereignty rules:
- meaningful coaching decisions must be executed in `packages/core-engine`
- API routers may not invent coaching decisions on their own
- preview and apply flows must call the same interpreter for a given decision family
- explanations must be emitted from interpreter output, not reconstructed independently
- every meaningful decision must emit a structured decision trace

Meaningful coaching decisions include:
- program recommendation
- frequency adaptation
- substitution selection
- progression changes
- deload triggers
- phase transitions
- weak-point adjustments

## Operational Authority Map

Current local-branch ownership is tracked in:
- `docs/current_state_decision_runtime_map.md`

Use that file as the operational source of truth for:
- authoritative module ownership by decision family
- canonical inputs and outputs
- trace expectations
- what routers may still do
- whether `intelligence.py` is acting as a thin façade or still owns live logic

Current dominant risks have shifted:
- router glue is no longer the dominant architectural risk
- authority ambiguity and wrapper drift in `packages/core-engine/core_engine/intelligence.py` is now a primary risk
- shallow first-class coaching state is now a primary modeling risk
- the deterministic stimulus-fatigue-response layer is now live but still early-stage and not yet broadly consumed for bounded adjustment decisions
- canonical `readiness_state` is now present and influences both coach-preview and weekly-review scoring
- the first deterministic `stimulus_fatigue_response` layer now exists in the progression family, now feeds generated-week deload/substitution pressure and weekly-review bounded adjustments, and now sits alongside canonical repeat-failure generation-time substitution powered by persisted `ExerciseState`; broader exercise-level generation use is still pending

6. API/UI Layer
- Program selection
- Workout execution and logging
- Explainable adaptation timeline

## Build-Time Components

1. Excel importer pipeline -> canonical program objects
2. PDF doctrine distillation pipeline -> typed coaching rules
3. Provenance and quality gates -> verification reports

## Legacy Components To Isolate

- `importers/reference_corpus_ingest.py` generated markdown guides remain build artifacts only.
- `GET /plan/intelligence/reference-pairs` is informational provenance, not coaching runtime logic.
- any runtime path that lacks canonical artifacts is legacy and must not gain new coaching behavior.

## Deployment Principle

Single-node deployment can remain unchanged (web/api/postgres/caddy). The architecture change is a domain-model and runtime-boundary change, not a hosting change.
