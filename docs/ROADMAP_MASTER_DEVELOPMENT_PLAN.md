# Master Development Roadmap

Last updated: 2026-03-12

## Purpose

This roadmap is the execution rail for turning the current architecture into a real, usable hypertrophy coaching product.

Priority order:

1. Working software
2. Stable deterministic coaching behavior
3. Honest explanations and traces
4. Architecture cleanup that directly supports the working app

This roadmap does not redesign the architecture. It organizes the existing system into a sequence that produces usable software quickly and keeps architecture work tied to shipping outcomes.

## What "Working App" Means

The app counts as working when a real user can do the full gold path without developer intervention:

1. create an account
2. complete onboarding and profile setup
3. generate a training week
4. open the current workout
5. log sets during training
6. submit a weekly review
7. generate the next week using persisted state

Minimum quality bar:

- API endpoints succeed for the gold path
- web UI can complete the gold path without hidden manual steps
- state persists correctly between steps
- decision traces exist for authoritative coaching decisions
- explanations shown to the user come from authoritative owners, not UI or facade invention

---

## Phase 0 - Current State Review

### What Already Exists

- a deterministic core engine with extracted decision-family modules
- a generated-week path with top-level `decision_trace`
- program onboarding packages and program catalog selection
- API routes for auth, profile, plan generation, workout flows, weekly check-ins, history, and analytics
- a web app with onboarding, week, today, check-in, history, settings, and guide surfaces
- persistence for profiles, workout plans, set logs, weekly check-ins, weekly review cycles, and exercise state
- growing canonical user training state and coaching state assembly
- a significant focused test suite around generation, scheduler behavior, workout flows, and API routes

### Core Engine Modules

- `packages/core-engine/core_engine/user_state.py`
  Canonical user training state assembly.
- `packages/core-engine/core_engine/decision_generated_week.py`
  Generated-week owner and top-level generated-week trace.
- `packages/core-engine/core_engine/generation.py`
  Generation runtime preparation and orchestration.
- `packages/core-engine/core_engine/scheduler.py`
  Week execution engine.
- `packages/core-engine/core_engine/rules_runtime.py`
  Runtime rule interpretation for scheduler and adaptation behavior.
- `packages/core-engine/core_engine/decision_progression.py`
  Readiness, progression, and stimulus-fatigue-response logic.
- `packages/core-engine/core_engine/decision_weekly_review.py`
  Weekly review interpretation and review-driven adjustments.
- `packages/core-engine/core_engine/decision_workout_session.py`
  Workout route-runtime shaping.
- `packages/core-engine/core_engine/decision_live_workout_guidance.py`
  Set feedback and live workout guidance.
- `packages/core-engine/core_engine/decision_coach_preview.py`
  Coach preview and recommendation surfaces.
- `packages/core-engine/core_engine/decision_frequency_adaptation.py`
  Frequency adaptation preview/apply and persistence.

### What The Gold Path Currently Does

Today the gold path already supports most of the core loop in branch reality:

- onboarding and profile setup
- selecting a program
- generating a week from the selected program
- returning structured sessions with deload, mesocycle, and trace data
- loading the current workout via `/workout/today`
- logging workout sets
- submitting weekly check-ins and weekly review data

Current limitation:

- the product is not yet at the point where the entire gold path is proven as one clean, end-to-end user journey in a small number of high-signal integration checks
- remaining architecture work should only be done when it improves this path

---

## Phase 1 - Stabilize the Coaching Engine

### Goal

Make the generated-week coaching path stable, traceable, and honest enough that downstream product work stops fighting engine drift.

### Exit Criteria

- generated-week decisions originate from the correct owner
- scheduler behavior is execution-first, not doctrine-owning
- remaining runtime fallback policy is either removed or explicitly bounded and tracked
- authoritative generated-week traces are complete enough to explain outcomes honestly

### Tasks

1. Finish doctrine contracts for generated-week runtime inputs.
   Focus:
   - scheduler session-selection doctrine
   - deload execution doctrine
   - mesocycle doctrine
   - substitution and exercise-adjustment doctrine

2. Remove remaining fallback policy where canonical doctrine should already exist.
   Focus:
   - `rules_runtime.py`
   - `scheduler.py`

3. Make `decision_trace` completeness a hard requirement on the generated-week spine.
   Required trace coverage:
   - canonical inputs used
   - owner family
   - scheduler/runtime execution steps
   - deload and mesocycle sources
   - adaptation and review overlays

4. Verify decision-family ownership on the full generated-week path.
   Ensure:
   - `decision_generated_week.py` owns generated-week meaning
   - `generation.py` remains orchestration
   - `scheduler.py` remains execution
   - `intelligence.py` does not regain coaching authority

5. Lock this phase with focused owner-boundary and trace tests before broader product work.

---

## Phase 2 - Gold Path End-to-End Functionality

### Goal

