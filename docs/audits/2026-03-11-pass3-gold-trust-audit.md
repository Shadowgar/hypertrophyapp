# 2026-03-11 Pass 3 Gold Trust Audit

Scope audited only:

- gold-path artifacts and runtime path
- gold loader / canonical artifact path
- trust tier and maturity claims
- non-gold program treatment

Authority used:

- `docs/architecture/GOLD_PATH_MILESTONE.md`
- `docs/architecture/TRUST_AND_MATURITY_MODEL.md`
- `docs/audits/2026-03-11-pass1-authority-audit.md`
- requested `docs/audits/2026-03-11-pass2-trace-explanation-audit.md` was not present on disk during this pass

## Executive judgment

The gold path is not ready for Tier 4A internal dogfood.

The strongest reality today is:

- the repo has one special gold artifact path
- several sub-surfaces inside that path are bounded and useful
- the end-to-end gold path still fails Tier 4A because generated week remains non-sovereign, explanation classification is not implemented, bounded-trust labeling is not honored in product copy, and non-gold programs are still surfaced as peer options without maturity qualification

## Gold Runtime Reality

### Gold loader and canonical artifact path

Observed gold path:

1. Gold authored artifact lives at `programs/gold/adaptive_full_body_gold_v0_1.json`.
2. Gold exercise knowledge is loaded from `programs/gold/pure_bodybuilding_phase_1_full_body.onboarding.json` through `_load_adaptive_gold_exercise_library()` in `apps/api/app/program_loader.py:201-216`.
3. Gold doctrine rules are loaded from `docs/rules/gold/adaptive_full_body_gold_v0_1.rules.json` through `load_program_rule_set()` in `apps/api/app/program_loader.py:451-471`.
4. The gold authored artifact is not used directly at runtime. It is projected into a generic `CanonicalProgramTemplate` by `_adaptive_gold_to_runtime_template()` in `apps/api/app/program_loader.py:290-347`.
5. Generation then flows through `prepare_generation_template_runtime()` and `resolve_generation_template_choice()` in `packages/core-engine/core_engine/generation.py:585-720`.
6. Week construction then flows through `scheduler.generate_week_plan()` in `packages/core-engine/core_engine/scheduler.py:807-941`.
7. Final payload shaping happens in `intelligence.build_generated_week_plan_payload()` in `packages/core-engine/core_engine/intelligence.py:1702-1731`.

### What this means

The gold path does have a distinct artifact family, but the runtime canonical artifact is still a lossy projection, not a doctrine-complete gold runtime artifact.

The clearest evidence is in `apps/api/app/program_loader.py`:

- `_adaptive_slot_to_runtime_exercise()` collapses authored `work_sets` into simple `sets` and `rep_range`, and sets `start_weight` to a hardcoded `20.0` (`apps/api/app/program_loader.py:219-272`)
- `_adaptive_gold_to_runtime_template()` hardcodes generic deload and progression defaults instead of carrying authored doctrine through the runtime artifact (`apps/api/app/program_loader.py:329-347`)

That means the first-class generated-week path is still driven by a structurally valid but semantically narrowed representation.

## Tier 4A Requirement Audit

