# Master Plan (Single Source of Truth)

## Product Vision

Rocco's HyperTrophy Plan is a deterministic, nutrition-aware, multi-user hypertrophy training platform designed to rival and exceed RP-style workflows while remaining:

- Local-first (self-hosted on Raspberry Pi)
- Deterministic at runtime (no guide search / no runtime ingestion)
- Mobile-first (iPhone Pro Max primary target: Safari/Edge)
- Dark mode default (white text + red accents)
- Deployable via Docker Compose

This file is the single source of truth for scope, phases, and definition of done. Any major scope change must update this file first.

---

# UI Design System — Hyperdrive OS Layer

## Design Philosophy

- Training Operating System: interfaces must prioritize execution speed, clarity, and deterministic user actions.
- Minimal cognitive load: one primary action focus per panel; secondary actions grouped and de-emphasized.
- Data-dense but clean: compact information grouping with strict typography hierarchy and spacing rhythm.
- Subtle depth, restrained glow: depth cues are structural, not decorative.
- Red accent reserved for state + power indicators only.

## Visual Language

- Ultra-dark matte background as the base surface.
- Frosted glass layered panels for grouped controls and data modules.
- Soft elevation shadows with low spread and low opacity for panel separation.
- Thin red accent outlines with a 1–2px maximum stroke width.
- Controlled glow is allowed only for:
  - active set
  - PR detection
  - recovery warning
- Green/Yellow/Red are reserved strictly for performance state signaling.

## Mode-Based Interface Architecture

- WORKOUT MODE
- PLAN MODE
- ANALYTICS MODE
- BODY MODE
- SYSTEM MODE

Layout density and panel structure may shift by mode, but component behavior and state semantics must remain deterministic and consistent across modes.

## Workout Runner UI Specification

- Exercise Control Module layout: exercise header, primary metrics block, set stack, and action row.
- Large working weight display as the dominant numeric element in each exercise module.
- Rep range displayed adjacent to working weight using fixed formatting.
- Collapsible warmups hidden by default after first completion, with deterministic expand/collapse state.
- Stacked working sets with clear current-set emphasis and completed-set state markers.
- Action row order is fixed: Video | Swap | Notes | Rest.
- Auto rest timer trigger starts immediately on set completion.
- Subtle pulse on set completion for confirmation feedback.
- Deterministic performance color state based on logged outcomes and recovery flags.

## Analytics Dashboard Specification

- Strength graph styling: thin white trend line with red peak highlights.
- Mesocycle vertical markers rendered as low-contrast separators at deterministic interval boundaries.
- Volume per muscle heat map using normalized weekly set volume buckets.
- Body measurement trend overlays aligned on shared date axis with bodyweight context.
- PR markers rendered as explicit point annotations for rep PR and weight PR events.

## Micro-Interaction Rules

- No heavy animations.
- Only CSS transforms and opacity transitions for interactive feedback.
- GPU-safe transitions only; avoid CPU-heavy paint patterns.
- No 3D libraries.
- 60fps target on iPhone Safari.

## Performance Constraints

- No large animation libraries.
- No particle systems.
- Minimal blur layers; limit concurrent frosted panels per viewport.
- Avoid layout thrashing by preventing repeated reflow-triggering patterns.
- All animations must complete under 200ms.

## Reference Visual Parity Program (Premium Finish)

Goal: make production screens visually align with the Hyperdrive reference aesthetic while preserving deterministic UX and mobile performance.

### Visual Parity Targets

- Multi-layer depth system with explicit material hierarchy (base matte shell, glass panel, elevated module, active highlight).
- Cinematic but restrained lighting: edge highlights, radial passes, controlled bloom, subtle vignette, low-opacity streaks.
- Instrument-grade module composition: dense but readable metrics, status pips, compact HUD rows, clear action rails.
- Tight typographic hierarchy: consistent title/body/label scales, fixed spacing rhythm, deterministic alignment grid.
- Premium command dock: stronger active/inactive contrast, consistent iconography, deterministic state semantics per mode.

### Design Token Expansion (Required)

