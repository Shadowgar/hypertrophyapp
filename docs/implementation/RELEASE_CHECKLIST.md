# Release Checklist

**Purpose:** Map [TRUST_AND_MATURITY_MODEL](docs/architecture/TRUST_AND_MATURITY_MODEL.md) release gates to concrete pass/fail criteria. Use this before claiming a path is ready for internal dogfood (Gate 1), private beta (Gate 2), or product-facing coach claim (Gate 3).

---

## Gate 1 — Internal Dogfood

Before a path is suitable for serious internal use, all of the following must pass.

| # | Criterion | Pass / Fail | Notes |
|---|-----------|-------------|--------|
| 1 | Path is at least Tier 4A (first-class internal) | [ ] | Structurally strong; doctrine good enough for honest internal use; safe for serious internal dogfood. |
| 2 | No mixed-authority seam on that path can change outcome meaning | [ ] | No router, facade, or UI invents or alters coaching decisions; decision_* owners only. |
| 3 | Explanations are authoritative or clearly non-authoritative | [ ] | All user-visible explanation text is trace-derived (authoritative) or explicitly labeled fallback/summary. |
| 4 | Desktop flows validated | [ ] | Full Phase 1 loop (onboard → generate week → today → log sets → check-in → review → next week) completes on desktop browser. |
| 5 | Mobile flows validated | [ ] | Same loop completes on mobile viewport or device; no layout/UX blockers. |
| 6 | Felt-behavior: path feels like a coach, not a planner | [ ] | Subjective audit: prescriptions and guidance feel coaching-driven, not generic. |
| 7 | Felt-behavior: explanations match visible behavior | [ ] | Rationale shown in UI matches what actually drove the decision (trace-backed). |
| 8 | Felt-behavior: substitutions feel stimulus-preserving | [ ] | Swap choices feel aligned to intent, not arbitrary. |
| 9 | Felt-behavior: progression and deload behavior feel justified | [ ] | When deload or progression triggers, the reason is understandable from context/trace. |
| 10 | Felt-behavior: compression preserves intent | [ ] | When reducing days/sessions, intent (e.g. weak-point day, compound priority) is preserved, not only volume. |

**Gate 1 pass:** All 10 criteria checked. Evidence: dogfood checklist completed, forbidden-residue greps clean, mini_validate green.

---

## Gate 2 — Honest Private Beta

Before another lifter uses the path without oversell, all of the following must pass.

| # | Criterion | Pass / Fail | Notes |
|---|-----------|-------------|--------|
| 1 | Gate 1 is complete | [ ] | All Gate 1 items above are satisfied. |
| 2 | Docs match branch reality | [ ] | Master_Plan, current_state_decision_runtime_map, ACTIVE_REMEDIATION_RAIL reflect actual code and behavior. |
| 3 | Non-gold programs are clearly gated or qualified | [ ] | If any non-gold program is exposed, it is labeled with maturity/trust scope (e.g. "experimental", "bounded trust"). |
| 4 | No presentation layer fakes rationale on visible user paths | [ ] | No UI or facade invents "why" text; all rationale trace-derived or explicitly non-authoritative. |

**Gate 2 pass:** All 4 criteria checked. Evidence: doc review, product copy review, Gate 1 evidence.

---

## Gate 3 — Serious Hypertrophy Coach Claim

Before the product can honestly use that phrase, all of the following must pass.

| # | Criterion | Pass / Fail | Notes |
|---|-----------|-------------|--------|
| 1 | No authoritative coaching decision occurs outside sovereign owners | [ ] | All meaningful decisions in decision_* modules; intelligence.py orchestration only. |
| 2 | intelligence.py is harmless orchestration only | [ ] | No coaching meaning owned in intelligence.py; forwarding/aliasing only. |
| 3 | Doctrine coverage is sufficient for exposed coaching behavior | [ ] | Typed rules and canonical state support every exposed recommendation, deload, substitution, progression. |
| 4 | Exercise knowledge is coaching-grade, not merely ID-grade | [ ] | Metadata supports substitution, stimulus intent, and compression decisions. |
| 5 | Traces are complete | [ ] | Every authoritative decision emits a sufficient decision_trace (owner, inputs, steps, outcome, reason_summary). |
| 6 | Gold path is Tier 4B | [ ] | First-class product-facing; strong enough to present as real coaching path without qualification. |
| 7 | Non-gold claims do not exceed non-gold maturity | [ ] | Any non-gold program is not marketed or presented as equal to gold. |

**Gate 3 pass:** All 7 criteria checked. Evidence: authority audit, trace audit, doctrine coverage review.

---

## How to use

- **Before internal dogfood:** Run Gate 1 checklist; fix any fail before inviting testers.
- **Before private beta:** Run Gate 2; ensure Gate 1 remains satisfied.
- **Before "coach" claim:** Run Gate 3; ensure Gates 1 and 2 remain satisfied.

Reference: [TRUST_AND_MATURITY_MODEL.md](docs/architecture/TRUST_AND_MATURITY_MODEL.md), [GOVERNANCE_CONSTITUTION.md](docs/architecture/GOVERNANCE_CONSTITUTION.md).