| # | Requirement | Status | Why |
| --- | --- | --- | --- |
| 1 | No gold-path authority in `intelligence.py` | `false` | Pass 1 already showed active generation-template ordering/selection and generated-week payload shaping in `intelligence.py` (`docs/audits/2026-03-11-pass1-authority-audit.md`). Current code still shows `order_generation_template_candidates()` and `recommend_generation_template_selection()` in `packages/core-engine/core_engine/intelligence.py:1847-2000`, plus generated-week payload shaping in `packages/core-engine/core_engine/intelligence.py:1702-1731`. |
| 2 | Preview / apply unification | `partial` | Coach preview and apply do share one decision family and apply consumes persisted preview payloads through `prepare_coach_preview_route_runtime()` and `prepare_coaching_apply_runtime_source()` in `packages/core-engine/core_engine/decision_coach_preview.py:102-235`. But the path still lacks explanation classification, and the product surface still mixes authoritative output with UI-humanized fallback text, so the path is not clean enough to call fully unified. |
| 3 | Structural fidelity gap list is current | `false` | I did not find a current, branch-accurate structural fidelity gap list. I found planning docs such as `docs/plans/2026-03-11-phase1-fidelity-diff.md`, but not the maintained gap list required by the milestone. |
| 4 | Doctrinal fidelity gap list is current | `false` | Same issue as structural fidelity. There is evidence of known doctrinal loss, especially Early Set / Last Set flattening in `docs/plans/2026-03-11-phase1-fidelity-diff.md`, but not the required current doctrinal gap list. |
| 5 | Explanation classification is implemented | `false` | I found no implementation of authoritative-rationale / descriptive-summary / generic-fallback classification. The only direct references are in architecture docs. Meanwhile the UI still resolves explanation text ad hoc with `resolveReasonText()` in `apps/web/lib/api.ts:327-364` and `resolveGuidanceText()` in `apps/web/app/today/page.tsx:134-141`. |
| 6 | Valid decision traces | `false` | Several sub-surfaces do emit strong traces, but the gold generated-week surface still lacks a constitutionally complete authoritative `decision_trace`, as already established in pass 1 and still visible from the generated-week path ending at `packages/core-engine/core_engine/scheduler.py:926-941` and `packages/core-engine/core_engine/intelligence.py:1702-1731`. |
| 7 | No semantically insufficient artifacts | `false` | The gold runtime artifact is still semantically insufficient for first-class coaching claims. The loader flattens authored work-set semantics and hardcodes generic progression/deload (`apps/api/app/program_loader.py:219-347`). The scheduler then invents mesocycle, deload, recovery-pressure, and continuity doctrine locally (`packages/core-engine/core_engine/scheduler.py:168-242`, `262-286`, `647-722`). |
| 8 | Felt behavior audit | `false` | I did not find a completed felt-behavior audit artifact for the gold path. |
| 9 | Correct bounded-trust labeling | `false` | The architecture docs define bounded trust, but product copy exceeds that budget with labels like `Coaching Intelligence`, `Program Intelligence`, `How the app coaches`, `adaptive coaching signals`, and `trainer's recommended program` in `apps/web/components/coaching-intelligence-panel.tsx:145-235`, `apps/web/app/settings/page.tsx:281-455`, and `apps/web/app/page.tsx:71-163`. |
| 10 | No shadow authority | `false` | Pass 1 found shadow authority in `intelligence.py`, `generation.py`, and `scheduler.py`. This pass additionally found user-facing rationale humanization outside explanation classification via `apps/web/lib/api.ts:327-364`, `apps/web/app/week/page.tsx:87-90`, and `apps/web/app/today/page.tsx:134-141`. |

## Actual Trust Level by Surface

Trust labels below are for the currently exposed surface, not the best-case helper in isolation.

| Surface | Actual trust level | Maturity reality | Why |
| --- | --- | --- | --- |
| Gold-path generated week | `Not Trustworthy Yet` | below Tier 3 | Generated week still depends on a lossy canonical artifact, shadow authority in `intelligence.py` / `generation.py` / `scheduler.py`, and ships without a constitutionally complete authoritative trace. |
| Gold-path today workout | `Not Trustworthy Yet` | below Tier 4A as a full surface | The live workout layer has useful deterministic subcomponents, but the full surface still inherits non-sovereign generated-week output, rendered mesocycle/deload claims, and explanation-like UI framing. |
| Substitutions | `Bounded Trust` | Tier 3 at best for covered exercises | Covered substitution logic is deterministic and traced through workout/runtime helpers, rule-set logic, equipment compatibility, and repeat-failure handling (`packages/core-engine/core_engine/decision_workout_session.py:1120-1263`, `packages/core-engine/core_engine/scheduler.py:378-455`). It is still bounded to covered metadata and rule coverage. |
| Progression | `Bounded Trust` | Tier 3 at best for covered progression families | Progression decisions in preview and workout state are handled by dedicated decision helpers and rule-backed rationale. That is materially stronger than generated-week doctrine, but still bounded and not enough to elevate the whole path. |
| Deload | `Not Trustworthy Yet` | below Tier 3 on generated-week path | Visible deload behavior is still materially determined by scheduler-local heuristics in `_compute_mesocycle_state()` and exposed without a full authoritative trace (`packages/core-engine/core_engine/scheduler.py:168-242`, `845-873`, `926-941`). |
| Weekly review | `Bounded Trust` | Tier 3 at best | Weekly review uses a dedicated decision family with explicit traces, persisted adjustments, and bounded readiness/SFR-aware logic (`packages/core-engine/core_engine/decision_weekly_review.py:715-1235`). Its truthful ceiling matches the trust model's bounded-review framing. |
| Recommendation | `Not Trustworthy Yet` | below Tier 4A as exposed | The recommendation engine is deterministic and traced, but it ranks and rotates across mixed gold and non-gold catalogs without maturity gating (`packages/core-engine/core_engine/decision_program_recommendation.py:65-96`, `139-164`, `276-509`). That makes the exposed recommendation surface over-strong relative to actual path maturity. |
| Preview / apply | `Bounded Trust` | Tier 3 at best | Coach preview/apply has the cleanest family-level ownership in this pass. Preview and apply share a decision family, preserve traces, and apply from persisted preview payloads (`packages/core-engine/core_engine/decision_coach_preview.py:102-235`, `317-469`, `698-876`). It is still blocked from Tier 4A by explanation-law, trust-labeling, and upstream generated-week sovereignty problems. |
| History / analytics | `Bounded Trust` | not a coach-authoritative maturity path | The backend analytics surface is deterministic summary logic with no claim to authoritative coaching causality (`packages/core-engine/core_engine/history.py:586-660`). It becomes over-strong only when the UI reframes it as coaching state. |
| Non-gold programs | `Not Trustworthy Yet` as peer-equal first-class paths | varying maturity, not disclosed | Non-gold programs may have usable runtime artifacts and some rule sets, but they are not clearly qualified per program. The product still treats them as peer catalog items and recommendation candidates without trust/maturity labels. |