- Define 4–6 depth tiers for shadow/glow treatment.
- Define glass opacity tiers for shell/card/module overlays.
- Define edge-highlight tiers for inactive/hover/active states.
- Define red accent intensity tiers (idle, active, warning, PR).
- Define state color tiers (green/yellow/red) reserved for performance signals only.

### Component Overhaul Scope (Required)

- Inputs, selects, textareas, and toggles adopt layered glass + inner border treatment.
- Buttons and segmented controls adopt deterministic active/pressed/disabled material states.
- Card primitives adopt shell/module variants with consistent padding, radius, and border logic.
- Bottom navigation dock adopts premium active indicator behavior and icon/text balance.
- Exercise control surfaces standardize metric emphasis, row rhythm, and action-rail hierarchy.

### Cinematic Shell Scope (Required)

- Add ambient matte background grain/noise at low opacity.
- Add subtle radial light passes with strict opacity ceilings.
- Add constrained vignette and edge illumination layers for depth framing.
- Keep all cinematic effects CSS-based and GPU-safe.

### Information Density & Dashboard Scope

- Add compact telemetry modules for weekly volume, progression, readiness, and body metrics.
- Standardize micro-widgets (status dots, sparkline framing, module headers, metric labels).
- Enforce deterministic module order per mode.

### Motion & Interaction Scope

- Transition duration budget: 120–200ms.
- Use opacity/transform only for interactive feedback.
- Add subtle glow ramp for active controls and completion events.
- Add deterministic press/focus feedback for all primary controls.

### Iconography & Framing Scope

- Use one consistent icon family/weight across command surfaces.
- Enforce mobile-first frame composition for screenshot parity (iPhone Pro Max first).
- Preserve accessibility contrast and tap target requirements while matching aesthetic goals.

### Visual Acceptance Criteria

- Side-by-side screenshot review shows clear parity in depth, hierarchy, accent behavior, and dock language.
- Onboarding, Today, Week, Check-In, History, Guides, and Settings share one coherent material system.
- Active/idle/warning states are visually distinct and semantically consistent.
- No performance regressions on mobile target (maintain current interaction smoothness).
- No deterministic behavior changes in planner/workout logic due to UI work.

---

## Product Goal

Deliver a deterministic hypertrophy planner + workout runner that can compete with RP-style hypertrophy apps while staying local-first, mobile-first, and Raspberry Pi deployable.

---

## Non-Negotiables

- **Runtime determinism:** no guide search, no PDF/XLSX parsing in runtime services.
- **Build-time only knowledge:** guide knowledge is converted into canonical templates + deterministic rules.
- **Multi-user onboarding** captures profile, split, days/week, nutrition phase, calories/macros, AND equipment availability.
- **Engine outputs** weekly plans, warmups, substitution-safe exercises, and next-weight recommendations.
- **Exposure-based progression** handles missed days, rolls priority lifts forward, prevents skipped muscles.
- **No RPE required:** reps-only logging must fully work (optional RPE may be added later).
- **Local-first:** no cloud dependency required for core features.

---

## Locked Technology Stack

Frontend:
- Next.js (App Router) + React + TypeScript
- Tailwind CSS + shadcn/ui
- PWA enabled
- Dark mode default theme

Backend:
- FastAPI (Python) + Pydantic
- JWT Auth

Database:
- PostgreSQL

Deployment:
- Docker Compose + Caddy reverse proxy

Platform:
- Raspberry Pi 5 / Ubuntu 24.04 LTS (ARM64)

---

## Runtime Constraints (Hard Rules)

- The runtime app must never parse or query PDFs/XLSX.
- The runtime app must never search guides or use embeddings/vector retrieval.
- The runtime app must never depend on OpenClaw to function.
- All program logic must execute from canonical templates in `/programs/` plus deterministic code rules.

---

## Reference Intelligence System (Next-Gen)

### Corpus Coverage (Current Repository)

- Reference corpus currently includes approximately:
  - 43 PDF files
  - 13 XLSX files
  - 1 EPUB file
- Program families present in corpus names include:
  - Pure Bodybuilding (Full Body + Phase 2 variants)
  - PowerBuilding 3.0
  - PPL systems
  - Upper/Lower systems
  - Essentials (3x/4x/5x)
  - Fundamentals, Muscle Ladder, Nutrition, Technique, Guidebooks

