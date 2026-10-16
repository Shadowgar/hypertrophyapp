# M4-R Batch 06 — Effort, performance progression and fatigue standard (candidate v0.3)

**Prepared:** 2026-10-16. **Authority:** human-reviewable **qualitative proposal only**, continuing [Batch 04](batch-04-customized-program-design-standard.md), [Batch 05](batch-05-original-exposure-and-feasibility-standard.md) and [Batch 06 appraisal](batch-06-rir-failure-progression-appraisal.md). The future app **must not consume this document as runtime rules**. No per-muscle set minimum/maximum, RIR band, default failure frequency, percentage load, recovery clock, deload trigger or progression increment has been approved.

## Core user promise, conditional on qualified future implementation

For an explicitly opted-in **Customized** workout, guide the person to **repeatably challenging, achievable training with intelligible progress tracking**, not to a fabricated machine-calculated physiological maximum. Accommodate the person's goal (hypertrophy vs strength vs mixed), readiness, skill, preferences, days, fatigue constraints, available equipment and *actually performed* comparable sessions. Preserve the owner’s **Authored Plans** untouched, including authored RPE and periodization. An original generator must not clone a purchased phase/week/session structure.

## 1. Separate planned effort, observed effort and stop conditions

A planned target, participant's perception and an objectively observed task outcome are **different measurements**. Candidate metadata dimensions for expert review:

| Distinct concept | Intended meaning; never infer this automatically |
| --- | --- |
| `prescribed_effort` | User-reviewed intention, source/version and confidence; may be RIR/RPE/technique instruction; not proof of achieved effort |
| `estimated_RIR_after_set` | Participant's self-report **with ability to leave unknown** and calibration quality; may be imprecise by lift/load/experience |
| `reported_RPE_after_set` | Actual user's chosen rating, scale/version and timing; distinguish from target RPE or an automatic formula conversion |
| `set_end_reason` | Completed planned repetitions; voluntary stop; technical deterioration; actual concentric inability; equipment interruption; pain; unknown |
| `failure_definition` | Momentary muscular vs technical vs volitional, if confidently known; do not label voluntary stopping “true failure” |
| `actual_load` | Recorded number + unit + per-hand/total/assistance and implement/variant; unknown load stays unknown |
| `performed_reps` | Real completed repetitions, not intended range; special methods and assisted reps separately identified |
| `exercise_comparability` | Movement variation, ROM, setup, assistance, load basis, recorded effort, set type and data corrections |
| `recovery_context` | User-reported tolerability/recent interruption plus comparable session performance, **not** a diagnostic or injury risk score |
| `confidence_and_override` | Why a suggestion is tentative; what information is missing; explicit confirmation/ability to reject |

Names are conceptual labels, not a database schema or permission to implement. A time-limited preview may use honest assumptions but must not activate if a required constraint is unknown.

**Failure is a separately disclosed option**, not an automatic “high quality” badge. A novice, unfamiliar machine, free-weight compound, fatigued user, returning lifter or user with pain must not be driven into an unrequested exhaustive attempt by the app. Distinguish skill/technical constraints from any medical assessment; the app cannot clear a person medically or calculate a true injury probability from RIR.

**Do not encode `RPE=10-RIR` as a universal truth:** the relationship depends on declared scale, conceptual definitions, observed effort and reliability; a target RPE does not make actual post-set RIR known.

## 2. Explain what evidence can and cannot choose

The scientific appraisal found: estimated-RIR syntheses suggest effort is relevant; direct trials on an 8-week time scale often do not demonstrate a clear need for momentary failure, including **2026 unilateral elbow-flexor and leg-extension comparisons**, while one 2025 **single-set** study suggests a possible modest site-specific benefit. A distinct 2025 multi-arm compound-lift trial was truncated/modified for feasibility in the failure conditions. These cannot be reduced to either “always fail” or “failure never matters.”

**Human-reviewable candidate:** expose a contextual effort *choice and rationale* tailored to movement difficulty, user skill, workout goal and actual capacity **without implementing a numeric default**. Better reasoning and honest uncertainty outrank a false universal target. Do not equate higher session distress, soreness, subjective burn, CK or temporary performance loss with more hypertrophy.

## 3. Progression based on comparable completed exposures

**Proposed state machine (conceptual, no executable code):**

1. **Observe:** read only actually completed, corrected and user-confirmed sessions for the same comparable movement variant and load semantics. Distinguish intended from completed sets and revisions; if history is empty, label first exposure a **calibration opportunity** rather than fabricate a starting 1RM.
2. **Qualify:** verify load unit, equipment, ROM/setup, set type, performed repetitions, acceptable technique, known/unknown reported effort, session timing and restrictions. A changed dumbbell to cable, load assistance, grip/ROM, or pain status may make comparison unsupported.
3. **Evaluate:** where repeated credible and comparable evidence exists, show changes in repetitions at the same load, changes in load at comparable repetition/effort, and user-rated task difficulty as **separate signals**. Do not infer muscle gain from a rep PR; strength skill, familiarity and effort also matter.
4. **Suggest, don't silently prescribe:** possible responses are **repeat/monitor**, consider a repetition target adjustment, consider a realistic available load increment, consider a deliberate exercise variant change, or **abstain** with a missing-data reason. The exact numeric thresholds are unapproved. The user can reject any change.
5. **Account for setbacks and constraints:** one lower-performance day or a missed week is not proof of overtraining, failed growth or required weight reduction. Use data completeness, goal changes, fatigue/recovery signals and time/equipment conflicts to support a **transparent review**, not a hidden penalty.
6. **Preserve history:** a changed recommendation never mutates the original performed workout, never rewrites an authored target, and never turns a draft preview into a completed training event.

