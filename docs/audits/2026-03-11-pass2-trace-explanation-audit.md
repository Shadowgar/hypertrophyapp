# 2026-03-11 Pass 2 Trace + Explanation Audit

Scope audited only:

- `packages/core-engine/core_engine/decision_progression.py`
- `packages/core-engine/core_engine/decision_weekly_review.py`
- `packages/core-engine/core_engine/decision_program_recommendation.py`
- `packages/core-engine/core_engine/decision_frequency_adaptation.py`
- `packages/core-engine/core_engine/decision_coach_preview.py`
- `packages/core-engine/core_engine/decision_workout_session.py`
- `packages/core-engine/core_engine/decision_live_workout_guidance.py`
- `apps/web/app/today/page.tsx`
- `apps/web/app/week/page.tsx`
- `apps/web/app/history/page.tsx`
- `apps/web/components/coaching-intelligence-panel.tsx`
- `apps/web/app/settings/page.tsx`
- `apps/web/app/checkin/page.tsx`
- `apps/web/lib/api.ts`

Authority used:

- `docs/architecture/GOVERNANCE_CONSTITUTION.md`
- `docs/architecture/TRUST_AND_MATURITY_MODEL.md`
- `docs/audits/2026-03-11-pass1-authority-audit.md`

Focus only:

- trace completeness
- explanation integrity

## Trace coverage verdict

No scoped decision family reaches `full trace`.

| Decision family | Trace coverage | Meets minimum valid `decision_trace` standard? | Why |
| --- | --- | --- | --- |
| `decision_progression.py` | `no meaningful trace` | `No` | Core owner outputs return decisions without `decision_trace`: `evaluate_schedule_adaptation()` emits schedule tradeoffs only, `recommend_progression_action()` emits action/reason only, and `recommend_phase_transition()` emits phase/reason only. Human-readable rationale is generated separately by `humanize_progression_reason()` and `humanize_phase_transition_reason()` instead of being emitted from a valid trace. See `packages/core-engine/core_engine/decision_progression.py:163-232`, `packages/core-engine/core_engine/decision_progression.py:235-279`, and `packages/core-engine/core_engine/decision_progression.py:434-566`. |
| `decision_weekly_review.py` | `partial trace` | `No` | The family does emit structured traces on summary and decision paths, especially `summarize_weekly_review_performance()` and `interpret_weekly_review_decision()`, but those traces still stop at `inputs` / `steps` / `outcome`. They do not carry constitution-equivalent `owner_family`, explicit `policy_basis`, `alternative_resolution`, or bounded `trust_scope`. See `packages/core-engine/core_engine/decision_weekly_review.py:591-654` and `packages/core-engine/core_engine/decision_weekly_review.py:715-913`; compare against the minimum standard in `docs/architecture/GOVERNANCE_CONSTITUTION.md:92-117`. |
| `decision_program_recommendation.py` | `partial trace` | `No` | Candidate resolution and final recommendation both emit traces, but the trace contract is still thin. `resolve_program_recommendation_candidates()` only records ordered IDs and compatibility mode, and `recommend_program_selection()` records steps plus the selected program, yet neither trace explains policy basis or why losing alternatives lost beyond step booleans. See `packages/core-engine/core_engine/decision_program_recommendation.py:65-97` and `packages/core-engine/core_engine/decision_program_recommendation.py:380-430`. |
| `decision_frequency_adaptation.py` | `partial trace` | `No` | Preview/apply traces exist, but they only summarize request context and aggregate outcomes. The actual week-level adaptation logic comes back from `adapt_onboarding_frequency()` while the trace records only counts such as `week_count` and `rejoin_policy`. No alternative resolution, policy basis, or trust scope is emitted. See `packages/core-engine/core_engine/decision_frequency_adaptation.py:40-117`, `packages/core-engine/core_engine/decision_frequency_adaptation.py:120-214`, and `packages/core-engine/core_engine/decision_frequency_adaptation.py:247-323`. |
| `decision_coach_preview.py` | `partial trace` | `No` | The preview family has the richest top-level trace in scope, but it still falls short of the constitutional minimum. `_coach_preview_trace()` captures inputs, delegated step results, and `outputs`, yet does not emit a constitution-equivalent reason summary, alternative resolution, or trust scope. Apply traces have the same pattern. See `packages/core-engine/core_engine/decision_coach_preview.py:698-767`, `packages/core-engine/core_engine/decision_coach_preview.py:770-876`, and `packages/core-engine/core_engine/decision_coach_preview.py:376-469`. |
| `decision_workout_session.py` | `partial trace` | `No` | The family emits many route and response traces, but most are orchestration traces around data loading, response shaping, and nested traces. Core state mutation like `resolve_workout_session_state_update()` still returns no trace at all, and the route traces do not provide a family-level policy basis or alternative resolution. See `packages/core-engine/core_engine/decision_workout_session.py:96-190`, `packages/core-engine/core_engine/decision_workout_session.py:318-385`, `packages/core-engine/core_engine/decision_workout_session.py:996-1055`, and `packages/core-engine/core_engine/decision_workout_session.py:1266-1462`. |
| `decision_live_workout_guidance.py` | `partial trace` | `No` | This family consistently emits traces for feedback, live adjustment, hydration, and summary guidance, but the traces are still `inputs` / `steps` / `outcome` only. They omit explicit policy basis, alternative resolution, and trust scope, and `hydrate_live_workout_recommendation()` even leaves `steps` empty. See `packages/core-engine/core_engine/decision_live_workout_guidance.py:76-108`, `packages/core-engine/core_engine/decision_live_workout_guidance.py:137-179`, `packages/core-engine/core_engine/decision_live_workout_guidance.py:182-261`, `packages/core-engine/core_engine/decision_live_workout_guidance.py:264-315`, and `packages/core-engine/core_engine/decision_live_workout_guidance.py:388-430`. |