### Product Requirement

- Every reference file in `/reference/` must be represented in-app through deterministic derived artifacts.
- Representation may be via structured metadata, canonical program objects, normalized guide text, summaries, and provenance references.
- Runtime determinism remains mandatory: no live PDF/XLSX parsing at request time.

### Build-Time Ingestion Architecture

Create deterministic ingestion pipeline modules in `/importers/` that:

1. Scan all assets in `/reference/` and register each file in an asset catalog.
2. Extract spreadsheet structure into canonical program/session/exercise schema.
3. Extract PDF/EPUB instructional text into normalized section documents.
4. Emit deterministic outputs:
   - `/programs/*.json` for runtime planning
   - `/docs/guides/*.md` for plan/exercise guides
   - `/docs/reference/index.json` for provenance index
5. Validate output checksums and schema correctness in CI.

### Program Catalog + Selection UX

- Add Program Catalog pages with cards for all imported programs (Pure Bodybuilding variants, PowerBuilding, PPL, etc.).
- Each program card must include:
  - intended level
  - frequency options
  - progression style
  - equipment assumptions
  - mesocycle length
- User selects start program during onboarding.
- User can switch program later in settings with deterministic migration rules.

### Plan Guide Pages (Text-First)

For each program, phase, session, and exercise slot, generate in-app text guide pages:

- Program overview guide
- Phase/mesocycle guide
- Day/session execution guide
- Exercise execution guide (warmups, working sets/reps, intensity techniques, rest rules, cues, substitutions)

Guides must render deterministic text artifacts; no embedded PDF rendering is required.

### Deterministic Progression to Next Program

- Engine may suggest program/phase advancement using explicit thresholds (adherence, progression stalls, mesocycle completion, recovery markers).
- Engine must not auto-switch programs without explicit user confirmation.

### Content Rights / Safety Handling

- Keep raw source files local in `/reference/`.
- API/UI should serve normalized instructional artifacts and provenance references, not bulk raw source document dumps.
- Prefer structured data + concise summaries over long verbatim copyrighted excerpts.

---

## Repository Structure

/apps/web  
/apps/api  
/packages/core-engine  
/programs  
/importers  
/reference  
/infra  
/docs  

---

# MVP Scope

- Auth: register/login (JWT)
- Onboarding profile:
  - name
  - age
  - weight
  - gender
  - units
  - experience level
  - split preference
  - days/week (2/3/4/5)
  - nutrition phase
  - calories/macros
  - training location (Gym/Home)
  - equipment profile (minimum support: Dumbbells Only)
- Weekly check-in (phase + calories/macros + bodyweight)
- Deterministic week plan generation from `/programs/` templates
- Equipment-aware plan generation
- Workout runner:
  - today endpoint
  - reps-only logging
  - resume workout
  - substitution button (“I don’t have this equipment”)
- Deterministic substitution engine
- Exercise history endpoint + simple trend charts
- Mobile-first screens
- Docker Compose deployment
- Core-engine unit tests for progression, warmups, substitution logic, week generation
- Program catalog selection + plan guide pages (text-first, deterministic)

## Authentication Methods

- Current (implemented): Email + Password (JWT)
- Planned (non-MVP):
  - Google OAuth login
  - Apple Sign In
  - Passkey login (WebAuthn)

Authentication expansion must preserve deterministic runtime behavior and local-first operation for core training features.

## Physique & Recovery Tracking (MVP-Level)

- Body measurement tracking (user-defined measurements + pre-seeded defaults)
- Deterministic measurement trend graphs
- Bodyweight overlay on physique trends
- “What’s sore today?” quick pre-workout input
- Exercise-level notes display in workout runner
- Exercise video button support when template metadata includes links

---

# Equipment & Substitution System (Core Requirement)

## User Equipment Context

User must select:

- Gym (full equipment)
- Home (minimum: dumbbells only; expandable later)

Equipment profile must filter available exercises during week generation.

---

## Deterministic Substitution Engine

Each exercise must include:

- movement_pattern  
  (horizontal_press, vertical_press, horizontal_pull, vertical_pull, squat, hinge, lunge, calf_raise, lateral_raise, curl, triceps_extension, etc.)

- primary_muscles (array)

