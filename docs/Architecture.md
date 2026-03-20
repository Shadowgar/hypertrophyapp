# Architecture - Adaptive Coaching Runtime

Last updated: 2026-03-20

This document describes the current runtime architecture. For governance rules, see `docs/architecture/GOVERNANCE_CONSTITUTION.md`. For module-level authority, see `docs/architecture/RUNTIME_AUTHORITY_MAP.md`.

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
- Evaluates progression, fatigue, deload, transition, substitution, and generated-week scheduler policy runtimes

3. Exercise Catalog Service
- Canonical exercise IDs, aliases, muscles, equipment, default media, substitutions

4. User State Service
- Stores logs and progression state
- Stores profile constraints and canonical `constraint_state`
- Stores weekly-checkin-backed readiness inputs and canonical `readiness_state`
- Stores fatigue/adherence/stall markers

5. Decision Engine (`packages/core-engine/core_engine/`)
- Inputs: template + rules + user state
- Outputs: today's plan, post-session evaluation, next-session adaptation
- Implemented as individual decision-family modules:
  - `decision_generated_week.py` -- week plan generation and template selection
  - `decision_progression.py` -- progression actions, phase transitions, stimulus-fatigue-response, readiness
  - `decision_weekly_review.py` -- review summarization, adjustment interpretation, plan overlay
  - `decision_workout_session.py` -- today routing, log-set, progress, summary
  - `decision_coach_preview.py` -- coach intelligence preview, apply, finalize
  - `decision_frequency_adaptation.py` -- frequency change preview/apply
  - `decision_program_recommendation.py` -- program switching
  - `decision_live_workout_guidance.py` -- real-time set feedback
- Supporting modules:
  - `rules_runtime.py` -- doctrine substrate (deload, substitution, mesocycle, muscle coverage, session selection)
  - `scheduler.py` -- execution engine (builds week plan from rules + template; does not define doctrine)
  - `user_state.py` -- canonical user training state assembly
  - `generation.py` -- generation runtime preparation and orchestration
  - `intelligence.py` -- orchestration-only compatibility façade (no new decision families allowed)

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

Current state and remaining risks:
- decision-family extraction is complete; all meaningful coaching decisions live in named `decision_*.py` owners
- `intelligence.py` is designated orchestration-only; no new decision families are permitted there
- canonical `readiness_state` is present and influences coach-preview and weekly-review scoring
- the deterministic stimulus-fatigue-response layer is live in the progression family, feeds generated-week deload/substitution pressure through `rules_runtime.py`, and powers weekly-review bounded adjustments
- canonical repeat-failure generation-time substitution is powered by persisted `ExerciseState`
- broader exercise-level SFR-driven generation use is still pending
- active administered full-body programs are `pure_bodybuilding_phase_1_full_body` and `pure_bodybuilding_phase_2_full_body`
- Phase 2 block transition checkpoints are now trace-visible via mesocycle runtime output

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