Turn the current architecture into a clearly working application for the main user journey.

### Gold Path Scope

1. onboarding
2. generate training week
3. view workout
4. log sets
5. run weekly review
6. generate next week

### Exit Criteria

- each gold-path step works through the real API
- the web UI can drive the flow cleanly
- state persists between steps without hidden resets or manual repair
- the next generated week reflects prior workout and review state

### Tasks

1. Connect every gold-path UI surface to the real engine/API flow.
   Focus:
   - onboarding and profile selection
   - week generation view
   - workout today view
   - workout logging path
   - weekly review/check-in path

2. Verify endpoint contracts for the full gold path.
   Focus:
   - request/response schema stability
   - route error handling
   - auth and persistence boundaries

3. Make persistence behavior explicit and reliable.
   Focus:
   - generated plans
   - workout logs
   - exercise state
   - weekly check-ins
   - weekly review cycles
   - next-week generation inputs

4. Add a small number of high-signal end-to-end tests for the full loop.
   Goal:
   - prove the app works, not just isolated modules

5. Fix only the product-breaking issues surfaced by those end-to-end checks.

---

## Phase 3 - Internal Dogfooding

### Goal

Get the app into the creator's real training loop and use real cycles to find bad decisions quickly.

### Exit Criteria

- the creator can run actual training weeks in the app
- weekly generation and review cycles are usable without engineering intervention
- observed coaching errors are captured as concrete issues with reproduction data

### Tasks

1. Run personal training cycles through the gold path.

2. Verify adaptation behavior during real use.
   Focus:
   - session compression
   - deload timing
   - substitution behavior
   - weak-point preservation
   - readiness and recovery response

3. Identify incorrect decisions with trace-backed issue logging.
   Each issue should capture:
   - canonical inputs
   - emitted trace
   - observed bad output
   - expected deterministic behavior

4. Tighten product rough edges that block repeated use.
   Focus:
   - workflow friction
   - confusing screens
   - persistence surprises
   - missing action visibility

5. Keep architecture changes limited to issues discovered through real usage.

---

## Phase 4 - Coaching Intelligence Expansion

### Goal

Improve the quality of hypertrophy optimization after the gold path is already working.

### Exit Criteria

- coaching intelligence changes are grounded in existing owners and canonical state
- new behavior improves the real training loop rather than just making the architecture more elaborate

### Task Tracks

#### Weak Point Prioritization

- improve deterministic weak-point slot preservation
- improve review-to-next-week carryover for weak-point emphasis
- verify weak-point changes survive frequency compression and session caps

#### Recovery Modeling

- deepen canonical coaching state only where owners need it
- broaden safe reuse of readiness and stimulus-fatigue-response inputs
- verify recovery-driven decisions stay traceable

#### Fatigue Management

- improve deload and high-fatigue handling using explicit doctrine
- reduce remaining bounded fallback behavior
- ensure fatigue actions are explainable from trace-backed inputs

#### Exercise Substitution Intelligence

- improve substitution quality while preserving stimulus intent
- connect repeat-failure and equipment substitution logic cleanly to canonical doctrine
- verify substitution continuity through workout logging and next-week generation

### Rule For This Phase

Do not expand intelligence just because a heuristic seems useful. Expand only when the behavior is supported by canonical inputs, correct ownership, and a product need observed in dogfooding.

---

## Phase 5 - Product Readiness

### Goal

Prepare the app to be used confidently as a real product rather than an internal engine demo.

### Exit Criteria

- the gold path is stable
- the UI is understandable without architecture context
- onboarding is low-friction
- documentation supports contributors and future AI implementation passes

### Tasks

1. Stability improvements.
   Focus:
   - regression protection
   - API contract hardening
   - production-safe error handling
   - migration and persistence confidence

2. UI clarity.
   Focus:
   - clean gold-path navigation
   - obvious workout actions
   - clear review and next-step flow
   - honest explanation rendering

3. Onboarding polish.
   Focus:
   - selected program clarity
   - equipment and schedule setup
   - first-week generation success rate

4. Documentation.
   Focus:
   - contributor-facing development rails
   - product-facing setup and usage docs
   - clear definitions of what is stable versus still bounded-trust

5. Release-readiness checks.
   Focus:
   - minimal smoke coverage
   - deployment confidence
   - issue triage rules

---

## Recommended Work Sequence

If the team wants the shortest path to a usable application, work in this order:

1. close the remaining generated-week doctrine and fallback gaps that still affect output quality
2. prove the full gold path with a small number of end-to-end tests
3. run real internal dogfooding cycles
4. improve coaching quality based on observed failures
5. polish the product only after the loop is reliable

## Anti-Drift Rule

If a task does not improve one of these, it should not take priority:

- gold-path completion
- output correctness
- persistence reliability
- trace honesty
- dogfood usability

Architecture cleanup is valuable only when it directly supports those outcomes.