- equipment_tags  
  (barbell, dumbbell, machine, cable, bodyweight, band, rack, bench, etc.)

- difficulty_class (optional)

Substitution Algorithm (Deterministic):

1. Filter by available equipment
2. Match exact movement pattern
3. Score by primary muscle overlap
4. Prefer template-defined substitutions
5. Return top 3–5 options

---

## Substitution Mapping Rules (Name Parsing + Template Overrides)

### Goal
Ensure substitutions are tied to the intended “main exercise” slot, while supporting equipment-aware selection and consistent logging.

### Canonical Model Requirements
Each exercise slot in a session must support:

- `primary_exercise_id` (the default exercise for that slot)
- `substitution_candidates` (ordered list of exercise IDs)
- `notes` (string, may include cues/tempo/intensity technique details)

The workout runner must always display the slot-level `notes` (even if a substitution is chosen), and may also show exercise-level notes if present.

### Deterministic Substitution Tie-In
When a user selects **“I don’t have this equipment”**, the substitution is applied to the **slot** (not globally). The slot retains:
- progression state link for that exposure
- notes/intention
- movement pattern + primary muscle intent

### Name Parsing Heuristic (Deterministic, Limited)
Templates/importers may auto-tag equipment based on exercise name tokens:

- If exercise name contains `DB`, `D.B.`, or `Dumbbell` → add `equipment_tags: ["dumbbell"]`
- If contains `BB`, `Barbell` → add `equipment_tags: ["barbell"]`
- If contains `Cable` → add `equipment_tags: ["cable"]`
- If contains `Machine` → add `equipment_tags: ["machine"]`
- If contains `BW`, `Bodyweight` → add `equipment_tags: ["bodyweight"]`

This heuristic is used only as a fallback. If the spreadsheet/template provides explicit equipment tags, those override parsing.

### Acceptance Criteria
- Substitutions are tied to the exercise slot (not free-floating).
- Selecting a substitute does not lose the original slot intent.
- `DB` in a name correctly tags the exercise as dumbbell-based (unless overridden).
- Exercise notes are visible during the workout at the point of performance.

User may select substitute during workout.

Substitution must preserve:
- movement pattern
- primary muscle intent
- progression continuity

No AI required. No guide search.

---

# Recovery & Soreness Tracking System (Deterministic)

## Input Model

- Pre-workout soreness input modal before session start
- Muscle list with severity per muscle:
  - None
  - Mild
  - Moderate
  - Severe

## Deterministic Adjustment Rules

- Severe: reduce working load slightly OR reduce one working set OR suggest lower joint-stress substitute
- Moderate: apply minimal adjustment only
- Mild: log only (no loading change)
- Rules must be deterministic, explicit, and testable
- System must never rewrite the full plan automatically

## Acceptance Criteria

- [x] Soreness input is captured pre-workout with deterministic severity values
- [x] Per-muscle soreness entries persist and are available to workout generation/recommendation logic
- [x] Severe soreness triggers only deterministic, bounded recommendation adjustments
- [x] Moderate soreness applies minimal deterministic adjustment
- [x] Mild soreness is logged without automatic loading changes
- [x] No automatic full-plan rewrite occurs from soreness input
- [x] Core-engine tests verify soreness-to-recommendation behavior

---

# Exercise Video Links (YouTube) (Core Requirement)

## Goal

Every exercise shown in the app should support an optional YouTube link so users can quickly view form/reference videos.

## Data Source

Video links are provided in canonical templates/imported program data and stored as part of exercise metadata.

## Canonical Data Model

Each exercise object supports:

- `video.youtube_url` (optional string)

If missing, UI should not render a video action.

## Runtime UX

- Workout runner shows a `Video` action on each exercise card when `video.youtube_url` exists.
- Tapping `Video` opens the link in a new browser tab.
- No runtime lookup/search is performed.

## Acceptance Criteria

- Video links are available in canonical schema and templates.
- Workout UI conditionally renders video action per exercise.
- Clicking video action opens external YouTube URL in new tab.
- Missing links do not create UI errors.

---

# Physique & Analytics Dashboard

