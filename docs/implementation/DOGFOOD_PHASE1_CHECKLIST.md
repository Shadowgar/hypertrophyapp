# Phase 1 Canonical Path — Dogfood Checklist

Last updated: 2026-03-16

Use this checklist to verify the administered Pure Bodybuilding Phase 1 path end-to-end on desktop and mobile (or viewport resize). Fix only blockers that prevent completing the loop; log issues with steps-to-reproduce for follow-up.

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

## Known follow-ups / technical debt

- **Post-onboarding login propagation is slow**: after completing onboarding and seeing the success state, the user may hit the login screen and need to wait a minute or two before credentials are accepted. Root cause appears to be a delay between registration/onboarding completion and the auth path being ready; tighten this so that login works immediately after onboarding.

## Reference

- API smoke test covering this path: `apps/api/tests/test_phase1_canonical_path_smoke.py`
- Local loop description: `docs/Master_Plan.md` § Local Dogfood Loop (Canonical Path)