## Trace-specific findings

### 1. `decision_progression.py` is still the clearest trace failure in this pass

Classification:

- trace coverage: `no meaningful trace`
- minimum-valid standard: `fails`

Why:

- The family owns progression action, phase transition, readiness derivation, and schedule adaptation decisions, but its core owner functions emit no `decision_trace` at all. See `packages/core-engine/core_engine/decision_progression.py:163-232` and `packages/core-engine/core_engine/decision_progression.py:434-566`.
- It also authors human-readable rationale strings outside a trace contract through `humanize_progression_reason()` and `humanize_phase_transition_reason()`. See `packages/core-engine/core_engine/decision_progression.py:235-279`.

Constitution impact:

- This family does not satisfy the minimum trace law in `docs/architecture/GOVERNANCE_CONSTITUTION.md:92-117`.
- Any first-class surface relying on these outputs inherits a weak explanation foundation.

### 2. The other six families are traceful but still constitutionally thin

Shared pattern:

- They usually provide `interpreter`, `version`, `inputs`, `steps`, and `outcome`.
- They usually do not provide constitution-equivalent `owner_family`, `policy_basis`, `reason_summary`, `alternative_resolution`, or `trust_scope`.
- The resulting traces are useful debug artifacts, but not yet minimally valid constitutional traces.

Most important examples:

- Weekly review: `packages/core-engine/core_engine/decision_weekly_review.py:816-882`
- Program recommendation: `packages/core-engine/core_engine/decision_program_recommendation.py:414-430`
- Frequency adaptation: `packages/core-engine/core_engine/decision_frequency_adaptation.py:81-116` and `packages/core-engine/core_engine/decision_frequency_adaptation.py:156-193`
- Coach preview: `packages/core-engine/core_engine/decision_coach_preview.py:714-767`
- Workout session: `packages/core-engine/core_engine/decision_workout_session.py:1023-1055` and `packages/core-engine/core_engine/decision_workout_session.py:1314-1333`
- Live workout guidance: `packages/core-engine/core_engine/decision_live_workout_guidance.py:217-248` and `packages/core-engine/core_engine/decision_live_workout_guidance.py:399-421`

### 3. Generated-week explanation surfaces still sit on top of fragmented traces from pass 1

Pass 1 already established that generated week ships with only `template_selection_trace` and `generation_runtime_trace`, not a constitutionally complete authoritative trace. See `docs/audits/2026-03-11-pass1-authority-audit.md:19-31`.

That matters here because:

- `apps/web/app/week/page.tsx` renders explanation-like copy directly from those fragmented traces.
- The week UI therefore presents rationale-like text before the generated-week path has a valid top-level authoritative trace.

## Explanation integrity verdict

### Acceptable or mostly acceptable in current scope

These are the strongest text paths in scope, because they render owner-supplied rationale fields rather than inventing new explanation text in the UI:

- Today between-set guidance and set feedback: `apps/web/app/today/page.tsx:218-223` and `apps/web/app/today/page.tsx:676-710`
- Today workout summary rationale: `apps/web/app/today/page.tsx:256-270`

Classification:

- `authoritative rationale` when `guidance_rationale` / `overall_rationale` / `item.guidance_rationale` is present
- `generic fallback` when `resolveGuidanceText()` falls back to `"Follow the planned progression."` or to the opening-set placeholder. See `apps/web/app/today/page.tsx:134-141` and `apps/web/app/today/page.tsx:218-223`.

Important limit:

- Even these better paths still depend on only `partial trace` families, so they are stronger than the other UI surfaces, not constitutionally finished.

### Illegal blur / mixing findings

#### 1. Frontend reason humanization is active shadow authority