- Strength trend graphs (weight over time)
- Rep performance trends
- Bodyweight trend graph
- Body measurement trends
- Volume per muscle weekly tracking
- PR detection (rep PR + weight PR)
- Adherence tracking (% completed sessions)
- Mesocycle markers on charts
- Deterministic calculations only (no runtime AI/guide parsing)

---

# Post-MVP Scope

- Optional last-set RPE support
- Expanded template library
- Advanced substitution trees
- Analytics dashboard
- Volume landmark tracking (MEV/MAV/MRV)
- Deload recommendation wizard
- Program version migration tooling
- Admin UI
- Full reference vault explorer (all source assets + provenance graph)

---

# Explicitly Out of Scope (MVP)

- PDF/XLSX runtime ingestion
- Vector retrieval
- Runtime LLM planning
- OpenClaw runtime dependency
- Social features
- Cloud dependency

---

# Definition of Done (MVP)

- `docker compose up --build` runs successfully on ARM64
- Web UI reachable
- API health endpoint responds
- Auth/profile/checkin/plan/workout/history endpoints functional
- Deterministic progression engine verified
- Deterministic substitution engine verified
- Equipment filtering functional
- 2/3/4 day compression logic works
- Dark-mode mobile UI polished
- Documentation accurate

---

# Roadmap (Phases + Checklists)

## Codex 5.3 Critical Burn-Down (Before Quota Exhaustion)

Purpose: prioritize the highest-risk items that benefit most from GPT-5.3-Codex before usage reaches 100% and work shifts to GPT-5-mini support mode.

### Priority A — Must Be Codex-Owned Now

- [x] Deterministic soreness modifier integration in generation/recommendation path (Phase 6)
- [x] Weekly volume-per-muscle computation + muscle coverage validator with deterministic tests (Phase 6)
- [x] Mesocycle state model + deload lifecycle + early-deload trigger rules + test matrix (Phase 7)
- [x] Program/template selection engine correctness (including equipment-safe variant selection) (Phase 8)
- [x] Reference ingestion architecture: deterministic PDF/EPUB/XLSX normalization + provenance index + checksum stability tests (Phase 13)
- [x] Deterministic “next recommended program” logic + switch confirmation semantics (Phase 13)

### Priority B — Codex Should Own If Time Allows

- [x] API contracts for guide retrieval and plan guide drill-down pathways (Phase 13)
- [ ] Offline queue/replay conflict semantics and deterministic sync rules (Phase 10)
- [ ] Security/hardening architecture: secrets strategy, rate limiting approach, backup/restore design and drills (Phase 11)
- [ ] Auth expansion architecture for OAuth + Passkey (WebAuthn) flows (Phase 12)

### Priority C — Safe for GPT-5-mini (After Codex Direction)

- [ ] Hyperdrive visual parity implementation tasks that do not alter deterministic behavior (Phase 14)
- [ ] Non-critical UI refinements, static content, docs cleanup, and screenshot parity checklists
- [ ] Test fixture expansion and visual regression snapshot maintenance

### Codex Exit Criteria (Before Handoff to Mini-Only Execution)

- [x] All Priority A architecture decisions merged with tests
- [ ] High-risk contracts documented (engine rules, ingestion schema, API invariants)
- [ ] Mini handoff pack updated with explicit do/do-not-change boundaries for deterministic logic

---

## Phase 0 — Foundation
- [x] Monorepo scaffold
- [x] Docker Compose stack
- [x] API `/health`
- [x] Dark-mode base UI
- [x] Alembic migrations
- [x] Docs baseline
- [x] Define UI design tokens (colors, spacing, glow intensity)
- [x] Define glass layer CSS system

---

## Phase 1 — PDL + Canonical Templates
- [x] Define canonical schema
- [x] Add movement_pattern field
- [x] Add equipment_tags field
- [x] Add substitution metadata field
- [x] Add video.youtube_url field to exercise schema (canonical PDL)
- [x] Add `notes` field to session exercise slots (template-level notes)
- [x] Add `substitution_candidates` list to exercise slots
- [x] Add deterministic equipment tag parsing fallback (DB/BB/Cable/Machine/BW) in importer/template tooling
- [x] Seed working template
- [x] Schema validation tests

---

