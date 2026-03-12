# Design Intent Comparison - 2026-03-07

## Purpose

This document compares the external architectural specification for Rocco's HyperTrophy against the actual repository state on 2026-03-07.

It answers a narrower question than the exhaustive review:

Does the current implementation match the intended application design?

## Bottom-Line Verdict

The implementation is **closer to the intended design than the external spec's "common failure cases" warning suggests**, but it is still **well short of the full intended hypertrophy coach**.

Most important conclusion:

- This repo is **not** just a static workout list or simple tracker.
- It **does** already contain a real substitution path, equipment-aware planning, adaptive schedule compression, progression logic, weak-point handling, soreness/fatigue inputs, weekly review logic, and historical analytics.
- It **does not yet** fully embody the design's deeper program-knowledge ambition: a broad doctrine-backed, typed-rules coaching engine that fully understands program philosophy across the library.

In short:

- The adaptive engine exists in meaningful partial form.
- The full coaching knowledge layer is still incomplete.

## Comparison Summary

| Design Area | Status | Notes |
| --- | --- | --- |
| Adaptive schedule builder | Implemented, partial | Real day-compression and redistribution logic exists, but not the final doctrine-backed engine. |
| Equipment constraint handling | Implemented | Equipment-aware filtering and substitution prefiltering are in production code. |
| Substitution engine | Implemented, partial | User can swap from equipment-incompatible exercises using compatible substitutions. Ranking sophistication is still limited. |
| Weak body part prioritization | Implemented, partial | Weak areas influence onboarding adaptation, weekly review adjustments, and frequency adaptation. |
| Fatigue / recovery / deload | Implemented, partial | Soreness, readiness, adherence, and underperformance feed progression and deload behavior. Broader recovery state is not fully modeled. |
| RPE / RIR tracking | Implemented, partial | RPE is stored, logged, and used by progression logic; full RIR/RPE doctrine encoding is not complete. |
| Progression system | Implemented, partial | Working-weight updates and progression recommendations exist. Full rules-runtime coverage is not done. |
| Missed workout recovery | Partial | Resume flow exists and schedule compression exists, but a dedicated missed-day recovery engine is not fully separated as its own subsystem. |
| Program import from Excel | Implemented, transitional | XLSX importer exists and now emits diagnostics. Canonical importer v2 is still missing. |
| PDF understanding / doctrine extraction | Early | Corpus ingestion and workbook/PDF pairing exist, but broad typed rule distillation is not complete. |
| Exercise knowledge system | Partial | Exercise-level notes, video, muscles, movement/equipment tags exist in templates/schemas, but not yet as a rich centralized exercise database. |
| Program library | Implemented | Multiple programs can be listed, selected, switched, and browsed. |
| Program timeline awareness | Implemented, partial | Runtime knows current week/day and deload context, but full authored timeline fidelity across all programs is still evolving. |
| Historical tracking / analytics | Implemented | History analytics, calendar, day detail, PRs, strength trends, volume heatmaps, and recommendation timeline exist. |
| Dashboard | Implemented, partial | Home route now shows live dashboard data instead of static placeholders, but still not the final consumer-grade dashboard. |
| Security / privacy | Partial | Standard auth/private-user data model exists, but the broader hardening roadmap is still incomplete. |

## What The External Spec Gets Right

The external design correctly identifies the core mission:

- this should be a hypertrophy program engine, not just a tracker
- programs should be understood structurally
- adaptation should preserve stimulus under real-world constraints
- progression, fatigue, equipment, weak points, and adherence should drive decisions

That is still the right design target for this repository.

It is also correct that the app is incomplete if any of these are entirely absent:

- substitution engine
- schedule adaptation
- progression logic
- program intelligence

## What The Current Repo Already Has That The Spec's Failure-Warning Might Miss

These systems are already present in real code.

### 1. Adaptive schedule builder exists

The repo already has deterministic day-compression and schedule adaptation logic.

Current behavior includes:

- respecting `days_available`
- compressing sessions evenly when days are reduced
- preserving priority lifts
- keeping weak-area stimulus during compression
- reporting tradeoffs and muscle-set deltas

This means the implementation is already beyond "static workout lists".

### 2. Equipment-aware substitution exists

The repo already:

- stores user equipment profile
- infers or resolves equipment tags
- filters exercise compatibility by available equipment
- prefilters compatible substitutions
- exposes substitution choices in the workout UI

That means the design's substitution requirement is partially delivered in a usable form.

### 3. Progression logic exists

The repo already:

- stores logged weight/reps/RPE
- updates exercise state after workouts
- computes next working weight
- tracks fatigue score at the exercise-state level
- recommends `progress`, `hold`, or `deload`

This is not final doctrine-backed progression, but it is real progression logic.

### 4. Weak-point logic exists

Weak areas already affect:

- onboarding frequency adaptation overlays
- weekly review adjustments
- specialization previews
- bounded extra practice / set adjustments

So the design's weak-body-part requirement is partially implemented rather than missing.

### 5. Fatigue and deload logic exists

The current code already uses:

- soreness inputs
- adherence score
- completion percentage
- underperformance streaks
- readiness score

to influence:

- progression action
- phase transitions
- early deload / scheduled deload behavior
- weekly review outputs

### 6. Historical analytics exists

The current implementation already stores and surfaces:

- set logs
- bodyweight trends
- strength trends
- PR highlights
- weekly check-in history
- calendar-based session history
- day-level detail including sets and volume

This is substantially beyond a basic tracker history page.

