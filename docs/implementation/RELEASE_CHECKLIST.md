# Release Checklist

**Purpose:** Map [TRUST_AND_MATURITY_MODEL](docs/architecture/TRUST_AND_MATURITY_MODEL.md) release gates to concrete pass/fail criteria. Use this before claiming a path is ready for internal dogfood (Gate 1), private beta (Gate 2), or product-facing coach claim (Gate 3).

---

## Gate 1 — Internal Dogfood

Before a path is suitable for serious internal use, all of the following must pass.

| # | Criterion | Pass / Fail | Notes |
|---|-----------|-------------|--------|
| 1 | Path is at least Tier 4A (first-class internal) | [x] | Evidence: `docs/validation/phase2_fullbody_handoff.md` (implemented runtime + tests) and `docs/validation/phase2_fullbody_parity_matrix.md` (parity coverage). |
| 2 | No mixed-authority seam on that path can change outcome meaning | [x] | Evidence: `docs/current_state_decision_runtime_map.md` ownership map and `docs/Architecture.md` sovereignty rules; no new logic in `intelligence.py`. |
| 3 | Explanations are authoritative or clearly non-authoritative | [x] | Evidence: decision-trace-driven runtime posture in `docs/current_state_decision_runtime_map.md`; no local narrative re-authoring on active path. |
| 4 | Desktop flows validated | [x] | Evidence: `docs/implementation/DOGFOOD_PHASE1_CHECKLIST.md` + API canonical loop test (`apps/api/tests/test_phase1_canonical_path_smoke.py`). |
| 5 | Mobile flows validated | [x] | Evidence: Today mobile interaction regression now passes (`apps/web/tests/today.runner.test.tsx`), including overlay open/close safety signal used to suppress dock interception; auth/session continuity remained stable in latest reruns. |
| 6 | Felt-behavior: path feels like a coach, not a planner | [ ] | Keep open for additional real-use qualitative loops; functional blockers are cleared but this row requires repeated human-use confirmation. |
| 7 | Felt-behavior: explanations match visible behavior | [x] | Evidence: trace-backed output coverage in parity matrix and canonical loop smoke behavior. |
| 8 | Felt-behavior: substitutions feel stimulus-preserving | [ ] | Functional substitution + restriction tests pass on active full-body paths; keep open for added qualitative multi-week evidence. |
| 9 | Felt-behavior: progression and deload behavior feel justified | [x] | Evidence: week-role and deload transition checks in `apps/api/tests/test_program_catalog_and_selection.py`, parity matrix, and frequency-window continuity coverage in `apps/api/tests/test_program_frequency_adaptation_api.py`. |
| 10 | Felt-behavior: compression preserves intent | [ ] | Flexible trace-first policy is in place and transition tests pass; keep open pending additional real-use qualitative confirmation. |

**Gate 1 pass:** All 10 criteria checked. Evidence: dogfood checklist completed, forbidden-residue greps clean, mini_validate green.

---

## Gate 2 — Honest Private Beta

Before another lifter uses the path without oversell, all of the following must pass.

| # | Criterion | Pass / Fail | Notes |
|---|-----------|-------------|--------|
| 1 | Gate 1 is complete | [ ] | Blocked by unresolved Gate 1 items 5/6/8/10. |
| 2 | Docs match branch reality | [x] | Updated active authority docs on 2026-03-20: `docs/Master_Plan.md`, `docs/current_state_decision_runtime_map.md`, `docs/implementation/ACTIVE_REMEDIATION_RAIL.md`. |
| 3 | Non-gold programs are clearly gated or qualified | [x] | Current wave explicitly bounded to active full-body family; non-active templates remain library/future assets. |
| 4 | No presentation layer fakes rationale on visible user paths | [x] | Evidence: governance + authority-map constraints and regression-watch rails in `docs/implementation/ACTIVE_REMEDIATION_RAIL.md`. |

**Gate 2 pass:** All 4 criteria checked. Evidence: doc review, product copy review, Gate 1 evidence.

---

## Gate 3 — Serious Hypertrophy Coach Claim

Before the product can honestly use that phrase, all of the following must pass.

| # | Criterion | Pass / Fail | Notes |
|---|-----------|-------------|--------|
| 1 | No authoritative coaching decision occurs outside sovereign owners | [x] | Decision-family ownership mapped and enforced in current-state docs; no known active-path owner violations. |
| 2 | intelligence.py is harmless orchestration only | [x] | Explicitly constrained to compatibility façade in architecture + runtime maps. |
| 3 | Doctrine coverage is sufficient for exposed coaching behavior | [ ] | Improved for active full-body family, but broader confidence requires additional real-use evidence. |
| 4 | Exercise knowledge is coaching-grade, not merely ID-grade | [ ] | Metadata hardening completed for active templates; expansion-grade confidence remains bounded. |
| 5 | Traces are complete | [x] | Active families include structured traces, including mesocycle transition checkpoint visibility. |
| 6 | Gold path is Tier 4B | [ ] | Not claimed yet; Gate 1 and Gate 2 not fully closed. |
| 7 | Non-gold claims do not exceed non-gold maturity | [x] | Current docs keep non-active templates qualified and out of active authority claims. |

**Gate 3 pass:** All 7 criteria checked. Evidence: authority audit, trace audit, doctrine coverage review.

---

## How to use

- **Before internal dogfood:** Run Gate 1 checklist; fix any fail before inviting testers.
- **Before private beta:** Run Gate 2; ensure Gate 1 remains satisfied.
- **Before "coach" claim:** Run Gate 3; ensure Gates 1 and 2 remain satisfied.

Reference: [TRUST_AND_MATURITY_MODEL.md](docs/architecture/TRUST_AND_MATURITY_MODEL.md), [GOVERNANCE_CONSTITUTION.md](docs/architecture/GOVERNANCE_CONSTITUTION.md).