## Overclaimed Trust Language

Yes. Current copy exceeds the truthful bounded-trust ceiling in multiple places.

Examples:

- `apps/web/components/coaching-intelligence-panel.tsx:145-235`
  - `Coaching Intelligence`
  - `Generate Coaching Preview`
  - `Apply Phase`
  - `Apply Specialization`
- `apps/web/app/settings/page.tsx:281-455`
  - `Program Intelligence`
  - `Recommended Program`
  - `Coaching Preview`
  - `Default — trainer's recommended program`
- `apps/web/app/page.tsx:71-163`
  - `Run today’s session to unlock progression, history, and coaching signals.`
  - `Generate a week to queue the next session and unlock adaptive coaching signals.`
  - `How the app coaches`
- `apps/web/app/week/page.tsx:127-140`
  - `Mesocycle Posture`
  - `Deload Precision`
  - `Progressive Overload`
  - `Reason:` text synthesized through `resolveReasonText(...)`
- `apps/web/app/history/page.tsx:197-206`, `712-761`
  - `Coach Queue`
  - `Coach recommendations need follow-through.`
  - `Coaching Decision Timeline`
  - free-form `Rationale:` presentation detached from explanation classification

The common pattern is not that the runtime is random. The problem is that the surface language sounds more coach-authoritative and explanation-clean than the current truth budget supports.

## Non-Gold Program Treatment

Yes. Non-gold paths are still overpromoted.

Why:

- `list_program_templates()` merges gold and non-gold templates into one flat catalog with no maturity or trust fields (`apps/api/app/program_loader.py:350-390`)
- `ProgramTemplateSummary` and `GuideProgramSummary` expose no trust or maturity qualification fields (`apps/api/app/schemas.py:428-443`)
- onboarding ranks programs only by split/day fit and alphabetical display, not maturity (`apps/web/app/onboarding/page.tsx:388-408`)
- guides render every program as a generic `Program Module` (`apps/web/app/guides/page.tsx:20-39`)
- settings exposes a flat program override list under `trainer's recommended program` language (`apps/web/app/settings/page.tsx:439-455`)
- program recommendation rotates across all compatible program IDs, including non-gold, on adaptation/coverage/mesocycle signals (`packages/core-engine/core_engine/decision_program_recommendation.py:65-96`, `139-164`, `276-509`)

This violates the milestone's explicit warning against equal promotion of non-gold programs.

## Bottom Line on Tier 4A Internal Dogfood

No.

The gold path is not ready for Tier 4A internal dogfood because all of the following remain true:

- generated week is still non-sovereign
- generated week is still driven by a semantically narrowed runtime artifact
- gold-path generated week still lacks a constitutionally complete authoritative trace
- explanation classification is not implemented on first-class gold surfaces
- bounded-trust labeling is not reflected honestly in product copy
- non-gold programs are still exposed as peer options without maturity gating
- no current structural gap list, doctrinal gap list, or felt-behavior audit was found

## Practical maturity reading

The truthful current read is:

- the repo has one strongest gold benchmark path
- some gold sub-surfaces are bounded and internally useful
- the end-to-end gold path is still below Tier 4A
- recommendation and non-gold exposure currently make the trust story look stronger than branch reality

## Recommended next pass

Pass 4 should be a narrow claim-downgrade and path-gating audit:

- enumerate every user-facing gold and non-gold label that exceeds bounded trust
- define the exact copy downgrade needed for each surface
- define the minimum catalog / recommendation gating needed so non-gold programs stop being presented as peer-equal to gold
- separately decide whether generated week should be demoted explicitly to below Tier 3 until the gold runtime artifact is doctrine-sufficient
