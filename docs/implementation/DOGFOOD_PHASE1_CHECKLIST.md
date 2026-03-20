# Full-Body Canonical Paths — Dogfood Checklist

Last updated: 2026-03-20

Use this checklist to verify the administered full-body canonical paths end-to-end on desktop and mobile (or viewport resize). Fix only blockers that prevent completing the loop; log issues with steps-to-reproduce for follow-up.

## Prerequisites

- API running: `cd apps/api && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Web running: `cd apps/web && npm run dev`
- Optional: Docker Compose up for API + DB, then use app at `http://<host>:18080/`

## Steps

1. **Log in** with a local test account (register if needed).
2. **Reset to clean Phase 1**
   - Call `POST /profile/dev/reset-phase1` with auth header, or
   - Onboarding → Developer Tools → "Reset Current User to Clean Phase 1".
3. **Generate week** — Week page or API: `POST /plan/generate-week`. Expect 5 sessions, program ID `pure_bodybuilding_phase_1_full_body`.
4. **Today** — Open Today page. Workout should auto-load when API health OK. Verify:
   - Session title and progress line visible.
   - List of exercises; tap one to open detail overlay.
   - Authored execution detail present (RPE, rest, substitutions, demo link, etc.).
   - "Do this set" line from API guidance only (no fabricated prose).
5. **Log a set** — In Today detail, log at least one set (reps/weight). Confirm success and any guidance/feedback from API.
6. **Weekly check-in** — Check-In page: submit weekly check-in (body weight, adherence, sleep, stress, pain flags).
7. **Weekly review** — Submit weekly review. Expect status "review_logged".
8. **History** — Open History; confirm current week appears; click a day to see detail.
9. **Frequency adaptation** — Settings or API: `POST /plan/adaptation/apply` with e.g. `target_days: 3`, `duration_weeks: 2`. Then regenerate week: `POST /plan/generate-week`. Expect 3 sessions and continuity with same program ID.
10. **Training state** — `GET /profile/training-state`. Confirm `user_program_state.program_id` is `pure_bodybuilding_phase_1_full_body` and session ID has same prefix.

## Validation

- **Desktop:** Complete steps 1–10 in one pass.
- **Mobile (or narrow viewport):** Repeat steps 1–10; note any layout, tap target, or loading issues.
- **Done when:** Loop completes at least once on desktop and once on mobile; blockers (if any) are listed with steps-to-reproduce for Step 2 (fix dogfood blockers).

## Dogfood Run Log

### Run 1 — 2026-03-16 (Desktop, Docker Compose at localhost:18080)

| Step | Result | Notes |
| --- | --- | --- |
| 1. Register | PASS | Onboarding → Create Account with `dogfood@test.com`, program `pure_bodybuilding_phase_1_full_body`, weak areas `chest, hamstrings`. Account created and redirected to Today page. |
| 2. Reset Phase 1 | SKIPPED | Fresh account — no reset needed. |
| 3. Generate week | PASS | Onboarding auto-generated week. Full Body #1 loaded with 12 exercises, 34 total sets. |
| 4. Today | PASS | Session title ("Full Body #1 · 0/34 sets"), date, exercise list visible. Exercise detail overlay shows authored prescription, substitutions, demo link, set guidance. |
| 5. Log a set | PASS | Logged 10 reps @ 44.1 lbs on Half Kneeling 1 Arm Lat Pulldown. Counter updated to 1/3. Coaching feedback appeared: "Keep the same load for the remaining sets and match the programmed rep target." |
| 6. Weekly check-in | PASS | Filled bodyweight 180 lbs, auto-populated nutrition (2600 kcal / 180g P / 70g F / 280g C), adherence 4/5. |
| 7. Weekly review | PASS | Review saved. Adaptive output: readiness 65, `progressive_overload_ready`, volume shift -1, load scale 0.931. |
| 8. History | PASS | History page loaded with all sections (calendar, progression brief, strength trend, bodyweight trend, PR highlights, readiness mix, volume heat map). Data sparse (expected for fresh account). |
| 9. Generate next week | PASS | "Generate Next Week Now" button on Check-In page worked. "Next week generated." message confirmed. |
| 10. Frequency adaptation / training state | NOT TESTED | Deferred to next run. |