`apps/web/lib/api.ts` contains a generic explanation engine that turns raw `reason` codes into full rationale sentences through `humanizeReasonCode()` and `resolveReasonText()`. See `apps/web/lib/api.ts:299-364`.

Why this is illegal blur:

- The helper is not rendering trace-derived rationale.
- It manufactures reason text in the presentation layer from code strings.
- The same helper is used on week, settings, coach preview/apply, and program switch surfaces, so a single shadow-authority helper shapes multiple first-class explanations.

Classification:

- `illegal blur/mixing`

#### 2. Week page presents rationale-like text from fragmented or non-trace sources

Findings:

- `Generation Read` renders `template_selection_trace.rationale` or `template_selection_trace.reason` through `resolveSelectionReason()`, even though pass 1 already marked the generated-week trace stack as fragmented. See `apps/web/app/week/page.tsx:87-90`, `apps/web/app/week/page.tsx:213-221`, and `docs/audits/2026-03-11-pass1-authority-audit.md:19-31`.
- `Mesocycle Posture` renders `Reason:` by humanizing `plan.mesocycle.deload_reason || plan.deload.reason` through `resolveReasonText()`. See `apps/web/app/week/page.tsx:135-140`.
- `Coverage Radar` uses imperative coaching copy, `Bring up ...`, that is not sourced from a trace. See `apps/web/app/week/page.tsx:151-153`.
- `Run full-volume exposures and accumulate clean reps before the next review gate.` is also explanatory coaching copy without a trace source. See `apps/web/app/week/page.tsx:135-139`.

Classification:

- `Generation Read`: `illegal blur/mixing`
- `Mesocycle Posture Reason`: `illegal blur/mixing`
- `Coverage Radar` action line: `illegal blur/mixing`
- Session counts, dates, covered muscles, weak-point slot counts: `descriptive summary`

#### 3. History page invents coaching interpretation from analytics

Findings:

- `resolveProgressionHeadline()` synthesizes causal coaching language from adherence, PR counts, and pending recommendations: `Progression is compounding.`, `Consistency is the limiter.`, `Coach recommendations need follow-through.` See `apps/web/app/history/page.tsx:164-179`.
- `Progression Brief` then presents that headline as the lead takeaway. See `apps/web/app/history/page.tsx:712-723`.

Classification:

- `illegal blur/mixing`

Why:

- This is not trace-derived rationale for a coaching decision.
- It is a summary-layer interpretation that sounds causal and coach-authoritative.

#### 4. Coaching recommendation timeline uses non-trace-derived rationale assembly

Backend finding:

- `decision_coach_preview.py` builds a single timeline rationale by preferring payload rationale strings and otherwise humanizing `reason` codes through `resolve_coaching_recommendation_rationale()`. See `packages/core-engine/core_engine/decision_coach_preview.py:879-908`.
- `build_coaching_recommendation_timeline_entry()` then stores that assembled text as `rationale`. See `packages/core-engine/core_engine/decision_coach_preview.py:919-953`.

UI finding:

- History renders that field as `Rationale:`. See `apps/web/app/history/page.tsx:747-766`.

Classification:

- `illegal blur/mixing`

Why:

- The timeline summary layer is choosing and humanizing explanations without requiring a valid `decision_trace` derivation path.

#### 5. Coaching preview and apply surfaces mix descriptive status with non-trace-derived rationale

Findings:

- `CoachingIntelligencePanel` renders preview progression and phase explanation lines through `resolveReasonText(...)`. See `apps/web/components/coaching-intelligence-panel.tsx:219-231`.
- The panel also turns `post_authored_behavior` into explanation text via `resolveReasonText(undefined, coachPreview.phase_transition.post_authored_behavior)`. See `apps/web/components/coaching-intelligence-panel.tsx:226-231`.
- Settings duplicates the same behavior for preview, program recommendation, program-switch confirmation, and phase-apply status. See `apps/web/app/settings/page.tsx:110-113`, `apps/web/app/settings/page.tsx:201-203`, `apps/web/app/settings/page.tsx:281-288`, `apps/web/app/settings/page.tsx:360-379`, and `apps/web/app/settings/page.tsx:473-476`.

Classification:

- progression / phase explanation lines: `illegal blur/mixing`
- `Current block complete` and `Recommendation: ...`: `descriptive summary`
- blank-state/status strings like `Preview ready`, `Generate a preview first`, `Phase apply failed`: `generic fallback`

#### 6. Weekly review UI re-humanizes codes instead of using trace-supplied rationale text

Findings:

- `humanizeCode()` in `apps/web/app/checkin/page.tsx` converts codes into readable explanation text in the UI. See `apps/web/app/checkin/page.tsx:21-34`.
- The review command card uses `humanizeCode(reviewResult.global_guidance)` instead of rendering the trace-carried `global_guidance_rationale` from `decision_trace.outcome`. See `apps/web/app/checkin/page.tsx:179-181` and `packages/core-engine/core_engine/decision_weekly_review.py:872-881`.
- The previous-week fault list uses `humanizeCode(fault.guidance)` instead of the trace-supplied `guidance_rationale` recorded during summary generation. See `apps/web/app/checkin/page.tsx:239-248` and `packages/core-engine/core_engine/decision_weekly_review.py:615-623`.
- The adaptive output overrides use `humanizeCode(item.rationale)` instead of the trace-supplied `rationale_text` already generated during decision construction. See `apps/web/app/checkin/page.tsx:358-363` and `packages/core-engine/core_engine/decision_weekly_review.py:789-796`.

Classification:

- `illegal blur/mixing`

#### 7. UI readiness labels in check-in are interpretive, not trace-derived

`resolveReadinessLabel()` turns readiness score thresholds into coaching-style language: `Primed to push`, `Manage fatigue carefully`, `Recovery-first week`. See `apps/web/app/checkin/page.tsx:49-60`.

Classification:

- `illegal blur/mixing`

Why:

- The text sounds like rationale or coaching judgment, but it is authored in the UI from scalar thresholds rather than from the review trace.

## Rationale-like UI text that is not trace-derived

- `apps/web/lib/api.ts:299-364` turns generic reason codes into rationale sentences for multiple first-class surfaces.
- `apps/web/app/week/page.tsx:135-140` shows deload reason via frontend humanization rather than a trace-derived rationale field.
- `apps/web/app/week/page.tsx:151-153` says `Bring up ...` without a trace-owned rationale.
- `apps/web/app/history/page.tsx:164-179` invents the `Progression Brief` headline.
- `apps/web/app/history/page.tsx:761` displays timeline `Rationale:` assembled in a summary helper rather than derived from `decision_trace`.
- `apps/web/components/coaching-intelligence-panel.tsx:220-231` and `apps/web/app/settings/page.tsx:364-379` render preview/apply rationale through frontend humanization and status formatting.
- `apps/web/app/checkin/page.tsx:179-181`, `apps/web/app/checkin/page.tsx:247`, and `apps/web/app/checkin/page.tsx:362` re-humanize weekly-review codes instead of using the rationale strings already present in trace data.

## Shadow authority in explanation / summary layers

### Backend

- `packages/core-engine/core_engine/decision_coach_preview.py:879-985`
  - `resolve_coaching_recommendation_rationale()` and timeline builders act as explanation-selection logic outside a valid trace contract.

### Frontend

- `apps/web/lib/api.ts:299-364`
  - `humanizeReasonCode()` / `resolveReasonText()` are cross-surface shadow authority for recommendation, deload, preview, and apply reasons.
- `apps/web/app/checkin/page.tsx:21-34`
  - `humanizeCode()` is a second explanation engine for weekly review.
- `apps/web/app/history/page.tsx:164-179`
  - `resolveProgressionHeadline()` turns analytics into causal coaching copy.

## Surface-by-surface classification summary

| Surface | Main explanation text in scope | Classification |
| --- | --- | --- |
| Today | `guidance_rationale`, `overall_rationale`, `item.guidance_rationale` | `authoritative rationale` when present; fallback strings are `generic fallback` |
| Today | Session intent / pacing / caution copy | `descriptive summary` or `generic fallback`, not authoritative rationale |
| Week | `Generation Read`, deload `Reason:`, coverage action line | `illegal blur/mixing` |
| Week | session lists, counts, candidate stack, weak-point slot counts | `descriptive summary` |
| History | `Progression Brief` headline | `illegal blur/mixing` |
| History | bodyweight detail, strength detail, queue counts | `descriptive summary` |
| History | timeline `Rationale:` | `illegal blur/mixing` |
| Coach preview / settings preview | preview progression / phase explanations via `resolveReasonText()` | `illegal blur/mixing` |
| Coach preview / settings | status and empty-state copy | `generic fallback` |
| Weekly review UI | command-center guidance, fault guidance, override rationale, readiness labels | `illegal blur/mixing` |

## Next recommended pass

Pass 3 should stay narrow and fix the explanation seam before widening scope:

1. Define a constitution-compliant trace contract per family, starting with `decision_progression.py`, because it is still the only family here with effectively no owner-level trace.
2. Remove frontend explanation humanizers from first-class coaching paths:
   - `apps/web/lib/api.ts`
   - `apps/web/app/checkin/page.tsx`
   - `apps/web/app/history/page.tsx`
3. Rewire week, history, preview/apply, and weekly-review surfaces to render only:
   - trace-derived rationale fields
   - clearly labeled descriptive summaries
   - clearly labeled generic fallbacks
4. Re-audit the generated-week path once pass 1 and pass 2 blockers are closed together, because the week UI currently sits on top of fragmented traces from pass 1 and mixed explanation logic from this pass.
