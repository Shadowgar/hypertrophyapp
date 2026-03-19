# Phase 1 Canonical Path — Dogfood Run Checklist

Use this as your **personal, check-off** run sheet while dogfooding the administered **Pure Bodybuilding Phase 1** path (desktop + mobile).

Reference source: `docs/implementation/DOGFOOD_PHASE1_CHECKLIST.md`

## Run metadata

- Date:
- Environment: (Docker `:18080` / local dev / remote)
- Account/email:
- Device: (Desktop / Mobile)
- Notes:

## Prerequisites

- [x ] API running (or Docker stack up)
- [ x] Web running
- [x ] Can log in successfully

## Desktop loop (do in order)

- [ x] **1) Log in** (register if needed)
- [ x] **2) Reset to clean Phase 1**
  - [ ] Option A: `POST /profile/dev/reset-phase1` (authed)
  - [x ] Option B: Onboarding → Developer Tools → **Reset Current User to Clean Phase 1**
- [x ] **3) Generate week** (`POST /plan/generate-week` or Week page)
  - [x ] Program ID is `pure_bodybuilding_phase_1_full_body`
  - [ x] Sessions generated (doc expectation: 5)
- [ x] **4) Today page validation**
  - [ x] Workout auto-loads when API health OK
  - [ x] Session title + progress line visible
  - [ x] Exercise list renders
  - [ x] Tap an exercise → overlay opens
  - [ x] Authored execution details visible (as applicable): technique, rest, RPE, substitutions, demo/video link, notes
  - [ x] “Do this set” guidance is from API (no fabricated prose)
- [ x] **5) Log at least one set**
  - [x ] Log reps + weight
  - [x ] Completed-set counter updates
  - [ x] Guidance/feedback appears (if provided)
- [x ] **6) Weekly check-in**
  - [x ] Submit check-in (body weight, adherence, sleep, stress, pain flags)
- [ ] **7) Weekly review**
  - [ ] Submit weekly review
  - [ ] Status becomes `review_logged`
- [ ] **8) History**
  - [ ] History loads
  - [ ] Current week appears
  - [ ] Click a day → see exercise/session details
- [ ] **9) Frequency adaptation continuity**
  - [ ] `POST /plan/adaptation/apply` (example: target_days=3, duration_weeks=2)
  - [ ] Regenerate week (`POST /plan/generate-week`)
  - [ ] Sessions match target days (e.g., 3)
  - [ ] Program ID continuity preserved (`pure_bodybuilding_phase_1_full_body`)
- [ ] **10) Training state continuity**
  - [ ] `GET /profile/training-state`
  - [ ] `user_program_state.program_id == pure_bodybuilding_phase_1_full_body`
  - [ ] Session IDs share the same program prefix (continuity)

## Mobile / narrow viewport loop (repeat)

- [ ] Repeat steps **1–10** on mobile (or narrow viewport)
- [ ] No major layout issues (overlay header reachable, buttons tappable, scroll works)

## Done criteria

- [ ] Desktop loop completed end-to-end
- [ ] Mobile loop completed end-to-end
- [ ] Any blockers captured with steps-to-reproduce (below)

## Issues / blockers log

For each issue, fill in:
- **Title**:
- **Severity**: blocker / high / medium / low
- **Where**: (Onboarding / Week / Today / Overlay / Check-In / History / Settings)
- **Steps to reproduce**:
- **Expected**:
- **Actual**:
- **Screenshots/logs**:

