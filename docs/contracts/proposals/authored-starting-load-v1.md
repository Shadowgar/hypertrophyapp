# Approved Authored provisional initial-load v1 amendment

**Status: Owner-approved numerical policy; implementation and qualification on PR #111.**
Date: 2026-10-23. Scope: Wave A / M2A / PERS-008 / [Issue #103](https://github.com/Shadowgar/hypertrophyapp/issues/103).
The owner explicitly approved this amendment at PR #111 commit
`4041a558ec3160806f36eddb7f0fc90c346681a9`, then authorized bounded implementation
through the existing owner, API and runner. This approval covers a provisional
initial estimate, not clinical accuracy, optimal training, production release,
existing completed-exposure progression or Customized policy. PR #110 remains
unchanged at `b3844398b50a64311f99ccf74411801bbd88225c`.

The approved [PERS-008 requirement](https://github.com/Shadowgar/hypertrophyapp/blob/4ac9c49b8c9f274dd70784f4ec9027e65592f657/docs/requirements/personal-workoutapp-2026-10-21.md)
and [Wave A crosswalk](https://github.com/Shadowgar/hypertrophyapp/blob/4ac9c49b8c9f274dd70784f4ec9027e65592f657/docs/roadmap/personal-capability-crosswalk-2026-10-21.md)
are on unmerged PR #109; they were read directly, not merged into this branch.
This amendment does not accept ADR-006, change completed-exposure progression,
or extend Authored policy to Customized.

## Why a numerical decision is needed

[`core_engine.load_intelligence`](../../../packages/core-engine/core_engine/load_intelligence.py)
owns Authored progression and has no initial 1RM calculation. Its reviewed
[M2A-1 design](../../plans/m2a-load-intelligence-design.md) covers actual completed
exposures, not a rep-aware conversion of self-reported strength. The retained
browser helper uses 70%; `rules_runtime.resolve_starting_load` can use 72%.
Neither depends on the prescribed repetitions. The canonical starting-rule
provenance does not establish a rep-specific percentage curve. Activating
either would bypass the requested decision and reuse an unsupported legacy path.

## Approved decision: provisional initial estimate v1

Add a distinct initial-calibration branch **inside the existing load owner**.
Keep `known_1rm`, `estimated_1rm`, `provisional_starting_load`, performed sets
and qualified progression distinct in the typed output and trace.

1. **Authority first.** The existing qualified history decision wins. Current
   working sets use existing remaining-set guidance. This initial branch is
   eligible only before current working sets and when there is no effective
   working history in the exact comparison cohort. If history exists but is
   unqualified, retain its known baseline/manual path and its specific reason;
   do not bypass missing effort, mixed loads, incomplete work or safety signals
   with a more confident estimate. No cross-machine fallback.
2. **Bounded eligibility.** Authored Phase 1/2 only; unchanged first ordinary
   working set with explicit numeric rep range, upper target **6–12**, and
   explicit source RPE range within **7–10**. No AMRAP, hard load directive,
   unresolved substitution, first-set intensity technique, pain/unsafe report,
   assistance, bodyweight or added-bodyweight estimate. Later-set techniques
   and source warm-up count/instructions remain untouched.
3. **Exact setup.** Require confirmed performed variant/side/ROM, equipment and
   setup identity (including relevant attachment/grip/settings), and explicit
   `total_external`, `per_hand` or `machine_stack` basis. A machine's displayed
   load is usable only on that same setup; no assumption about pulley ratio,
   Smith bar/counterweight or transfer to another machine. This is user-declared
   context, not verified equipment calibration.
4. **Known 1RM path.** Positive finite user-entered load, explicit lb/kg, observed
   date not in the future, and confirmation it still represents this exact
   setup. No maximal test is requested. The entered 1RM remains a reported
   benchmark, never an actual performed record in WorkoutApp.
5. **Recent-set path.** Positive finite load, **1–10** completed reps, explicitly
   reported **0–3 RIR**, and **reps + RIR ≤ 10**, same confirmed setup/date rules.
   Missing RIR stays unknown and yields manual calibration. Compute
   `estimated_1rm = load × (1 + (reps + RIR) / 30)`; for `reps + RIR = 1`, retain
   `estimated_1rm = load`. Label this estimated, not known. Do not convert an
   old actual RPE field into RIR or store this report as completed work.
6. **Rep-aware provisional load.** For the first working set only:

   ```text
   target_reps = upper bound of first source working-set rep target
   provisional_target_RIR = 10 − lower bound of its source RPE target
   raw_start = known_or_estimated_1rm / (1 + (target_reps + provisional_target_RIR) / 30)
   ```

   The source-target translation is an **explicit owner-approved assumption for this
   estimate only**. It does not infer actual effort, rewrite the source target,
   or activate RPE/RIR conversion in the progression owner. Choosing the upper
   rep bound and lower RPE bound is a conservative product choice, not a
   validated guarantee of the resulting effort.
7. **Attainable selection.** Use canonical decimal kg and a positive, explicitly
   declared attainable list or min/step/max grid in its original unit. Choose
   the greatest attainable load **at or below** `raw_start`; never round up or
   invent a zero-origin stack, minimum bar or default 0.5 kg grid. If none is
   available, abstain with the missing context and leave manual logging usable.

## Worked acceptance examples — approved policy

Declared example grid: 5–100 lb in 2.5 lb steps, exact same cable setup.

| Input and unchanged first-set target | Raw calculation | Approved expected output |
|---|---|---|
| Known 100 lb; Cross-Body 10–12, RPE 7–8 | `100 / (1 + 15/30) = 66.666… lb` | **65 lb provisional**; 1 source warm-up, all 3 work sets/effort targets unchanged |
| Same benchmark; target 8–10, RPE 7–8 | `100 / (1 + 13/30) = 69.767… lb` | **67.5 lb provisional**, illustrating rep dependence |
| Recent 40 lb × 8, explicit 2 RIR; Cross-Body target | `e1RM = 53.333… lb`; raw `35.555… lb` | **35 lb provisional**, estimated strength labeled separately |
| First example entered as 45.359237 kg with the same lb grid converted exactly | Same physical calculation | **29.48350405 kg = 65 lb**, no display-round-trip drift |
| Known benchmark, missing setup/grid, recent RIR unknown, or incompatible machine | Not admitted | No inferred weight; explain the missing item and permit manual load |
| Exact-cohort completed 40 kg × 11 with actual source-compatible RPE | Existing progression owner | **40 kg history-backed hold**, even if a benchmark would imply a different initial estimate |

New-feature core/API/frontend tests and isolated browser qualification are recorded
in [implementation evidence](../../evidence/starting-load-2026-10-23/IMPLEMENTATION.md).
The table defines acceptance values; the evidence distinguishes calculations,
actual application demonstrations, inherited failures and remaining limits.

## Evidence and limits of the assumptions

[LeSuer et al., 1997](https://paulogentil.com/pdf/The%20Accuracy%20of%20Prediction%20Equations%20for%20Estimating%201-RM%20Performance%20in%20the%20Bench%20Press,%20Squat,%20and%20Deadlift.pdf)
compared prediction equations, including Epley, using repetitions to fatigue in
67 untrained students on three free-weight lifts. It supports identifying the
equation as an estimate; it does **not** validate this RIR extension, inverse
calculation or cable exercise. `1/30` retains WorkoutApp's existing Epley
coefficient convention; it is accepted here only as provisional initial-load policy.

[Zourdos et al., 2016](https://pubmed.ncbi.nlm.nih.gov/26049792/) studied an
RIR-based RPE scale in experienced and novice squatters. It supports the scale's
interpretation, not precise Cross-Body performance prediction.
[Shimano et al., 2006](https://pubmed.ncbi.nlm.nih.gov/17194239/) found that the
repetition/percentage relationship differs by exercise. These studies therefore
motivate low-confidence labeling and exact-setup boundaries; they do not approve
these coefficients or establish an optimal/safe individualized load. The input
bounds, conservative target, grid floor and RIR extension above are **owner-approved
engineering choices**, not thresholds claimed from those studies.

## Application boundary

The API persists an independent account/setup-scoped calibration revision,
original magnitude/unit/date/method and explicit confirmation. It never
write a `WorkoutSetLog`, completed exposure, strength PR or prior prescription.
Reload of the same occurrence restores the exact calibration; a later occurrence
requires confirmation that it remains representative. A setup/source/variant
change invalidates applicability. Current effective history is re-evaluated
before offering or applying it; correction/void can remove history qualification
without rewriting the saved benchmark or resurrecting voided work.

The approved runner renders the owner's separate `provisional` result as
“Suggested starting weight — estimate”, with units, a short reason, missing
context explanation and editable actual weight. User edits/pending commands
stay stationary and unchanged by refreshed advice. Source warm-up numbers may
use that result only through an explicit provisional-input extension of the
existing source warm-up owner, retaining its count, recipe and uncertainty.
Customized keeps its independent calibration/consent policy. No deployment or
production migration is authorized by approval of this numerical amendment.

[Current runtime characterization and remaining gates](../../evidence/starting-load-2026-10-23/README.md).


## Implementation identity and retry clarification

An equipment/setup identity has one declared meaning within the source/variant
scope. Changing grip, side, ROM or settings requires a distinct setup identity;
a saved identity cannot silently be reassigned by editing the descriptive details.
The same occurrence restores its own latest report. Later occurrences may reuse
the saved fields only after explicit confirmation. Calibration retries preserve
command and payload and append at most one revision; their response re-evaluates
current guidance rather than replaying an obsolete recommendation. This differs
from immutable performed-set receipt replay and never rewrites that history.
