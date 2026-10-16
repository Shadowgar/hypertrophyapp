# M4-R Batch 04 — Evidence-to-program design standard (candidate v0.1)

**Research date:** 2026-10-16  
**Status:** Original research synthesis and **nonbinding** generator specification. Not a validated optimum, formal systematic review, authorized source modification, or implemented prescription. This work introduces **no** numerical dose defaults, application code, database changes, or copy of a proprietary workout table.

## The product question

A user can type: "I want Full Body," "Build a four-day Upper/Lower," "Make a three-day PPL," or "Choose the best split for me with 45 minutes per workout." What *must* a trustworthy independent Customized mode do?

**Candidate answer:** Build a multiweek, coherent, feasible plan with explicit goals, equipment, available actual dates, experience/skill, session duration, muscular coverage and progression; preserve useful movement comparability; show unresolved constraints or genuine tradeoffs; let the user review and activate it. Do not claim that any split name is intrinsically the highest-hypertrophy option.

## Evidence basis and boundaries

### 1. What the owner's private training books say — source observation, not efficacy proof

- Nippard's **Fundamentals** manual (printed pp.6–7, 23, 80–86) presents 3-day Full Body, 4-day Upper/Lower and 5-day body-part structures as practical alternatives. It emphasizes preference/adherence, repeatable exercises and a progression logbook. Its historical p.84–86 frequency/volume claims were tied to 2016/2017 reviews; the later 2026 literature does not justify copying those numbers as universal rules.
- **Essentials 4x** (printed pp.5–8) explicitly optimizes a roughly 45-minute session constraint through fewer exercise sets, higher focus on quality and performance tracking. It does **not** establish that all short sessions are physiologically equivalent to longer, higher-volume sessions.
- **High Frequency Full Body 4x** (printed pp.7–11, 74–75) treats stimulus-to-fatigue as a conceptual tradeoff, not a measured universal score. It notes both benefits and concerns of distributing training frequently.
- **Back Hypertrophy** (printed p.5) warns that adding direct arm work to heavy back training can overcount stress because pulls already involve elbow flexors. **Shoulder Hypertrophy** (printed p.7) warns against simply stacking its high-pressing-volume specialization on top of chest specialization. These are source-level *cautions*, not proven fixed set discounts or clinical overuse predictions.
- **Pure Bodybuilding Phase 1/2** handbooks contain source-specific effort/intensity, prescribed techniques, approved replacements and weaker-muscle options; these are **Authored Plan instructions**, not a universal generated-plan construction recipe.
- **Comeback Bridge** (printed pp.6–7) distinguishes complete vs partial layoffs vs continued heavy lifting; these are author-specific bridge options rather than proven optimum recovery durations.
- **Powerbuilding** separates size-and-strength objectives and uses lift-specific intensity/progression. Do not assume a person's "build muscle" request also mandates maximum 1RM strength specialization.

No unpublished manuscript text, complete exercise tables, private source URLs, licensed identifiers or original source files are committed here.

### 2. What independent human research supports — external literature, not source author authority