**Evidence logic:** 2022 and 2024 controlled load-vs-repetition comparisons both found useful adaptations with either strategy; recent 2026 progressive-vs-fixed experiments favor ongoing challenge but **also change effort/volume load as subjects adapt**. Hence neither forced weekly extra weight nor fixed load/reps forever is an approved universal prescription.

**Candidate explanatory text:** “You completed more reps with the same equipment and load, which is measurable performance progress. Your reported effort is missing, so I can’t yet say whether to raise the weight.” / “The implement changed, so last session's weight is not directly comparable.” / “This set felt easier than last time, but one observation is not proof your recovery is complete.”

## 4. Fatigue and planned easier work: constraints, not predictive biomarkers

Candidate review variables are subjective recovery/readiness (clearly user-reported), actual completed work, noticeable decline across **comparable sessions**, missed training, chosen schedule, movement technical demands, time cap and restrictions. These may guide *questions* or optional conservative choices; they are **not** validated hypertrophy-surplus calculators, diagnostic classifiers or “injury risk = 7%” outputs.

- **Acute effect** (repetitions/velocity lost today, discomfort after a heavy squat) is not the same as **longitudinal adaptation** or what caused an injury.
- **No compulsory deload on a preset week.** Strength-peaking source phases, competition tapers and a short research-trial deload are not universal hypertrophy doses. A future optional easier period needs a stated reason, user understanding and expert-reviewed criteria; its magnitude, length and triggers remain unresolved.
- **No automatic increased effort to overcome a plateau.** Reassess comparability, adherence, exercise feasibility and recovery first, then allow informed choices.
- **Pain/limitations** are not treated as “push through.” The app should make substitution/stop-and-seek-appropriate-professional-help options available, without pretending to diagnose.

## 5. Original, non-numeric acceptance cases for future review

| Case | Expected preview/reasoning | Must never happen |
| --- | --- | --- |
| New user selects hypertrophy, unfamiliar barbell, no measured RIR | Explain skill/calibration uncertainty; pick feasible movement options and no unverified performance target | Force failure or assume a current 1RM |
| Trained person records moderate effort after a comparable set | Preserve reported RIR/RPE and technique details; offer qualitative next-time options | Convert perceived 3 RIR to an objective 3 RIR biological fact |
| User performs same exercise at same load and more reps | Recognize performance progress while checking effort/setup comparability | Automatically declare a quantified muscle-size gain or load increase |
| Load has no smaller available increments | Offer additional comparable reps or holding load where appropriate | Invent machine plates or increments |
| User swaps unilateral dumbbell for bilateral cable | Reset load comparison eligibility and explain mechanical difference | Copy “last weight” across noncomparable implements |
| Last session missed; rolling PPL in use | Maintain explicit next-session pointer and actual calendar | Mark missed work complete or restart week automatically |
| Fatigued after a technically demanding compound session | Distinguish acute fatigue from chronic training response; user-controlled conservative alternatives | Force another failure set to “boost hypertrophy” |
| Reports pain or training-limiting discomfort | Pause/adapt the activity choice and present appropriate real-world help | Medical clearance prediction or a numeric injury probability |
| Plateau after multiple comparable attempts | Consider goals, load feasibility, scheduling and actual effort; user-approved monitor/variation choice | Autogenerate a high-volume supercompensation phase |
| Source-owned bench specialization selected in Authored | Preserve its exact verified source and target vs last-set logging semantics | Rewrite it with new generalized customized recommendations |

**Human quality gate:** expert reviewers must assess exercise ontology, actual set/variant comparability, target-vs-reported RIR/RPE reliability, feasibility, chronic vs acute fatigue distinction, missing-data behavior and user-facing disclaimers. Before any numbers: independent primary-study appraisal/supplement checks, explicit population/goal/condition constraints, owner acceptance and separate deterministic acceptance harness. No code until that gate.

## 6. Evidence update / reversal policy

Keep claims traceable to specific papers and publication/cutoff dates. If a new well-controlled study reverses a muscle-specific finding, the original candidate rationale must become **review-required**, not silently change live training. Version qualitative policies independently of Authored source artifacts. Separate the user's preferences and lived training experience from literature conclusions, and maintain full informed activation control.

**Bottom line:** Better original workout construction requires **measurement honesty, effort feasibility, repeatable progression and individually reviewable decisions**, not pretending to have calibrated a universal scientific optimum.
