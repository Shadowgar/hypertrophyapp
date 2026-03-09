# Exhaustive Project Review - 2026-03-07

## Purpose

This document is a high-detail project-state review intended for another AI system or human architect to evaluate whether the repository is still following the original adaptive coaching rebuild plan.

It is written from the actual repository state on 2026-03-07, not from aspirational product copy.

Primary questions answered:

1. What has actually been implemented?
2. How far along is each master-plan phase?
3. What is still missing?
4. Is the implementation still aligned with the original deterministic coaching plan?
5. How would a real user use the app today?
6. What must happen next for the app to become the intended "AI-like without runtime AI" hypertrophy coach?

## Executive Verdict

The repository is meaningfully advanced beyond a toy MVP, but it is not yet the full deterministic hypertrophy coaching system described in the redesign documents.

Current reality:

- The app already behaves like a usable local-first workout planner and workout runner.
- Onboarding, login/reset, daily workout execution, weekly review, history analytics, guide browsing, program switching, and deterministic preview/apply flows all exist.
- Validation discipline is real: `./scripts/mini_validate.sh` is green as of this review.
- The codebase is strongly aligned with the architectural rule that runtime must not parse raw PDFs/XLSX.
- The project is not yet at the stage where the full coaching doctrine in the reference PDFs has been distilled into a broad typed rules layer and used as the central runtime brain.

Bottom line:

- Master-plan execution completeness: about `57%`.
- Vision completeness relative to "best hypertrophy coach ever": about `35%`.

The difference between those two numbers matters.

Why:

- A lot of UI, workflow, testing, and deterministic scaffolding is already built.
- The deepest knowledge-layer tasks, especially importer v2, PDF-to-rules distillation, and full decision-engine grounding in typed rules, are still incomplete.

## Review Method

This assessment was based on:

- Current code in `apps/api`, `apps/web`, `packages/core-engine`, `importers`, and `programs`.
- Current docs in `docs/`, especially `Master_Plan.md`, `GPT5_MINI_EXECUTION_BACKLOG.md`, `Architecture.md`, `Canonical_Program_Schema.md`, `High_Risk_Contracts.md`, and `Master_Plan_Checkmark_Audit.md`.
- Current validation status from `./scripts/mini_validate.sh`.
- Current route/page/test inventory.

Scoring method for phase percentages:

- `100%` = delivered and validated against the stated goal.
- `75%` = substantial implementation exists, but important gaps remain.
- `50%` = meaningful partial implementation exists.
- `25%` = early foundational work exists, but not enough to call the phase functionally delivered.
- `0%` = not meaningfully started.

Phase percentages below are judgment calls, but they are anchored to repo evidence rather than guesswork.

## Project-Wide Status Snapshot

### Validation Baseline

As of this review:

- API tests: `86 passed`
- Web tests: `28 passed`
- Web build: success
- Full gate: `./scripts/mini_validate.sh` passes

### Surface Inventory

Implemented top-level web routes:

- `/`
- `/login`
- `/reset-password`
- `/onboarding`
- `/today`
- `/week`
- `/history`
- `/settings`
- `/checkin`
- `/guides`
- `/programs/[id]`
- dynamic guide detail routes under `/guides/...`

Implemented API areas:

- health
- auth
- profile
- plan
- workout
- history
- weekly review/check-in
- soreness and body measurements

Implemented major build-time systems:

- XLSX transitional importer
- onboarding package builder v2
- reference corpus ingestion/provenance pipeline
- ingestion quality reporting

Implemented core-engine modules:

- `equipment.py`
- `intelligence.py`
- `onboarding_adaptation.py`
- `progression.py`
- `scheduler.py`
- `warmups.py`

## Phase Completion Percentages

| Phase | Name | Completion | Rationale |
| --- | --- | ---: | --- |
| A | Architecture Audit and Isolation | 100% | Runtime/source boundaries are documented, audited, and test-guarded. |
| B | Canonical Schema and Gold Baseline | 55% | Gold schema assets and stronger validators exist, but schemas are not yet the universal runtime contract. |
| C | Importer and Rule Distillation | 15% | Transitional importer and one onboarding-package path exist; canonical importer v2 and broad PDF rule distillation do not. |
| D | Deterministic Decision Engine | 35% | Deterministic adaptation/progression pieces exist, but not yet as a complete typed-rules runtime. |
| E | Gold End-To-End Runtime Flow | 60% | Program selection, workout generation, logging, review, and some adaptation are live; the gold-rule path is not the sole runtime brain yet. |
| F | Scale and Harden | 55% | Validation, archive hygiene, tests, history UX, and drift control are solid; broad migration and production hardening remain. |
| G | Onboarding Reliability and Parity | 82% | Onboarding funnel, recovery, autosave, and key parity slices are delivered; parity edge cases remain. |