| Question | External literature | Research interpretation for design |
| --- | --- | --- |
| Are Full Body or split labels independently superior? | [PMID 38595233](https://pubmed.ncbi.nlm.nih.gov/38595233/) (2024, 14-study synthesis) | No general volume-equated superiority found. A null contrast does **not** prove physiological equivalence in every subgroup |
| How should weekly set exposure be handled? | [PMID 41843416](https://pubmed.ncbi.nlm.nih.gov/41843416/) (2026 ACSM position stand; searches through Oct. 2024); [PMID 41343037](https://pubmed.ncbi.nlm.nih.gov/41343037/) (2026, 67-study meta-regression) | Dose matters and has diminishing returns; counting indirect sets is model-dependent. Neither a fixed personal maximum nor an experimentally validated universal indirect-set coefficient has been established |
| Should we score higher training frequency as intrinsically better? | [PMID 41343037](https://pubmed.ncbi.nlm.nih.gov/41343037/) | Independent hypertrophy effect is uncertain; frequency can help distribute quality training and strength practice |
| Should every set reach failure? | [PMID 38970765](https://pubmed.ncbi.nlm.nih.gov/38970765/) (2024 estimated-RIR exploratory meta-regression); [PMID 41843416](https://pubmed.ncbi.nlm.nih.gov/41843416/) | Closer-to-failure work can matter for growth, but estimated RIR has uncertainty and universal failure was not a consistently superior prescription |
| Should exercise selection constantly change? | [PMID 35438660](https://pubmed.ncbi.nlm.nih.gov/35438660/) (2022 8-study review); [PMID 39388663](https://pubmed.ncbi.nlm.nih.gov/39388663/) (2025 70-woman randomized trial) | Systematic movement variety *may* affect some regional outcomes, but random frequent changes are unsupported and one trial found broadly similar gains with stable versus varied selection |
| Is every long-length variation superior? | [PMID 33009197](https://pubmed.ncbi.nlm.nih.gov/33009197/) (2021 20-person hamstrings RCT); [PMID 40570881](https://pubmed.ncbi.nlm.nih.gov/40570881/) (2025 12-study Bayesian review) | Some head-/movement-specific comparisons favor one variation; broad muscle-length evidence does not validate a universal bonus |
| Should training be split by sex? | [PMID 40028215](https://pubmed.ncbi.nlm.nih.gov/40028215/) (2025 Bayesian meta-analysis, 29 studies) | Relative size gains broadly similar in studied adults; do not impose stereotyped program inventories based solely on sex |

**Research quality:** The above is a targeted synthesis from independently retrieved abstracts and previously reviewed rights-eligible full texts, not fresh exhaustive full-text appraisal of every referenced study. Observed source practice, research outcome, our inference and the future generator policy are **separate levels of evidence**. The reviews overlap underlying trials and must not be treated as independent samples.

## Candidate requirements: what a generator should do

### Hard constraints — reject or explicitly request modification rather than hide a failure

- Keep **Authored Plan** immutable; only a separately chosen, informed **Customized** mode can construct original training.
- Record the exact program objective: hypertrophy, strength, mixed, or re-entry. "Best" means best *for the stated objective and constraints*, not one universal magic score.
- Respect specified equipment, training location, absolute session-time cap, available local dates/timezone, practical exercise restrictions, required split (if feasible) and selected training days.
- Account for incomplete or missing input using transparent defaults or **abstention**; never invent owned machines, bar weights, medical clearance, benchmark 1RMs or exercise competence.
- Preserve exercise prescription semantics: sets, actual reps and units, target effort vs observed effort, set type, load basis (per-hand vs total vs assistance), and any paired sequences. Corrected/undone records must remain canonical.
- Never silently delete a session when a split/date combination is infeasible; show the user the conflict and practical alternatives.
- Preview must be distinct from activation. Stable program/session identities survive reloads; a preview cannot consume weeks or training history.
- New program design cannot assume scientific protection from injury; discomfort and technique constraints need conservative alternatives or user action.

### Soft objectives — balance, not fake-precision scores

- Prioritize adherence, completed high-quality work, manageable session time and sufficient repeatable movement practice.
- Cover relevant muscle actions and regions *when feasible* using a deliberately varied but bounded exercise selection; avoid redundant exercises solely to maximize a volume metric.
- Balance intended primary and secondary muscle exposure from compounds; **do not** silently add specialization workload on top of already high indirect exposure.
- Spread work across actual dates to reduce avoidable same-muscle fatigue/interference; keep cross-week context and explain unresolved recovery data.
- Maintain exercises long enough to make progress comparable; rotate deliberately for constraints, preference, phase or evidence-supported regional objectives.
- Recommend changes from qualified *completed comparable exposures*, not because a calendar week elapsed. Unknown actual effort stays unknown.
- Offer confidence-aware explanations: "selected to fit equipment and target actions" rather than "scientifically proven #1 exercise."

## Split feasibility: scenario matrix for a future acceptance harness

These are **illustrative test cases**, not approved weekly training prescriptions or a claim that a specific split is optimal.

| User asks | Candidate feasibility response | Failure/qualification to test |
| --- | --- | --- |
| **2 days, Full Body**, moderate session limit | Create two original, balanced exposures that fit exact dates and available equipment | Avoid promising full maximal dose for every muscle when time is insufficient |
| **3 days, Full Body** | Use three complementary full-body sessions; vary emphasis without chaotic weekly movement rotation | Check overlapping direct/indirect work, rest spacing, and actual duration |
| **3 days, Upper/Lower** | Offer an alternating/rolling Upper–Lower sequence across successive weeks with transparent uneven same-week frequencies | Must not pretend a fixed week contains two of each, nor restart the same opening session every Monday |
| **3 days, PPL** | Honor PPL as a feasible preference if the required work fits, and disclose that major patterns generally appear once in that seven-day cycle | Do not label it scientifically inferior or guarantee equivalent growth; suggest a rolling alternative if goals/duration warrant |
| **4 days, Upper/Lower** | Build distinct Upper A/B and Lower A/B exposures at user-selected dates | Must be original, not copied from any purchased 4-day program; no unapproved extra weak-point sets |
| **4 days, PPL** | Support a transparent **rolling sequence** across weeks if the user wants this split rather than falsely inserting six sessions into four dates | Cross-week state must carry next session and preserve performed dates; no skipping or doubling when the week changes |
| **5 days, choose for me** | Compare Full Body/hybrid/Upper–Lower+focus or rolling PPL using feasible duration and preference; explain tradeoffs | Do not pick solely by split label or fabricated hypertrophy rating |
| **6 days, PPL** | Build two differentiated cycles with equipment, recovery and actual calendar constraints | Avoid claiming high frequency always beats fewer days; fatigue and session budget need monitoring |
| **45-minute gym sessions** | Reduce unnecessary complexity/time costs, consider feasible pairing and controlled set dose | Do not silently truncate the requested outcome, omit warm-up/setups or call every advanced technique a growth multiplier |
| **Return from an extended break** | Request/observe recent training readiness and present a conservative re-entry structure | Do not infer current 1RM from historic PR or automatically copy Comeback source week structure |
| **Bigger shoulders / arms** | Redistribute emphasis deliberately; count pressing/pulling overlap and nonpriority coverage | Avoid blindly stacking two specialization programs or using made-up recovery/overuse probabilities |
| **Home equipment, only adjustable dumbbells** | Select compatible original movements, load semantics and feasible increments; disclose missing equipment | No barbell/leg-press/cable prescriptions or impossible load rounding |
| **Missing schedule or equipment** | Ask one essential question or provide an openly provisional preview with explicit unknowns | No false claim of a fully qualified program; no hidden default about owned equipment |

### Hard test cases

A future deterministic harness should include: a week crossing DST/timezone changes; 4-day rolling PPL spanning December–January; a missed session and user-controlled carryover; two users with equal goals but different equipment; history corrected after activation; unknown load/RPE; a long-duration exercise with a 30-minute time cap; changing grip or machine variants without inheriting an incomparable working load; no invalid program silently activated. Validate on isolated data, mobile UI and real human review.

## Stop/go gate before implementation

**Ready for a generator design PR only after:** (a) human-reviewed, versioned definition of exercise ontology and direct/indirect coverage; (b) population-specific starting dose and effort *ranges* justified with full-text evidence, including explicit uncertainty; (c) initial program schemas and qualitative split plans verified as original; (d) a content/feasibility acceptance harness passes for several competing configurations; (e) all code preserves source and execution histories.

**Ready for production only after:** tested safe onboarding, comparable progression, realistic timing/equipment, data correction/recovery, false-infeasibility investigation, and independent knowledgeable coaching review.

**Non-goal:** This document does not prove the existence of a globally optimum workout, assign any numerical muscle-gain scores, endorse one sex-specific plan, approve exercise substitutions, or change any live workout.