## Where The Repo Is Still Meaningfully Behind The Intended Design

These are the major architectural gaps.

### 1. Exercise knowledge base is not yet a rich centralized system

The design calls for a deep exercise knowledge base with:

- instructions
- technique cues
- common mistakes
- injury considerations
- alternatives
- difficulty
- movement pattern
- muscle metadata

Current state:

- some of this exists in template/schema fields and guide responses
- guide pages exist
- videos and notes exist
- movement/equipment/muscle metadata exists in important places

But:

- there is not yet a clearly centralized, comprehensive exercise database that fully satisfies the intended schema richness
- the exercise guide UI still exposes sparse data and remains more implementation-oriented than polished coaching content

### 2. Program understanding is only partial

The design intends the system to understand:

- why exercises exist
- what philosophy the phase is serving
- how progression works at a program-design level

Current state:

- program templates, deload config, progression config, and guide routing exist
- a gold rules schema exists
- onboarding packages encode blueprint structure

But:

- most runtime behavior is still not driven by a broad doctrine-backed rules layer extracted from PDFs
- program philosophy awareness exists more in design docs and selective schema fields than in the full live runtime

### 3. Importer pipeline is still transitional

The design expects a robust program import engine that fully understands:

- weeks
- days
- exercises
- sets
- reps
- RPE
- alternatives

Current state:

- build-time XLSX import exists
- workbook/PDF pairing exists
- importer now emits provenance and diagnostics
- onboarding importer v2 exists for one structured path

But:

- canonical importer v2 is still missing
- the current generic XLSX importer is still transitional and session-oriented rather than final phase/week/day/slot fidelity

### 4. The coaching brain is still narrower than intended

The design target is effectively a deterministic bodybuilding coach.

Current state:

- there is meaningful deterministic coaching scaffolding
- there are coach preview/apply flows
- there are adaptation previews and weekly review outputs

But:

- the broad rulebook from the PDFs is not yet encoded into a mature typed runtime rule engine across the catalog
- missed-workout recovery, fatigue management, progression, and substitution are real but still more modular/provisional than fully unified under the final architecture

### 5. Program timeline fidelity is uneven across the library

The design expects the app to know exactly where the user is in a multi-week authored plan.

Current state:

- week generation and mesocycle context exist
- deload timing exists
- onboarding package blueprints carry stronger timeline structure

But:

- the broader runtime program library still includes older canonical templates and transitional imported artifacts
- library-wide canonical timeline fidelity is not finished

## Direct Response To The Spec's Comparison Checklist

### 1. Program import capability

Assessment: **Yes, but transitional.**

- XLSX import exists.
- PDF ingestion exists.
- Workbook/PDF provenance pairing exists.
- Canonical importer v2 is still missing.

### 2. Exercise metadata system

Assessment: **Partial.**

- Exercise notes, muscles, movement/equipment tags, videos, and substitutions exist.
- A rich centralized exercise database is not yet complete.

### 3. Substitution engine

Assessment: **Yes, partial implementation.**

- Equipment-aware substitution exists.
- UI substitution flow exists.
- Ranking sophistication and knowledge richness can improve.

### 4. Adaptive schedule builder

Assessment: **Yes.**

- Day compression and adaptation exists in engine code and tests.
- This is one of the clearer implemented design pillars.

### 5. Fatigue tracking

Assessment: **Yes, partial implementation.**

- Fatigue score, soreness, adherence, readiness, and deload logic exist.
- The recovery model is still simpler than the intended end state.

### 6. Weak body part prioritization

Assessment: **Yes, partial implementation.**

- Weak areas influence adaptation and weekly review adjustments.

### 7. RPE-based progression

Assessment: **Yes, partial implementation.**

- RPE is logged and used by progression recommendation logic.
- Full doctrine-based RPE/RIR programming logic is still incomplete.

### 8. Program knowledge model

Assessment: **Partial and still the biggest gap.**

- Typed schemas and gold-rule structures exist.
- Full program-philosophy understanding is not yet broadly encoded in the live runtime.

## Most Accurate Characterization Of The Current Product

The app is currently best described as:

**a deterministic hypertrophy training application with a real adaptive engine and meaningful coaching scaffolding, but not yet a fully realized doctrine-backed hypertrophy coach**.

That is more advanced than:

- static workout app
- simple logging tracker
- basic CRUD training diary

But less complete than:

- full professional bodybuilding coach engine
- full program-philosophy-preserving adaptation platform across the whole library

## Most Important Mismatches To Fix Next

If the goal is to bring implementation closer to the design intent as fast as possible, the highest-value remaining work is:

1. canonical importer v2 with full phase/week/day/slot fidelity
2. richer exercise knowledge system and guide content structure
3. broader PDF doctrine to typed rule distillation
4. unified rules-runtime integration for progression/fatigue/deload/transition logic
5. continued dashboard and explanation-surface refinement so the product feels like a coach, not a debug console

## Final Judgment

The external specification is directionally correct about what the product should become.

However, if someone used that spec alone to guess the current repo state, they would likely underestimate what is already implemented.

The current repo already contains:

- real adaptation logic
- real substitution logic
- real progression logic
- real weak-point logic
- real equipment filtering
- real history analytics
- real multi-program selection and generation

The true gap is not whether adaptive hypertrophy systems exist in the codebase.

The true gap is whether those systems have been elevated into the full, knowledge-rich, doctrine-backed, coach-grade architecture described by the design.

That answer is still: **not yet**.