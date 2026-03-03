# GPT-5-mini Execution Backlog (Safe Takeover)

## Goal
Ship remaining Phase 8/13 UI surfaces without changing locked deterministic contracts.

## Locked Inputs
- API contracts in `docs/GPT5_MINI_HANDOFF.md`
- Model ownership policy in `docs/Master_Plan.md` (`Model Ownership & Quality Routing`)

## Sprint A — Program Selection UX (UI-only)

### Task A1 — API client support
- File: `apps/web/lib/api.ts`
- Add:
  - `ProgramTemplateSummary` type
  - `api.listPrograms()` -> `GET /plan/programs`
  - optional `template_id` param support in `api.generateWeek(templateId?)`
- Acceptance:
  - Type-safe compile
  - No change to existing endpoint paths

### Task A2 — Onboarding program picker
- File: `apps/web/app/onboarding/page.tsx`
- Add:
  - fetch `api.listPrograms()` on load
  - selector for `selected_program_id`
  - include `selected_program_id` in `/profile` payload
- Acceptance:
  - Onboarding saves selected program
  - Existing onboarding flow still works if program fetch fails (fallback to `full_body_v1`)
 
 Status: COMPLETED by Codex — `apps/web/app/onboarding/page.tsx` now fetches `/plan/programs` and persists `selected_program_id`.

### Task A3 — Settings program switcher
- File: `apps/web/app/settings/page.tsx`
- Add:
  - show current `profile.selected_program_id`
  - fetch and render program options
  - save changes through existing `/profile` upsert
- Acceptance:
  - User can change selected program without breaking other profile fields

 Status: COMPLETED by Codex — `apps/web/app/settings/page.tsx` includes program selector and saves via `/profile`.

### Task A4 — Week page override
- File: `apps/web/app/week/page.tsx`
- Add optional override selector using `api.listPrograms()` and call `api.generateWeek(selectedOrUndefined)`
- Acceptance:
  - default button uses server-selected program
  - override path works and still returns week plan

Status: COMPLETED by Codex — `apps/web/app/week/page.tsx` now supports an optional program override and passes template id to `POST /plan/generate-week`.

## Sprint B — Plan Guide Scaffolding (UI route structure)

### Task B1 — Program guide index route
- Add route: `apps/web/app/guides/page.tsx`
- Display available programs from `api.listPrograms()`.

Status: COMPLETED by Codex — `apps/web/app/guides/page.tsx` lists available programs and links to program guide pages.

### Task B2 — Program detail guide route
- Add route: `apps/web/app/guides/[programId]/page.tsx`
- Render text-first placeholders sourced from existing summary fields.

Status: COMPLETED by Codex — program detail route implemented at `apps/web/app/programs/[id]/page.tsx` (naming differs: `/programs/:id`).

 Status: PARTIALLY COMPLETED — a program guide page was added at `apps/web/app/programs/[id]/page.tsx`. Mini may adapt naming to `guides/*` if preferred.

### Task B3 — Exercise guide placeholder route
- Add route: `apps/web/app/guides/[programId]/exercise/[exerciseId]/page.tsx`
- Render deterministic placeholders and link back to program guide.

Status: COMPLETED by Codex — exercise guide route implemented at `apps/web/app/guides/[programId]/exercise/[exerciseId]/page.tsx` and renders text-first exercise details when available in program templates.

Acceptance for Sprint B:
- Routes compile
- No runtime PDF rendering/parsing
- No new backend contract requirements

## Guardrails (Must Follow)
- Do not edit `packages/core-engine/**`.
- Do not edit `apps/api/alembic/**`.
- Do not change auth/security behavior.
- Do not change existing response semantics for locked endpoints.

## Validation per PR

```bash
cd /home/rocco/hypertrophyapp

docker compose exec -T api sh -lc 'cd /app/apps/api && PYTHONPATH=. pytest tests/test_program_catalog_and_selection.py tests/test_profile_schema.py tests/test_workout_resume.py -q'

cd /home/rocco/hypertrophyapp/apps/web
npm run build
```

## Escalation to GPT-5.3-Codex
Escalate immediately if any task requires:
- schema/model changes
- migration changes
- planner behavior changes
- deterministic rule changes
