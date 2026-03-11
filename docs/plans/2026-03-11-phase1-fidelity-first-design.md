# Phase 1 Fidelity-First Design

Last updated: 2026-03-11
Status: Approved design for next major implementation wave

## Goal

Make the current full-body adaptive gold path materially closer to the real `Pure Bodybuilding Phase 1 - Full Body` authored workbook while preserving the deterministic adaptive runtime architecture.

This phase is intended to move the product from "strong engine foundation" toward "real hypertrophy operating system I could actually trust in the gym." The primary success condition is not broader feature count. It is a more faithful, more coach-like full-body path that still adapts deterministically to real-world constraints.

## Why This Is The Right Next Move

Current repo state:
- the deterministic engine is substantially more mature than the product surface
- the adaptive-gold runtime path is stable enough to serve as the validation spine
- later-week authored mesocycle behavior, deloads, transition-pending state, substitution continuity, and bounded constraint handling are already in place
- the current gold full-body runtime is still a compressed approximation of the real source program, not a close reproduction

User reality:
- the project owner is currently following the real Phase 1 full-body workbook
- trust will come faster from matching that lived program experience than from broadening into more generalized features first

Doctrine sweep reinforcement from docs + source materials:
- structured mesocycles matter
- intro/ramp weeks matter
- early-set versus last-set effort structure matters
- weak-point and arms work are first-class, not optional decorations
- substitutions are part of the doctrine, not a UX patch
- exercise variation should be systematic, not random
- nutrition should eventually support small-surplus / maintenance / small-deficit paths, not crash-diet heuristics

## Non-Divergence Statement

This is not a break from the current plan.

It is a reprioritization inside the existing plan structure:
- Phase B: stronger gold baseline fidelity
- Phase C: better doctrine extraction and authored-source usage
- Phase D: smarter adaptation from a more faithful authored source
- Phase E: more credible gold end-to-end runtime
- Phase H: better user-testing readiness because the product will more closely match a trusted real program

What is *not* changing:
- runtime still must not parse raw PDFs/XLSX
- canonical templates/rules/state remain the runtime authority
- deterministic traces remain required
- routers remain thin
- AI/chatbot logic is still not the workout authority

What *is* changing:
- the next major work wave should optimize for fidelity to the Phase 1 full-body authored doctrine before broadening more features or more generalized program coverage

## Core Design Decision

Do not build a new engine.
Do not add a one-off runtime path.
Do not make runtime depend on raw documents.

Instead, strengthen the existing architecture so that:

1. the actual workbook/PDF pair remains the fidelity target
2. the onboarding package is treated as an intermediate authored artifact that may itself require reconciliation
3. the adaptive gold runtime template tracks the corrected authored source more faithfully
4. the loader preserves more authored week/day/slot semantics
5. the scheduler adapts from the faithful 5-day authored source downward to 4/3/2 days only when needed
6. the product explains the resulting week as a coach-authored block, not a generated spreadsheet clone

## Architecture

### 1. Source Doctrine Boundary

Primary fidelity targets for this phase:
- `reference/Pure Bodybuilding Phase 1 - Full Body Sheet.xlsx`
- `reference/The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf`