## Phase 2 — Auth + Equipment-Aware Profiles
- [x] JWT auth
- [x] Login method (email/password)
- [x] Password reset flow (request reset + confirm reset)
- [x] User profile CRUD
- [x] Onboarding wizard
- [x] Profile UX location (`/onboarding` for initial setup, `/settings` for review/edit)
- [x] Add training location (Gym/Home)
- [x] Add equipment profile (Dumbbells Only minimum)
- [x] Profile validation tests

---

## Phase 3 — Weekly Check-In + Nutrition Phase
- [x] Weekly check-in model
- [x] Phase modifiers
- [x] Add soreness input model + CRUD
- [x] Add body measurement model + CRUD
- [x] Validation rules
- [x] UI implementation
- [x] Tests

---

## Phase 4 — Core Engine v1
- [x] Warmup engine
- [x] Progression engine
- [x] Exposure tracking
- [x] Phase modifiers
- [x] Unit tests

---

## Phase 5 — Workout Runner + Substitution UX
- [x] Workout instance generation
- [x] Reps logging
- [x] Resume logic
- [x] Add soreness modal before workout start
- [x] Add notes display per exercise
- [x] Add Video button per exercise
- [x] Implement Exercise Control Module UI
- [x] Implement rest timer auto-start + subtle pulse animation
- [x] Implement Video | Swap | Notes action row styling
- [x] Add “I don’t have this equipment” button
- [x] Add Video action per exercise card that opens video.youtube_url in a new tab
- [x] Display slot `notes` in the exercise card (collapsible)
- [x] Ensure notes persist and remain visible after substitutions
- [x] Substitution picker modal
- [x] Persist substitution selection
- [x] Update exercise state correctly
- [x] Tests

---

## Phase 6 — Weekly Plan Generator (Equipment-Aware)
- [x] Equipment filtering during generation
- [x] Substitution pre-filtering
- [x] Ensure substitution selection is applied at the slot level and logged accordingly
- [x] Compression logic (2/3/4 days)
- [x] Ensure soreness modifiers apply deterministically to recommendations
- [x] Track weekly volume per muscle
- [x] Muscle coverage validator
- [x] Deterministic week output tests

---

## Phase 7 — Mesocycle + Deload Logic
- [x] Mesocycle model
- [x] Deload support
- [x] Early deload triggers
- [x] UI indicator
- [x] Tests

---

## Phase 8 — Program Library Expansion
- [x] Full Body templates
- [x] PPL templates
- [x] Upper/Lower templates
- [x] Equipment-safe variants
- [x] Template/program selection logic
- [x] Onboarding program picker (required)
- [x] Settings program switcher (required)
- [x] Program catalog API + UI cards
- [x] Program explanation summaries per catalog item
- [ ] Ensure importers map spreadsheet YouTube links into canonical templates for all supported programs

---

## Phase 13 — Reference Corpus Intelligence + Plan Guides
- [x] Build asset catalog covering every file in `/reference/`
- [x] Add deterministic PDF/EPUB extraction pipeline (build-time)
- [x] Add deterministic XLSX extraction pipeline (build-time)
- [x] Emit normalized guide docs into `/docs/guides/`
- [x] Emit provenance index (`asset -> section -> derived entity`)
- [x] Add API endpoints for program/day/exercise guides
- [ ] Add web Plan Guide pages (Program → Phase → Day → Exercise)
- [x] Add workout runner drill-down to exercise guide text
- [x] Add deterministic “next recommended program” suggestion logic
- [x] Add explicit confirmation flow before program/phase switch
- [x] Add ingestion determinism tests (checksum + schema stability)
- [x] Add guide coverage tests (no orphan assets)

---

## Phase 9 — Analytics + Trends
- [ ] Exercise trend charts
- [ ] Bodyweight trend
- [ ] Adherence tracking
- [ ] Add strength trend charts
- [ ] Add body measurement charts
- [ ] Add PR detection logic
- [ ] Add adherence tracking dashboard
- [ ] Implement analytics dashboard visual system
- [ ] Add PR highlight styling
- [ ] Add volume heat map styling

---

## Phase 10 — Offline Reliability
- [ ] Offline logging queue
- [ ] Replay mechanism
- [ ] Sync status UX

---

