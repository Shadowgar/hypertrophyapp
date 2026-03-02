# Master Plan (Single Source of Truth)

## Product Vision

HypertrophyApp is a deterministic, nutrition-aware, multi-user hypertrophy training platform designed to rival and exceed RP-style workflows while remaining:

- Local-first (self-hosted on Raspberry Pi)
- Deterministic at runtime (no guide search / no runtime ingestion)
- Mobile-first (iPhone Pro Max primary target: Safari/Edge)
- Dark mode default (white text + red accents)
- Deployable via Docker Compose

This file is the single source of truth for scope, phases, and definition of done. Any major scope change must update this file first.

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
  - days/week (2/3/4)
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

# Post-MVP Scope

- Optional last-set RPE support
- Expanded template library
- Advanced substitution trees
- Analytics dashboard
- Volume landmark tracking (MEV/MAV/MRV)
- Deload recommendation wizard
- Program version migration tooling
- Admin UI

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

---

## Phase 0 — Foundation
- [x] Monorepo scaffold
- [x] Docker Compose stack
- [x] API `/health`
- [x] Dark-mode base UI
- [x] Alembic migrations
- [x] Docs baseline

---

## Phase 1 — PDL + Canonical Templates
- [x] Define canonical schema
- [ ] Add movement_pattern field
- [ ] Add equipment_tags field
- [ ] Add substitution metadata field
- [ ] Add video.youtube_url field to exercise schema (canonical PDL)
- [x] Add `notes` field to session exercise slots (template-level notes)
- [x] Add `substitution_candidates` list to exercise slots
- [x] Add deterministic equipment tag parsing fallback (DB/BB/Cable/Machine/BW) in importer/template tooling
- [x] Seed working template
- [ ] Schema validation tests

---

## Phase 2 — Auth + Equipment-Aware Profiles
- [x] JWT auth
- [x] User profile CRUD
- [x] Onboarding wizard
- [ ] Add training location (Gym/Home)
- [ ] Add equipment profile (Dumbbells Only minimum)
- [ ] Profile validation tests

---

## Phase 3 — Weekly Check-In + Nutrition Phase
- [x] Weekly check-in model
- [x] Phase modifiers
- [ ] Validation rules
- [ ] UI implementation
- [ ] Tests

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
- [ ] Resume logic
- [ ] Add “I don’t have this equipment” button
- [x] Add Video action per exercise card that opens video.youtube_url in a new tab
- [x] Display slot `notes` in the exercise card (collapsible)
- [x] Ensure notes persist and remain visible after substitutions
- [ ] Substitution picker modal
- [ ] Persist substitution selection
- [x] Update exercise state correctly
- [ ] Tests

---

## Phase 6 — Weekly Plan Generator (Equipment-Aware)
- [ ] Equipment filtering during generation
- [ ] Substitution pre-filtering
- [ ] Ensure substitution selection is applied at the slot level and logged accordingly
- [ ] Compression logic (2/3/4 days)
- [ ] Muscle coverage validator
- [ ] Deterministic week output tests

---

## Phase 7 — Mesocycle + Deload Logic
- [ ] Mesocycle model
- [ ] Deload support
- [ ] Early deload triggers
- [ ] UI indicator
- [ ] Tests

---

## Phase 8 — Program Library Expansion
- [x] Full Body templates
- [x] PPL templates
- [x] Upper/Lower templates
- [ ] Equipment-safe variants
- [ ] Template selection logic
- [ ] Ensure importers map spreadsheet YouTube links into canonical templates for all supported programs

---

## Phase 9 — Analytics + Trends
- [ ] Exercise trend charts
- [ ] Bodyweight trend
- [ ] Adherence tracking

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

---

# Drift Prevention Rules

- All new features must map to a roadmap phase.
- Substitution engine must remain deterministic.
- No runtime guide parsing ever.
- All core-engine logic must have unit tests.
- This document must be updated before major architectural changes.

---