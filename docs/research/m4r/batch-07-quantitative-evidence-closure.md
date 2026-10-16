# M4-R Batch 07 — Quantitative evidence closure and study-dependency correction

**Date:** 2026-10-16. **Purpose:** close *specific* prior research blockers rather than restart the JN archive audit or re-review Batches 01–06. **Status:** targeted scientific appraisal; not a completed independent systematic review, GRADE assessment, numerical-policy approval, or authorization to implement a generator.

## Scope and methodological provenance

Previously completed: 78 private JN assets inventoried (57 original PDFs / 21 XLSX), full binary/OOXML structural audits, Batches 01–06 literature and candidate qualitative standards. **No original archive files were re-downloaded, hashed or counted again**. B06's new private manual checks and core source observations were reused rather than replayed.

This batch targeted:
1. **2026 Pelland/Remmert/Robinson volume–frequency published methods/results** previously abstract-level only;
2. **2026 Vasconcelos/Ruivo/Refalo multiple-paper cohort independence** previously judged probable overlap;
3. a **2026-10-06 non-peer-reviewed reanalysis** using the same published volume–frequency dataset;
4. existing independently appraised 2023–2026 reviews/trials to separate supported *population-level ranges* from numerically unvalidated *individual defaults*.

Source verification dates: October 16, 2026. Public paper identifiers and links are included below. Available published PDF was visually confirmed at its first page, evidence-tiers page and limitations page, and sections reviewed in small portions. Supplemental OSF analysis scripts, individual-study coding and any author-supplied raw data **were not independently run or recalculated**. No formal RoB 2/AMSTAR 2/GRADE grade assigned here. This is **not** a new full systematic search.

## R07-A — 2026 volume/frequency meta-regression: methods-level appraisal advanced