Derived rollups:

- Master-plan execution completeness: `57%`
- Product usability completeness for a serious internal MVP: about `70%`
- Deterministic coaching-brain completeness: about `30-35%`

## Phase-By-Phase Assessment

## Phase A - Architecture Audit and Isolation

### Status

`100% complete`

### What is done

- The repo has explicit architecture docs describing runtime/build-time separation.
- Runtime does not parse raw `reference/*.pdf` or `reference/*.xlsx` in request paths.
- Runtime does not depend on `docs/guides/generated/*.md`.
- Runtime-boundary tests exist.
- Reference-pair/provenance paths are treated as informational/build-time, not runtime coaching logic.

### Evidence

- `docs/Architecture.md`
- `docs/High_Risk_Contracts.md`
- `docs/Master_Plan_Checkmark_Audit.md`
- `apps/api/tests/test_runtime_source_boundaries.py`

### Remaining work

- No major remaining work in this phase beyond maintaining discipline as new features are added.

## Phase B - Canonical Schema and Gold Baseline

### Status

`55% complete`

### What is done

- Gold template schema exists: `AdaptiveGoldProgramTemplate`.
- Gold rules schema exists: `AdaptiveGoldRuleSet`.
- Onboarding package schema exists: `ProgramOnboardingPackage`.
- User overlay/frequency adaptation schema exists.
- Cross-field validators have been strengthened.
- Negative-path tests now exist for onboarding package integrity.
- One gold program template exists.
- One gold rules file exists.
- One gold onboarding package exists.

### Evidence

