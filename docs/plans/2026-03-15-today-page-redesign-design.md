# Today Page Redesign — Design

**Date:** 2026-03-15  
**Status:** Design approved; implementation pending  
**Goal:** Mobile-first, iOS-ready Today page: whole-day-at-a-glance list, drill into one exercise at a time. Reduce information overload and clarify copy.

## Doc alignment (no drift)

This design was checked against all active docs so the UI change does not drift from product or architecture:

- **docs/implementation/FORBIDDEN_PATTERNS.md** — UI must not invent coaching prose. Render `rationale` (or backend-emitted guidance) only; no local reason→message maps or humanized codes.
- **docs/implementation/ACTIVE_REMEDIATION_RAIL.md** — Presentation surfaces are rendering-only. Week/today must continue to show authored execution detail from authoritative data. No reintroduction of forbidden residues (e.g. `humanizeCode`, `_PROGRAM_REASON_MESSAGES`).
- **docs/Master_Plan.md**, **docs/current_state_decision_runtime_map.md** — Week/today surfaces show authored execution detail directly (early-set RPE, last-set RPE, technique, rest, substitutions, demo link, tracking loads). Redesign reorganizes *how* it is shown, not *whether*; data still comes from runtime/API.
- **docs/flows/Onboarding_and_Flows.md** — Start Workout, Log Sets, and Substitution flows unchanged: `/today`, `GET /workout/today`, `POST /workout/{id}/log-set`, substitution picker. No API contract changes.
- **docs/Architecture.md** — API/UI layer remains responsible for workout execution and logging; decision engine remains authority for coaching meaning. UI continues to render owner output only.

## Design decisions

- **Primary use:** Mobile browser first; eventual iOS app. Touch targets ≥44pt; navigation suitable for native stack (list → push detail).
- **Pattern:** List-first, then drill into detail (Approach B). No expand-in-place so the list stays scannable and the detail screen maps to a single pushed view on iOS.
- **Session Intent / Between-Set Coach:** Remove the standalone “Session Intent” card. Replace the confusing “Between-Set Coach” block with a single, clear “Do this set” line on the exercise detail screen, using only backend-emitted guidance (no local “unlock within-session load guidance” prose unless the API provides it).

---

## 1. Top of Today (above the list)

- **Header:** “Today” + date (e.g. “Sun, Mar 15”). Sticky optional.
- **Primary action:** One full-width button, min 44pt height: “Load today’s workout” (or “Reload” when already loaded). No “Runner Status” / “API ok” line unless we add a minimal status indicator (e.g. dot) for offline/error.
- **After load:** One line only: session title (e.g. “Arms & weak points”) + total progress (e.g. “0/12 sets” or “3/12 sets”). No Session Intent card, no “Authored day”, “Weak-point slots”, “Open with X sets…”, or pacing/caution paragraphs on this page.
- **Alerts:** When “Sunday review required” or “No workout”, show a single alert block with message + “Go to Check-In” or “Generate week” CTA as today. No duplicate messaging.

---

## 2. Exercise list (whole day at a glance)

- **Structure:** One scrollable list. One row per exercise. Each row is a single tappable target (min 44pt height) that navigates to the exercise detail screen.
- **Per row:** Exercise name (selected variant after swap); sets progress (e.g. “0/3” or “2/3”); optional one-line prescription (e.g. “10–12 reps @ 20 kg”) to avoid crowding. No RPE, technique, rest, or “Authored substitutions” in the list row.
- **Order:** Same as workout.exercises from API.
- **Visual:** Clear separation between rows (e.g. list dividers or cards). Progress can be a small badge or right-aligned text. No telemetry labels (“Exercise Slot”, “status-dot”) in the list; keep the list minimal and scannable.

---

## 3. Exercise detail screen (drill-in)

- **Entry:** Tapping a list row opens the detail screen (new route or full-screen overlay). One back control (button or swipe) to return to the list.
- **Content (in order):**
  1. **Title:** Exercise name (with link to guide if available).
  2. **Prescription:** Sets × rep range @ weight (e.g. “3 sets · 10–12 reps @ 20 kg”).
  3. **Authored execution detail** (from API only): Early-set RPE, last-set RPE, technique, rest, tracking loads, authored substitutions, demo/video link. Rendered in a compact, readable block (e.g. small labels + values). No invented copy; if the API does not send a field, do not show it.
  4. **“Do this set” line:** One line of guidance only. Source: from `live_recommendation` or set feedback `guidance`/`rationale` when present; otherwise from planned rep range and weight (e.g. “Do 10–12 reps @ 20 kg this set”). Remove the phrase “Log the opening set to unlock within-session load guidance” unless the API explicitly provides it; do not invent similar prose.
  5. **Set logging:** Existing log-set control (ExerciseControlModule or equivalent): log completed sets with reps/weight; call `POST /workout/{id}/log-set`; show feedback when returned.
  6. **Actions:** Video (if available), “I don’t have this equipment” (substitution), Notes. Same behavior as today; can be buttons or compact links, min 44pt touch target.