## Phase 11 — Hardening
- [ ] Backups
- [ ] Restore procedures
- [ ] Secrets management
- [ ] Rate limiting
- [ ] Failure drills

---

## Phase 12 — Advanced Enhancements
- [ ] Optional RPE support
- [ ] MEV/MAV/MRV tracking
- [ ] Deload wizard
- [ ] OpenClaw advisory layer
- [ ] Google OAuth login
- [ ] Apple Sign In login
- [ ] Passkey login (WebAuthn)

---

## Phase 14 — Hyperdrive Visual Parity (App-Wide Premium UI)
- [ ] Expand design tokens for depth/glow/glass/accent tiers
- [ ] Implement shell material tiers (base, glass, elevated, active)
- [ ] Implement cinematic background layers (grain, radial pass, vignette)
- [ ] Overhaul form controls (input/select/textarea/toggle) with unified material language
- [ ] Overhaul button and segmented-control interaction states
- [ ] Overhaul card primitives (shell/module variants + deterministic spacing grid)
- [ ] Upgrade command dock contrast, active markers, and icon consistency
- [ ] Standardize typography scale/weights/line-height/letter-spacing across routes
- [ ] Standardize telemetry micro-widgets (status dots, metric labels, module headers)
- [ ] Upgrade Today runner composition to closer HUD parity
- [ ] Upgrade Onboarding composition and hierarchy to match premium finish
- [ ] Upgrade Week/Check-In/History/Guides/Settings to same material hierarchy
- [ ] Add analytics visual module polish (sparklines, PR highlights, compact charts)
- [ ] Add motion polish pass (120–200ms, transform/opacity only)
- [ ] Add iconography consistency pass for all nav/action surfaces
- [ ] Capture screenshot parity checklist for key screens (before/after)
- [ ] Add web visual regression snapshots for critical routes
- [ ] Validate no performance regression on mobile target
- [ ] Validate no deterministic behavior changes from UI refactor

---

# Model Ownership & Quality Routing

Use model routing to maximize quality while keeping throughput high.

## GPT-5.3-Codex (Primary for Critical Engineering)

GPT-5.3-Codex owns implementation and review for high-risk and architecture-sensitive work:

- Core engine logic (`packages/core-engine`) and deterministic planning rules
- API contract changes, migrations, auth, security-sensitive flows
- Program ingestion architecture, canonical schema evolution, import validation
- Workout runner state logic, substitution correctness, progression behavior
- Refactors affecting multiple services or cross-layer coupling
- Final code review/acceptance for any production-facing feature

## GPT-5-mini (Support for Low-Risk Throughput Work)

GPT-5-mini may handle bounded, low-risk tasks with strict guardrails:

- Drafting documentation sections and checklist updates
- UI copy improvements and non-critical content edits
- Boilerplate page scaffolds that do not change core business logic
- Test skeletons and fixture setup (must be reviewed before merge)
- Data normalization scripts where output is validated by schema tests

## Mandatory Quality Gates

- Any change touching planner determinism, auth, data models, or migrations requires GPT-5.3-Codex implementation or final review.
- Any GPT-5-mini code contribution must pass automated tests and then receive GPT-5.3-Codex review before acceptance.
- Runtime behavior changes require updated tests in API/core-engine/web as applicable.
- No merge if model ownership is unclear for a changed area.

## Default Assignment Rule

- If uncertain, route the task to GPT-5.3-Codex.
- GPT-5-mini is opt-in for scoped support tasks only.

## Operational Handoff Docs

- `docs/GPT5_MINI_HANDOFF.md` (locked contracts + allowed scope)
- `docs/GPT5_MINI_EXECUTION_BACKLOG.md` (ordered mini task plan)
- `docs/GPT5_MINI_RUNBOOK.md` (execution + validation + failure handling)
- `docs/GPT5_MINI_BOOTSTRAP_PROMPT.md` (session-start prompt for mini)
- `scripts/mini_preflight.sh` + `scripts/mini_validate.sh` (automation guardrails)

---

# Drift Prevention Rules

- All new features must map to a roadmap phase.
- Substitution engine must remain deterministic.
- No runtime guide parsing ever.
- All core-engine logic must have unit tests.
- This document must be updated before major architectural changes.

---