### Run 2 — 2026-03-20 (API multi-week runtime evidence, local pytest)

| Scenario | Result | Evidence |
| --- | --- | --- |
| Phase 2 week-5 generation | PASS | `tests/test_program_catalog_and_selection.py::test_phase2_generate_week_uses_week_five_before_transition` |
| Phase 2 week-5 -> week-6 transition checkpoint | PASS | `tests/test_program_catalog_and_selection.py::test_phase2_generate_week_week_five_to_six_transition_is_checkpoint` |
| Phase 2 interruption + resume + week-10 continuity | PASS | `tests/test_program_catalog_and_selection.py::test_phase2_generate_week_supports_interruption_and_resume_and_week_ten` |
| Time-budget behavior across Phase 2 block transition | PASS | `tests/test_program_catalog_and_selection.py::test_phase2_time_budget_compression_applies_across_block_transition` |
| Movement restrictions on rotated weeks | PASS | `tests/test_program_catalog_and_selection.py::test_phase2_movement_restrictions_remain_enforced_on_rotated_weeks` |

Command:
`PYTHONPATH=/home/rocco/hypertrophyapp/packages/core-engine python3 -m pytest tests/test_program_catalog_and_selection.py::test_phase2_generate_week_uses_week_five_before_transition tests/test_program_catalog_and_selection.py::test_phase2_generate_week_week_five_to_six_transition_is_checkpoint tests/test_program_catalog_and_selection.py::test_phase2_generate_week_supports_interruption_and_resume_and_week_ten tests/test_program_catalog_and_selection.py::test_phase2_time_budget_compression_applies_across_block_transition tests/test_program_catalog_and_selection.py::test_phase2_movement_restrictions_remain_enforced_on_rotated_weeks`

Result: `5 passed in 10.02s`.

### Observed Issues (non-blocking)

1. **Uniform starting loads**: All 12 exercises show identical 44.1 lbs starting load regardless of exercise type (lat pulldown vs belt squat vs skull crusher). Expected: per-exercise default loads based on movement pattern. **Severity**: Coaching quality — not a blocker but reduces first-week realism.
2. **Soreness form re-appears on exercise click**: After skipping the soreness form, clicking an exercise button sometimes resurfaces it. The form intercepts clicks on the exercise list. **Severity**: UX friction — requires two "Skip" taps before accessing exercises.
3. **Bottom nav intercepts scroll-area clicks**: The fixed bottom navigation bar overlaps the lower portion of the page content, intercepting click targets (Skip button, last exercises). **Severity**: UX friction — scrollIntoView needed to reach targets.
4. **Check-In nav link doesn't navigate from Today page**: Clicking "Check-In" in the bottom nav while the exercise detail overlay is open doesn't navigate away. Direct URL navigation works. **Severity**: Minor UX friction.

## Known follow-ups / technical debt

- **Post-onboarding login propagation is slow**: after completing onboarding and seeing the success state, the user may hit the login screen and need to wait a minute or two before credentials are accepted. Root cause appears to be a delay between registration/onboarding completion and the auth path being ready; tighten this so that login works immediately after onboarding.
- **Uniform starting loads** (from Run 1): Per-exercise default starting loads should be movement-pattern-aware instead of a flat default.
- **Soreness form re-trigger** (from Run 1): Once dismissed, the soreness form should not resurface during the same session.
- **Bottom nav z-index / safe area** (from Run 1): Page content should have bottom padding equal to nav height to prevent click interception.

## Reference

- API smoke test covering this path: `apps/api/tests/test_phase1_canonical_path_smoke.py`
- Local loop description: `docs/Master_Plan.md` § Local Dogfood Loop (Canonical Path)
