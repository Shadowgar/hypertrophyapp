# Load-progression contract

Status: **Owner-approved automatic-load direction; technical evidence rules Proposed**. Owner: deterministic load/exposure decision family; API records effective data and web presents/prefills/overrides. [ADR-006](../adr/0006-load-and-exposure-model.md). No numerical training threshold is newly accepted here.

## Inputs, exposure and comparability

Input: immutable prescription, effective set records for a finalized exercise occurrence, performed variant/equipment, explicit load unit/basis, actual effort when supplied, quality/readiness flags, comparable prior exposures, equipment inventory, ruleset/version and explicit context. Output: `increase / hold / decrease / monitor`, attainable working load or no newly inferred load, sufficiency/uncertainty, evidence references, reason and override origin.

One completed exposure is one finalized exercise occurrence with all required effective qualifying work sets. Warm-ups and technique children do not count as ordinary work-set exposures. Voided/duplicate records are excluded. Explicit partial closure is retained with completeness status; incomplete evidence cannot silently increment completed-exposure/streak counts. A rule can evaluate a declared partial evidence set conservatively without relabeling it complete. Repeated same-exercise occurrences are distinct; correlation and prescription differences must not inflate confidence.

Compare performed variant, equipment/load basis/units, prescribed reps/effort and actual quality/completeness. Catalog ID or primary slot alone is insufficient. Assistance is not ordinary added load; per-hand load is not total barbell load. Missing equipment calibration/effort prevents that comparison dimension. Prescribed RPE/RIR never substitutes for actual observed effort; do not fabricate legacy values or silently convert between RPE/RIR.

## Actions and authority

`increase` advances an attainable load when qualified evidence/rules justify it. `hold` preserves a qualified load when continuation is supported. `decrease` recommends an attainable reduction based on qualified context/performance. `monitor` explicitly abstains from a new progression conclusion when evidence is insufficient/incomparable/uncertain; it can retain a clearly labeled known/overridden baseline without implying qualification.

Calculate and prefill the next load automatically; user arithmetic is unnecessary. Expose evidence/reason and allow override. Mid-workout correction uses current effective sets and the same permission boundary; it may change working load, never authored exercises, set counts, reps, RPE/RIR, techniques or block progression. Source hard load/intensity instructions constrain coaching. Pain or an impossible load can pause/report unresolved work; substitution still needs explicit source permission and confirmation.

Use available plates/stacks/dumbbells, unit/basis and equipment increments. Rounding direction/rules are versioned and respect allowed bounds; an unattainable suggestion returns an explained alternative/conflict. Plate calculation considers bar/load basis and inventory rather than inventing plates. Warm-up calculation preserves source warm-up semantics under one qualified owner.

## Sufficiency, corrections and acceptance

Bad-day protection distinguishes one anomalous context from repeated comparable regression. Exact windows, progression thresholds, confidence categories and safety exceptions require accepted doctrine or clearly labeled proposed rules and qualification; no new universal thresholds are selected here. Confidence describes evidence sufficiency/comparability, not probability of hypertrophy gains.

Persist recommendation/evidence/rule version and user chosen load/reason. Performed load controls later analysis; planned/prefilled load remains separate. Corrected/undone sets invalidate dependent exposure summaries, streaks and recommendations and rebuild the same effective state; historical evidence references remain auditable. Lost/inconsistent projections trigger rebuild/monitor rather than guess.

Acceptance: planned 50 versus performed 45 uses the performed evidence; missing effort does not produce a same-RPE claim; assisted/bodyweight variants remain separate; a single bad day does not automatically prove regression; partial/duplicate/child sets do not count as extra completed exposures; correction removes its future effect; available increments produce feasible prefill; override preserves authored dose and trace. PostgreSQL concurrency and replay must qualify the supporting history contract.