Intermediate authored source:
- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json`

Runtime-safe output target:
- `programs/gold/adaptive_full_body_gold_v0_1.json`

Current correction from the source audit:
- the onboarding package is richer than the runtime path, but it is still not a faithful 1:1 representation of the actual workbook/PDF
- the workbook/PDF contain materially different day structures and exercise lineups than the current onboarding package

That means the onboarding package should be treated as:
- the best current structured artifact
- but not the unquestioned final source of truth for this fidelity-first phase

This phase therefore needs to reconcile the onboarding package toward the actual workbook/PDF for:
- 5-day day structure
- week-by-week authored intent
- slot roles
- weak-point and arms logic
- exercise knowledge and substitution candidates
- intensity/effort progression cues

The adaptive gold runtime template should become a closer runtime projection of the corrected authored source, not a loosely related gold sample.

### 2. Loader Boundary

Primary files:
- `apps/api/app/program_loader.py`
- `apps/api/app/adaptive_schema.py`
- `apps/api/app/template_schema.py`

Responsibilities in this phase:
- preserve more authored week/day/slot fidelity from the onboarding-backed doctrine
- preserve richer week-role semantics beyond generic accumulation/deload/intensification labels where justified
- preserve weak-point day semantics and arms-day semantics
- preserve authored day count (`5`) as the source schedule truth
- continue adapting into runtime-safe structures without introducing a parallel path

### 3. Scheduler Boundary

Primary file:
- `packages/core-engine/core_engine/scheduler.py`

Responsibilities in this phase:
- treat authored 5-day structure as the default doctrinal truth
- compress into 4/3/2 days only when user constraints require it
- protect compounds, weak-point work, and high-value slot roles during compression
- reduce lower-priority accessories before higher-priority authored intent
- preserve intro-week logic and later intensification logic when adapted downward
- keep mesocycle explanation explicit in output and traces

### 4. Decision Runtime Boundaries

Primary files:
- `packages/core-engine/core_engine/decision_progression.py`
- `packages/core-engine/core_engine/decision_weekly_review.py`
- `packages/core-engine/core_engine/decision_coach_preview.py`
- `packages/core-engine/core_engine/decision_live_workout_guidance.py`

Responsibilities in this phase:
- consume the more faithful authored template without needing a new decision-family split
- preserve deterministic rationale for intro weeks, intensification, substitutions, deloads, and phase completion
- avoid inventing a generalized doctrine layer beyond what the current artifacts can support

### 5. Product Surface Expectations

Primary files likely impacted later in the implementation wave:
- `apps/web/app/today/page.tsx`
- `apps/web/app/week/page.tsx`
- `apps/web/components/coaching-intelligence-panel.tsx`
- `apps/web/lib/api.ts`

Product expectation for this phase:
- the app should increasingly feel like it is delivering a real coached block
- `Today` should show a believable workout derived from an authored program
- `Week` should reflect the block structure clearly
- post-week transition behavior should remain explicit
- no false “AI magic” claims; the intelligence must stay explainable

## Success Criteria

### User-facing success
- the full-body path feels recognizably like the real Phase 1 workbook
- session ordering and emphasis make sense across a 5-day week
- weak-point and arms work are preserved intentionally
- intro weeks feel like adaptation weeks
- later weeks feel more aggressive/intensified
- substitutions feel coherent and exercise-specific
- constrained schedules still preserve the most important block intent
- block completion is obvious to the user

### Engineering success
- authored 5-day structure is represented more faithfully than today
- 5-day generated output closely tracks the authored workbook
- 4/3/2-day compression preserves doctrinal priorities
- intro weeks, intensification, deload, and weak-point semantics survive runtime generation
- workout/today/logging/history flows still work on the updated path
- traces and rationale remain deterministic and intelligible

## Out Of Scope For This Phase

Not part of this implementation wave:
- broader multi-program migration from the full `/reference` corpus
- native iOS product work
- Apple Health integration
- full nutrition/macros/calories product system
- full body-comp / measurement system
- replacing deterministic logic with AI runtime logic

These remain future priorities, but not the best immediate move.

## Product Intelligence Position

This phase still supports the larger vision of building something as close as possible to an AI-smart hypertrophy system without chatbot-driven workout authority.

The model remains:
- structured doctrine + canonical templates + canonical user state + deterministic adaptation

This is *not* less intelligent than a generalized approach.
It is actually a smarter sequencing choice because:
- trust starts with fidelity on one real program
- once one path is believable, broader generalization becomes safer
- grounded intelligence beats broad but shallow “smartness”

In short:
this phase makes the app more faithful first so it can become more broadly intelligent later without losing rigor.