- `apps/api/app/adaptive_schema.py`
- `apps/api/tests/test_adaptive_gold_schema_contract.py`
- `apps/api/tests/test_program_onboarding_contract.py`
- `programs/gold/adaptive_full_body_gold_v0_1.json`
- `docs/rules/gold/adaptive_full_body_gold_v0_1.rules.json`
- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json`

### What is not done

- There is not yet one unified, final canonical schema that the full runtime clearly uses for all template/catalog/rules/user-state concerns.
- Exercise catalog schema exists in pieces but is not yet the universal live runtime source for all generated programs.
- User training-state schema is still spread across SQLAlchemy models, API payloads, and engine structures rather than cleanly formalized into one final canonical contract family.
- Gold baseline assets exist, but the entire runtime is not yet driven exclusively from those assets and their typed rules.

### Remaining work

- Finalize canonical program-template schema for full runtime use, not just gold validation.
- Finalize exercise-catalog schema and ensure runtime exercise knowledge is sourced from it consistently.
- Finalize typed coaching-rules schema beyond the initial gold sample.
- Formalize user-state schema for progression/fatigue/adherence/stall state in a more explicit contract layer.
- Add more negative/ambiguity validation cases across all canonical artifact types.

## Phase C - Importer and Rule Distillation

### Status

`15% complete`

### What is done

- Transitional XLSX importer exists and is build-time only.
- Importer sanitizes structural rows.
- Importer maps YouTube links deterministically.
- Importer now emits explicit `import_diagnostics` warnings instead of silently failing in several ambiguity cases.
- Importer retains `source_workbook` provenance.
- A separate onboarding importer v2 exists for one-program onboarding package generation.
- Reference corpus ingestion/provenance pipeline exists.
- Ingestion quality report exists.

### Evidence

- `importers/xlsx_to_program.py`
- `importers/xlsx_to_onboarding_v2.py`
- `importers/reference_corpus_ingest.py`
- `importers/ingestion_quality_report.py`
- `apps/api/tests/test_xlsx_to_program_sanitization.py`
- `apps/api/tests/test_xlsx_to_program_video_mapping.py`
- `apps/api/tests/test_reference_corpus_ingestion.py`
- `apps/api/tests/test_ingestion_quality_report.py`

### What is not done

- The repository does not yet have the canonical importer v2 described in the redesign docs.
- Workbook parsing is still session-oriented transitional output, not a robust canonical phase/week/day/slot emitter.
- Warmup/work-set fidelity is not comprehensively preserved from workbook sources in the general transitional importer.
- No broad, production-grade ambiguity/error-reporting contract exists for all workbook failure modes.
- PDF-derived doctrine is not broadly distilled into typed rule objects.
- Rule-source provenance links are not yet complete at scale.

### Remaining work

- Build canonical importer v2 that outputs phase/week/day/slot structure.
- Preserve authored warmups, set types, reps, effort targets, load targets, notes, and videos more faithfully.
- Add ambiguity severity levels and fail-fast behavior for unrecoverable imports.
- Emit canonical quality reports for importer v2 outputs.
- Build PDF doctrine extraction workflow that creates typed rule objects.
- Link each rule to source sections/metadata.
- Expand beyond one gold rule file.

## Phase D - Deterministic Decision Engine

### Status

`35% complete`

### What is done

- Deterministic frequency adaptation exists for onboarding packages.
- Coaching preview endpoints exist.
- Specialization and phase-application flows exist.
- Exercise-state progression updates happen on set logging.
- Weekly review calculates readiness and adjustment outputs.
- Workout summary logic exists.
- Program recommendation and switching logic exists.

### Evidence

- `packages/core-engine/core_engine/onboarding_adaptation.py`
- `packages/core-engine/core_engine/progression.py`
- `packages/core-engine/core_engine/intelligence.py`
- `apps/api/app/routers/plan.py`
- `apps/api/app/routers/workout.py`
- `apps/api/app/routers/profile.py`
- `apps/api/tests/test_program_frequency_adaptation_api.py`
- `apps/api/tests/test_plan_intelligence_api.py`
- `packages/core-engine/tests/test_onboarding_adaptation.py`
- `packages/core-engine/tests/test_progression.py`
- `packages/core-engine/tests/test_intelligence.py`

### What is not done

- The runtime is not yet clearly driven by a complete typed coaching-rules runtime loaded from canonical rule objects.
- Underperformance, stalls, deload triggers, substitution policy, and phase transitions are not yet obviously unified under one final explainable rules engine architecture.
- A large amount of current behavior is deterministic and useful, but still heuristic/provisional relative to the redesign target.

### Remaining work

- Implement rules-runtime layer that consumes canonical typed rule objects.
- Route progression, fatigue, deload, and transition decisions through that rules layer.
- Persist explainable rationale on every meaningful adjustment, not only selected preview/apply flows.
- Expand deterministic decision tests to more scenario families.

## Phase E - Gold End-To-End Runtime Flow

### Status

`60% complete`

### What is done

- Users can create accounts, persist profile data, and choose a program.
- Users can generate a week.
- Users can retrieve today's workout.
- Users can log sets.
- Users get exercise-state updates and workout summaries.
- Users can run weekly review/check-in.
- Users can preview/apply some adaptation decisions.
- History and guide views support understanding prior performance and planned exercise context.

### Evidence

- `apps/web/app/onboarding/page.tsx`
- `apps/web/app/login/page.tsx`
- `apps/web/app/week/page.tsx`
- `apps/web/app/today/page.tsx`
- `apps/web/app/checkin/page.tsx`
- `apps/web/app/settings/page.tsx`
- `apps/web/app/history/page.tsx`
- `apps/web/app/guides/...`
- `apps/api/app/routers/*`
- web/API tests under `apps/web/tests` and `apps/api/tests`

### What is not done

- The flow is not yet a gold-sample-only end-to-end deterministic coaching runtime grounded primarily in the final canonical rules architecture.
- Program generation is still driven by current canonical templates and logic, not the full intended doctrine-backed coaching layer.
- Next-workout adaptation exists in pieces, but not yet as the fully explainable coaching engine envisioned by the redesign.

### Remaining work

- Fully wire gold sample template + rules into end-to-end runtime path.
- Make next-session adaptation driven by final typed rules, not provisional heuristics.
- Persist and surface rationale consistently across the full user flow.
- Expand user-facing explanation surfaces so the app behaves more like a real coach and less like a JSON-backed planner.

## Phase F - Scale and Harden

### Status

`55% complete`

### What is done

- Imported template variants have been moved to archive paths for audit instead of runtime selection.
- Validation gate is real and green.
- Regression coverage is broad for current implemented surfaces.
- History/calendar training view is delivered.
- Drift review discipline exists.
- Build/runtime boundary checks exist.

### Evidence

- `programs/archive_imports/README.md`
- `apps/api/tests/*`
- `apps/web/tests/*`
- `scripts/mini_validate.sh`
- `docs/Master_Plan_Checkmark_Audit.md`

### What is not done

- Library-wide migration to canonical importer/rules pipeline is not done.
- Scenario coverage is good but not exhaustive for all adaptation edge cases.
- Security hardening and offline sync are documented contracts more than fully delivered product systems.
- Release gate for the full target product is not yet satisfied.

### Remaining work

- Migrate more programs into canonical v2 structures.
- Expand scenario and regression suite for progression/fatigue/deload/substitution.
- Implement more of the security/offline/auth-expansion roadmap.
- Build production-grade recovery, backup, and rate-limit verification flows where still only documented.

## Phase G - Onboarding Reliability and Parity

### Status

`82% complete`

### What is done

- Multi-step onboarding funnel exists.
- Onboarding persists profile and questionnaire answers.
- Onboarding supports program selection and weak-area input.
- Auth failure handling is explicit.
- Dev wipe/reset support exists.
- Password reset flow exists.
- Browser-local onboarding draft autosave/restore exists.
- First-plan bootstrap is wired.

### Evidence

- `apps/web/app/onboarding/page.tsx`
- `apps/web/app/login/page.tsx`
- `apps/web/app/reset-password/page.tsx`
- `apps/api/app/routers/auth.py`
- `apps/api/app/routers/profile.py`
- `apps/api/tests/test_auth_password_reset.py`
- `apps/web/tests/onboarding.error.test.tsx`
- `apps/web/tests/onboarding.program.test.tsx`

### What is not done

- Screenshot/reference parity translation is only partial.
- Some parity edge cases and long-tail onboarding states are still missing.
- The onboarding experience is functionally solid, but not clearly at the final visual/behavioral parity target from all reference materials.

### Remaining work

- Finish parity checklist conversion and implementation.
- Cover edge-case branches and more reference-derived steps where still deferred.
- Improve polish and reduce remaining developer-oriented language in user-facing flows.

## Is The Repo Still Following The Original Plan?

## Short Answer

Yes, but unevenly.

## Strong alignment points

- The repo still strongly respects the deterministic runtime boundary.
- Runtime still aims to use structured templates and rule-like deterministic logic rather than freeform runtime AI.
- Testing, validation, and explainability are treated as serious engineering requirements.
- Gold assets and schema hardening work are moving in the direction described by the plan.

## Drift from the intended order

The project has also advanced significant user-facing UX before fully completing the knowledge layer.

That means:

- onboarding
- history
- settings/intelligence UX
- program switching
- workout runner

are ahead of:

- canonical importer v2
- broad rule distillation from PDFs
- fully grounded rules runtime

This is not a fatal plan violation, but it is a sequencing deviation.

Interpretation:

- Good news: the product is testable and usable now.
- Risk: polish can create the illusion that the central coaching brain is further along than it actually is.

The most important architectural truth is this:

The app is currently a strong deterministic workout application with early adaptive-coaching capabilities, not yet the full doctrine-backed hypertrophy coaching engine envisioned by the redesign.

## User-Facing Product Review

## What a real user can do today

### 1. Land on the home page

The user can:

- go to login
- go to password reset
- start onboarding
- jump to today's workout

The home page is simple and acts more like a launcher than a finished dashboard.

### 2. Create an account or log in

Returning users:

- use `/login`
- enter email and password
- token is stored locally
- redirect goes to `/today` unless another `next` path is provided

Users who forgot a password:

- use `/reset-password`
- request a reset token
- in dev/no-email environments the token can be displayed directly
- submit token + new password
- redirect back to login

### 3. Complete onboarding

First-time users go through `/onboarding`.

Current flow:

- intro slides
- one-question-per-step questionnaire
- optional skips on selected non-critical questions
- name/account step
- optional program selection
- optional weak-area entry
- account creation or login
- profile save
- first plan generation attempt
- redirect to `/today`

The onboarding collects practical training context such as:

- gender
- goal
- height
- weight
- birthday
- training age
- frequency
- motivation
- obstacle
- training location
- gym setup
- experience level
- preferred workout duration
- days available

Important reliability features:

- local draft autosave/restore
- dev wipe-by-email
- dev wipe-current-user-data
- password reset request shortcut

### 4. Pick a program

There are currently multiple ways to influence or choose program selection.

During onboarding:

- the user can choose a program from visible catalog options

In settings:

- the app fetches a deterministic program recommendation
- the user can see a reason for the recommendation
- the user can manually switch to a compatible program
- switching uses a confirmation step

In week generation:

- the user can override the server-selected program for that generated week

In guide browsing:

- the user can browse available guide programs and inspect days/exercises

Important current limitation:

- program selection exists, but the catalog is still a mixture of active canonical runtime templates and work-in-progress gold/canonical migration work.
- this is not yet the fully doctrine-backed program-selection experience implied by the long-term vision.

### 5. Generate a week

The user goes to `/week`.

They can:

- optionally choose a program override
- generate the week
- see raw plan output
- use the coaching-intelligence panel from that screen

Current product truth:

- week generation works
- output presentation is still developer-heavy because the page exposes raw JSON-like output instead of a final polished planning UI

### 6. Open today's workout

The user goes to `/today`.

The page currently supports:

- loading the most relevant session for today or a resumable unfinished session
- seeing workout title/date
- deload and mesocycle context
- daily quote
- resume status
- progress status
- per-exercise execution controls
- live feedback as sets are logged
- substitutions
- notes toggles
- soreness gating before workout load
- workout summary after completion

This is one of the strongest parts of the shipped app.

### 7. Know what exercises to do

From a user perspective, the current ways to know what to do are:

- `/today`: primary execution screen with actual exercises for the current session
- guide links from exercises when available
- `/guides`: browse programs and open day/exercise guides
- `/history`: inspect what was planned/performed previously

The user does not yet get the full final "coach explains everything like a world-class hypertrophy system" experience.

Current state is better described as:

- the app can tell the user what to do today
- the app can provide some exercise/guide context
- the app can show completion and progression data
- the app does not yet fully expose the deep doctrinal reasoning that the long-term design intends

### 8. Log sets and progress through the workout

On `/today`, the user can:

- complete sets
- send `log-set` requests
- see live recommendation updates
- keep progress state
- resume unfinished workouts later
- get day summary feedback

This is already meaningful training workflow functionality, not just placeholder UI.

### 9. Perform weekly review/check-in

On `/checkin`, the user can:

- see whether Sunday review is required
- inspect previous-week lift audit summary
- update bodyweight and nutrition targets
- submit adherence score and notes
- receive adaptive output including readiness score and exercise overrides

This is an important bridge between raw workout logging and higher-level adaptive behavior.

### 10. Inspect history and trends

On `/history`, the user can:

- view analytics
- view recommendation timeline
- inspect calendar-style training history
- switch between week/month windows
- filter by completion/program/muscle
- inspect missed days with planned detail
- inspect PR-marked days
- jump to previous same weekday
- compare same-weekday deltas

This is one of the clearest recent signs that the product is moving from basic logging toward coaching context.

### 11. Adjust settings and preview intelligence behavior

On `/settings`, the user can:

- view profile context
- view recommendation reason
- switch programs
- preview coaching adjustments
- preview/apply frequency adaptation
- preview/apply phase or specialization decisions
- wipe current user data

Current limitation:

- this screen is powerful but still fairly operator/developer-oriented.
- it exposes the scaffolding of the adaptation system rather than a polished consumer-grade coaching UX.

## What The App Is Today Versus What It Is Supposed To Become

## Today

The app is:

- a deterministic workout planner
- a workout runner
- a logging and review tool
- an early adaptive-coaching platform with previews and some applied decisions
- a strong engineering scaffold for a larger coaching system

## Intended future state

The app is supposed to become:

- a deterministic hypertrophy coach that encodes workbook structure and PDF doctrine into typed, explainable logic
- a system that uses the knowledge in the reference folder at build time to create runtime coaching intelligence
- a product that feels AI-like to the user because it adapts, explains, remembers, and personalizes, even though it is not using runtime LLM improvisation for core coaching decisions

## Critical clarification

The original plan does **not** support a runtime model that simply "reads the PDFs" and improvises coaching.

The intended path is:

- parse and structure knowledge at build time
- convert doctrine into explicit rules
- run deterministic algorithms at runtime
- surface explanations and adaptive behavior that feel coach-like

That is the correct "AI-like without actually being AI" interpretation for this repo.

## Current Gaps Between That Vision And Current Reality

- The reference knowledge is not yet broadly distilled into canonical typed rules.
- The importer does not yet fully preserve canonical workbook structure at the final target fidelity.
- The current coaching logic is not yet fully equivalent to "the best hypertrophy coach ever" encoded into transparent deterministic rules.
- Much of the UX exists, but the deepest knowledge engine is still under construction.

## Exhaustive Remaining Work List

This section is intentionally long and direct.

## Foundational schema and knowledge-layer work still remaining

- finalize canonical runtime schemas for all template/rules/catalog/user-state concerns
- unify transitional and canonical artifact formats where they still diverge
- define final canonical exercise knowledge contract and use it consistently
- formalize user-state contract for progression, fatigue, adherence, stall, and adaptation state
- broaden negative validation coverage

## Importer work still remaining

- build real importer v2 for canonical phase/week/day/slot extraction
- preserve authored warmups more faithfully
- preserve work-set types (`work`, `top`, `backoff`) where present
- preserve `rest_seconds`, `load_target`, effort targets, and notes more fully
- support multi-phase and multi-week authored structures instead of flat transitional sessions
- emit stronger ambiguity diagnostics and fail-fast behavior for invalid workbooks
- generate canonical importer-quality reports in the final intended format
- migrate additional workbooks through the new importer path

## PDF/rules-layer work still remaining

- define full typed doctrine-to-rules schema set
- extract more than one gold rules artifact
- connect rules to explicit source sections/metadata
- add rule simulation tests
- integrate rule provenance into explainability surfaces

## Decision-engine work still remaining

- replace provisional heuristics with rules-runtime-backed decision making where still provisional
- unify progression, fatigue, deload, underperformance, and transition decisions in one coherent engine
- persist rationale on all meaningful adaptations
- support more realistic hypertrophy-specialization logic across the broader catalog
- add stronger scenario coverage for stalls, low readiness, deload, rejoin windows, substitutions, and weak-point specialization

## End-to-end runtime work still remaining

- make gold sample the clean reference path for end-to-end deterministic runtime
- connect weekly review outputs more directly to future generated sessions
- improve explainability surfaces in user-facing pages
- move raw plan/debug-style output toward polished guided UX
- expose more rationale for why a particular exercise/day/program was chosen

## Scale-out migration work still remaining

- migrate additional archived imported programs into canonical runtime-ready structures
- rationalize remaining active program catalog against future canonical set
- expand guide coverage and guide richness
- improve provenance and auditability across migrated programs

## Hardening work still remaining

- broaden regression coverage for full adaptation scenarios
- implement more of the documented offline-sync contract
- implement more of the documented security hardening contract
- implement more of the documented auth-expansion contract if that remains in scope
- validate backup/restore/failure drill procedures against real implementation, not only design docs

## Onboarding/product-parity work still remaining

- finish remaining onboarding parity items from screenshot/reference analyses
- reduce developer-oriented messaging in user-facing screens
- improve finished-product polish for login/onboarding/settings/week pages
- build more explicit in-app program discovery and program-comparison flows

## Coaching-experience work still remaining

- make the app feel more like a real hypertrophy coach and less like a planner with debug overlays
- provide clear explanation of session intent and exercise purpose
- give users better reasons for progression, substitutions, deloads, and specialization shifts
- connect history, weekly review, and next-session planning more visibly

## Best-Case Interpretation For Another AI Reviewer

If another AI is evaluating whether the current implementation is on-plan, the correct interpretation is:

- The architecture is still fundamentally on-plan.
- The UX and workflow scaffolding are ahead of the deepest knowledge-layer work.
- The repository has strong deterministic discipline and validation rigor.
- The biggest remaining gap is not front-end plumbing; it is the coaching knowledge layer.

The most accurate one-sentence summary is:

This repository is already a capable deterministic workout application with meaningful adaptive scaffolding, but it is still early-to-middle stage in the transformation into a full doctrine-backed hypertrophy coaching system.

## Recommended Next Execution Order

If strict adherence to the original plan matters most, the next work should prioritize:

1. canonical importer v2 with phase/week/day/slot fidelity
2. broader typed rules distillation from PDFs
3. rules-runtime integration for progression/fatigue/deload/transition logic
4. end-to-end gold-sample runtime path using those canonical assets
5. then scale catalog migration and consumer-grade UX refinement

If product usability matters most, the current app is already quite usable for internal or advanced local testing, but that should not be confused with completion of the core coaching mission.

## Appendix A - Shipped Web Surface Inventory

### Core routes

- `/` home launcher
- `/login` password login
- `/reset-password` request/confirm reset
- `/onboarding` multi-step onboarding funnel
- `/today` current workout runner
- `/week` week generation screen
- `/history` analytics + calendar + coaching timeline
- `/settings` profile/program/intelligence/adaptation controls
- `/checkin` weekly review flow
- `/guides` guide index
- `/guides/[programId]` guide detail
- `/guides/[programId]/phase/[phaseId]` phase guide
- `/guides/[programId]/phase/[phaseId]/day/[dayIndex]` day guide
- `/guides/[programId]/exercise/[exerciseId]` exercise guide
- `/programs/[id]` program guide detail

### Key web test coverage

- onboarding happy path
- onboarding error handling
- history analytics
- history calendar
- settings program selection
- settings intelligence flow
- week generation override
- today runner
- today log-set
- today substitution
- route snapshots

## Appendix B - Shipped API Surface Inventory

### Health

- `GET /health`

### Auth

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/dev/wipe-user`
- `POST /auth/password-reset/request`
- `POST /auth/password-reset/confirm`

### Profile / weekly review / recovery

- `GET /profile`
- `POST /profile`
- `GET /profile/program-recommendation`
- `POST /profile/program-switch`
- `POST /weekly-checkin`
- `GET /weekly-review/status`
- `POST /weekly-review`
- soreness CRUD
- body-measurement CRUD
- `POST /profile/dev/wipe`

### Planning / guides / intelligence

- `GET /plan/programs`
- `GET /plan/guides/programs`
- `GET /plan/guides/programs/{program_id}`
- `GET /plan/guides/programs/{program_id}/days/{day_index}`
- `GET /plan/guides/programs/{program_id}/exercise/{exercise_id}`
- `GET /plan/intelligence/recommendations`
- `POST /plan/intelligence/apply-phase`
- `POST /plan/intelligence/apply-specialization`
- `POST /plan/intelligence/coach-preview`
- `POST /plan/adaptation/preview`
- `POST /plan/adaptation/apply`
- `POST /plan/generate-week`

### Workout execution

- `GET /workout/today`
- `POST /workout/{workout_id}/log-set`
- `GET /workout/{workout_id}/progress`
- `GET /workout/{workout_id}/summary`

### History

- `GET /history/exercise/{exercise_id}`
- `GET /history/weekly-checkins`
- `GET /history/analytics`
- `GET /history/calendar`
- `GET /history/day/{day}`

## Appendix C - Current Active Program Asset Picture

Active runtime templates in `programs/`:

- `full_body_v1.json`
- `ppl_v1.json`
- `upper_lower_v1.json`

Gold artifacts:

- `programs/gold/adaptive_full_body_gold_v0_1.json`
- `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json`
- `docs/rules/gold/adaptive_full_body_gold_v0_1.rules.json`

Archived imported artifacts remain for audit in `programs/archive_imports/`.

## Final Conclusion

The repository is not drifting into chaos. It has a coherent architecture, strong test discipline, and a real implemented product surface.

But if the success standard is:

"the app has absorbed the hypertrophy knowledge from the spreadsheets and manuals and now behaves like a best-in-class deterministic hypertrophy coach"

then that standard has not been met yet.

The core coaching-knowledge transformation is still the biggest unfinished body of work.

The correct strategic posture is:

- preserve the strong shipped UX and test baseline
- stop pretending the coaching brain is finished
- aggressively complete importer v2, rules distillation, and rules-runtime integration
- then scale the catalog and polish the consumer experience

That is the fastest path to making the product truly feel "AI-like" without betraying the original deterministic design philosophy.