**Pelland et al.**, [PMID 41343037](https://pubmed.ncbi.nlm.nih.gov/41343037/), [journal DOI 10.1007/s40279-025-02344-w](https://doi.org/10.1007/s40279-025-02344-w). Final publication *Sports Medicine* 56 (2026), first online December 4, 2025. Peer-reviewed version (25 published PDF pages) now examined, including methods, effect-model results, discussion, bias caveats and uncertainty. The earlier B05 label “abstract-only” is superseded **for published main-text appraisal**, not supplementary reanalysis.

**Exact denominator accounting, which matters to decisions:**
- **All outcomes combined:** 67 independent studies, 2,058 participants.
- **Hypertrophy volume model:** **35 studies**, **220 modeled effects**, **1,032 participants**, not all 67 studies/2,058. A square-root form fit best within the candidate models; marginal fixed effects explained about **22.3%** of the variability, so substantial unexplained variation remains.
- Models included duration and training-status covariates; source participants mean age ~25, 79.1% male, excluded age >70, studies predominantly short. Authors note limits in control availability, studied high-volume cases, protocol variability and selection of participants who completed tolerable interventions.
- **Direct/indirect exercise involvement was judged by the measured muscle's likely force-generating role.** Indirect contribution was represented as either **0, 0.5 or 1** for comparing model fit, with the midpoint fitting these pooled data better. This **does not validate a universal biological half-set** for any particular muscle, elbow position, skill or person.

**Model-derived volume-efficiency boundaries, recorded solely as empirical reference data:** Authors' *fractional set* classification placed ~**4 weekly sets** at their **smallest-detectable model-defined response**, roughly **5–10** in a higher-efficiency tier, **11–18** in a next tier, then progressively diminishing model yield. Their **smallest detectable effect size of ~2.05% muscle size** was estimated with auxiliary nontraining control-group data; it is a **statistical modeling threshold**, not the amount that any person's muscle would reliably grow or a validated “minimum effective dose” for all. Uncertainty expands with high volume; authors did **not** identify a clear general hypertrophy plateau in their best-fitting model. We deliberately **do not copy the full published tier table** or convert its numbers into future code.

**Risk and scope:** The main analysis was a multilevel *across-protocol* synthesis, not an individual randomized trial of “exactly four weekly sets” versus no training. Its inclusion search ended before June 2024 and did not cover all trials published later. TESTEX is not automatically equivalent to a formal RoB 2 assessment; authors themselves acknowledge that few papers precisely defined actual momentary failure. Site-specific ultrasound/other imaging can differ from whole-muscle outcomes and can be affected by post-exercise fluid changes; dose response of *one measured site* does not guarantee a feasible *whole-body* plan at the same volume for every region.

**Decision:** support “weekly work matters; marginal benefit likely diminishes,” and use model boundaries **only as *review evidence***. Block any claim that the model's four fractional sets represent an individual minimum or that 0.5 is a universal secondary-muscle coefficient. Block defaulting to 19+, 30+ or 43+ sets on the grounds that an extrapolated curve continues upward. Quantitative **per-muscle starting ranges** still require distinct population/goals, stress counting rules, expert review and owner approval.

## R07-B — Shared 2026 intervention cohort: independent cross-report evidence confirmed

Primary published record: [Vasconcelos et al., *Applied Sciences* 2026, DOI 10.3390/app16178724](https://www.mdpi.com/2076-3417/16/17/8724), titled *Bioelectrical Responses to Resistance Training Performed to Momentary Failure or with Repetitions in Reserve: A Within-Subject Analysis of Phase Angle and Impedance Components*. This independently published article **explicitly states that 19 resistance-trained adults did twice-weekly unilateral preacher curl **and** leg extension training under contralateral failure/RIR assignment during the same eight-week experiment**. Its sex-specific sample details (11 men, eight women; male age 20.4 ± 1.8 years, female age 24.8 ± 4.7; male weight 74.9 ± 7.6 kg, female 63.0 ± 10.1) reconstruct the exact overall averages previously seen in the two muscle-specific papers.

- [Arm hypertrophy report, PMID 42784046 / PMC13609929](https://pmc.ncbi.nlm.nih.gov/articles/PMC13609929/) covered preacher-curl elbow-flexor adaptations in the same-size/same-characteristic cohort.
- [Leg-extension report, PMID 42617172](https://pubmed.ncbi.nlm.nih.gov/42617172/) covered knee-extensor adaptations with the same-size/same-characteristic cohort.
- **The third paper's outcome is limb-level electrical impedance/phase angle, not independently demonstrated local hypertrophy.**

**Cohort disposition:** Treat as **one 19-person randomized within-participant intervention with at least three outcome reports**, not two or three independently replicated trials. No private participant data requested. Exact cross-paper record linkage (ID-level) was not published to us, but the third paper's explicit training-combination statement resolves the key review decision. B06's “probable overlap” wording is updated. No claim of independent muscle-specific replication is allowed.

## R07-C — Latest dose/frequency reanalysis: promising but nonindependent

[Boutagy & McKean, posted October 6, 2026 on SportRxiv](https://sportrxiv.org/index.php/server/preprint/view/1100), *Weekly training volume, but not its division into sessions, is associated with resistance-training hypertrophy*. **Unreviewed preprint / not a new randomized sample.** It reanalyzes the Pelland dataset restricted to direct, site-specific hypertrophy observations (authors report 220 effects from 35 trials and 963 participants under their cleaned analytical rules). The abstract indicates hypertrophy was associated with weekly volume but shows a near-zero independent session-partitioning estimate, with intervals compatible with negligible effects under their analytic assumptions.

**Interpretation:** Does not overturn the published volume synthesis by itself; it highlights that interpreting per-session volume, session frequency and weekly volume as independent causal levers is methodologically fraught. **Do not add preprint study counts to Pelland's totals, or claim it independently proved split equivalence.** A future validated tool may distribute doses over feasible dates but should not award independent hypertrophy “frequency points.”

## R07-D — Cross-evidence synthesis for numeric ranges (reuses previously appraised works)

- **ACSM 2026 position stand** [PMID 41843416](https://pubmed.ncbi.nlm.nih.gov/41843416/), overview of 137 reviews, searched to **October 2024**, reports better average hypertrophy with higher dose including **≥10 weekly sets** in compared literatures. That is **not** a requirement that every user must start or stay at ten, nor independent of the same underlying trials examined by Pelland and earlier reviews.
- **2023 Bayesian network review** [PMID 37414459](https://pubmed.ncbi.nlm.nih.gov/37414459/) finds multiset approaches among useful options versus no training, but the hypertrophy network had **0% studies rated low RoB** by the authors in the previous B05 full-text inspection. Node ranks are not workout split rankings.
- **2024 nine-study rest review** [PMID 39205815](https://pubmed.ncbi.nlm.nih.gov/39205815/) suggested potential benefits when moving from **≤60 seconds to longer** recovery but did **not** detect a specific hypertrophy optimum above about **90 seconds** in its sparse, heterogeneous comparisons. Therefore a “90-second scientifically perfect timer” is unsupported.
- **2017 21-study load review** [PMID 28834797](https://pubmed.ncbi.nlm.nih.gov/28834797/) compared <=60% vs >60% 1RM with protocols trained to failure; it found no significant pooled difference in hypertrophy, but heavy loads better for test-specific 1RM strength. This does **not** prove identical hypertrophy for every repetition number or make failure mandatory for any given load.
- **2024 split/full-body meta-analysis** [PMID 38595233](https://pubmed.ncbi.nlm.nih.gov/38595233/) did not identify a volume-equated universal split advantage. Non-significance is **not** robust equality across all schedules or populations.
- **Failure / effort:** the distinct B06 papers, including [PMID 40249908](https://pubmed.ncbi.nlm.nih.gov/40249908/) and the now-de-duplicated Vasconcelos cohort, do **not** identify a reliable universal RIR optimum. Training to failure can entail greater immediate fatigue; single-set studies occasionally favor it at specific muscles without compelling a generalized failure policy.
- **Progression:** load versus rep experiments [PMID 36199287](https://pubmed.ncbi.nlm.nih.gov/36199287/) found both viable; a 2026 progressive-versus-fixed trial [PMID 42880344](https://pubmed.ncbi.nlm.nih.gov/42880344/) changed RIR and accumulated work as training advanced. Forced week-by-week heavier weights are not isolated as a unique cause of growth.

## Findings and evidence-status table

| Domain | Directly usable *qualitative* principle | Numeric finding may be discussed by reviewers | Not approved / open research |
| --- | --- | --- | --- |
| Volume | More qualified hard work can improve hypertrophy with diminishing returns; respect time and tolerance | Group-level `≥10 sets/wk` (ACSM); 2026 **4 fractional** model detection; **5–10 / 11–18 fractional** comparison tiers | No universal 4-, 10-, 15-, 20- or 30-set personal prescription; no automatic volume ramp |
| Set accounting | Track primary and secondary stimulus separately | Fractional 0/0.5/1 *model comparisons* | No validated biological 0.5 secondary set multiplier for any exercise |
| Frequency and split | Choose actual achievable days, dose distribution and user preference | Volume-equated literature largely does not isolate clear hypertrophy superiority | No 'optimal split' or days-per-week hypertrophy score |
| Reps and load | Different loads/repetition schemes can cause growth, provided challenging work and comparable technique | Low/high load definitions vary between trials | No universal maximum hypertrophy repetition count or %1RM |
| RIR/failure | Record target versus completed/perceived effort; avoid obligatory failure | 1–3 RIR studied in limited controlled contexts | No universally optimal RIR or false physiological effort precision |
| Rest | Adequate rest for repeatable performance; time feasibility matters | >60s potentially helpful; not proven exact best timer | No one-size 60/90/180s optimum |
| Progression | Hold, more reps, more load or reassess based on comparable records | Context-specific trial differences | No calendar-forced increment / invented 1RM |
| Deload | Review persistent practical fatigue/tolerability and user choice | No validated global length/onset | No compulsory week-4/6 deload or unverified recovery clock |

### Research-stop boundary, not an endless literature project

**Ready to draft human-reviewable qualitative program blueprints now:** ownership separation, explicit exercise-actions and equipment, honest time cap, one-session versus rolling cycles, direct/secondary ledger, actual-versus-target effort, nonautomatic progression, missing-data abstention, independent scenario comparisons.

**Not ready for final generator numerical approval:** initial sets/week by training status and *which muscle*, direct/indirect weighting coefficient, target/maximum RIR, exact rest by movement, minimum warmup, schedule-specific time predictions, medically constrained populations and fatigue-triggered deload criteria. A qualified human strength professional must make these explicit conditional decisions, documenting dose-counting assumptions and user exceptions. If the owner wants faster delivery, **no additional general literature audit is needed first**; use the finite reviewer decisions rather than creating more research batches without a defined gap.

**No app source, generator, database, Authored Plan, training history or production environment was changed. No copyrighted JN program tables were copied.**