- **After logging a set:** Optionally show the last-logged set and next-set recommendation in a short block (again using only API `guidance`/`rationale`), then keep focus on “Do this set” and next log action.

---

## 4. Copy and guidance (no new coaching prose)

- **Between-set / “Do this set”:** Use only guidance text that comes from the API (`guidance`, `rationale`, or equivalent from `decision_live_workout_guidance` outputs). If none, show the planned prescription for the next set (e.g. “10–12 reps @ 20 kg”). Do not add local phrases like “unlock within-session load guidance” or other explanations that are not in the backend response.
- **Session Intent:** Removed from Today. No replacement card on this page. Optional: later, a single “i” or short tooltip on the session title if we need to explain “Authored day” or intent in one line, still using only backend/authoritative fields.
- **Forbidden:** No `humanizeCode`, no `resolveReadinessLabel`, no local reason→message maps, no fabricated labels (see FORBIDDEN_PATTERNS and ACTIVE_REMEDIATION_RAIL).

---

## 5. Data and API

- No API changes. Continue to use `GET /workout/today`, `POST /workout/{session_id}/log-set`, existing today payload shape, `live_recommendation`, set feedback, and substitution persistence as today.
- Authored execution fields (early-set RPE, last-set RPE, technique, rest, substitutions, demo link, tracking loads) remain rendered from the same API payload; only the layout and placement change (list vs detail).

---

## 6. Out of scope for this redesign

- Week page, Check-In, Settings, History, Onboarding: unchanged by this plan.
- Coaching intelligence panel: remains only on Check-In and Settings; not re-added to Today.
- Soreness modal, recovery “Generate Week and Reload Today”, and Sunday review / Go to Check-In behavior: keep as is.
- Workout summary (post-completion): can stay as a separate card or move to detail; exact placement left to implementation.

---

## 7. What needs to be done (implementation checklist)

1. **Routing / navigation**  
   - Add a detail view (e.g. `/today/[exerciseId]` or in-page state + full-screen detail) so list row tap opens detail and back returns to list. Ensure back is obvious and works with browser history or native-style stack.

2. **Top section**  
   - Implement header (Today + date), single “Load today’s workout” button (min 44pt), one-line session title + total progress after load, and single alert block for Sunday review / no workout with existing CTAs.

3. **Exercise list**  
   - Implement scrollable list of exercises: one tappable row per exercise (name, sets progress, optional one-line prescription), min 44pt height, no Session Intent card, no Between-Set Coach card on this view.

4. **Exercise detail**  
   - Implement detail layout: title, prescription, authored execution block (from API only), single “Do this set” line (API guidance or planned prescription only), set-logging control, Video/Swap/Notes actions. Remove or replace “Log the opening set to unlock within-session load guidance” with API-sourced or neutral prescription copy.

5. **Copy and compliance**  
   - Audit all Today copy: no new coaching prose; no forbidden residues; guidance text only from API. Run ACTIVE_REMEDIATION_RAIL grep checks after implementation.

6. **Tests**  
   - Update Today tests: list visible after load; tap row opens detail; back returns to list; set logging still works; substitution and alerts unchanged. Remove or update assertions that relied on Session Intent card or old Between-Set Coach block. Keep canonical path and authored-detail assertions aligned with current_state and ACTIVE_REMEDIATION_RAIL.

7. **Docs**  
   - After implementation, update ACTIVE_REMEDIATION_RAIL and current_state_decision_runtime_map to state that Today uses list + detail and that Session Intent card is removed; reference this design doc.

---

## 8. Reference

- Approved user goal: **B — Load the workout and see the whole day at a glance (all exercises + progress), then drill into one.**
- Primary use: **mobile browser;** eventual **iOS application.**
- Design discussion: coaching intelligence removed from Today (confirmed in code); Between-Set Coach and Session Intent replaced by one-line “Do this set” on detail and removal of standalone cards.
