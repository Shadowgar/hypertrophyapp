# M4-R cross-project evidence note — Military H2F and optional tactical-readiness programming

**Date:** 2026-10-16. **Classification:** original research/architecture proposal only. **Implementation:** none. **Do not expand the active M4-C1 hypertrophy pilot** from GitHub issue #85 or mutate source-owned Authored plans. No paid/proprietary or distribution-limited source material may be redistributed.

## Question

Can the owner's separate **Super Soldier military learning project** contribute to `hypertrophyapp`, whose principal initial goal is science-based individual hypertrophy and adaptive working-load progression?

**Decision:** Yes, as an **additional physical-performance/conditioning knowledge layer and distinct optional user objective**, not a direct replacement for hypertrophy programming or blanket copying of a military PT routine. Military *readiness* and maximal muscle growth measure different outcomes. Both should share the same reliable exercise-history, dose/exposure, effort and calendar infrastructure.

## What was actually inspected

- Connected Drive folder **Mil Docs** contained **28 PDFs** with opaque numerical filenames, so titles were checked by *small, targeted text extracts* rather than pretending the folder was a modern H2F curriculum. Selected source identifications:
  - `20638.pdf`: Army FM 3-19.30 **Physical Security** (2001); no modern physical fitness prescription.
  - `23786.pdf`: Army FM 5-426 **Carpentry** (1995); not exercise evidence.
  - `22285.pdf`: Army FM 3-25.150 **Combatives** (2002); contains physical preparation and train-the-trainer topics but assumes supervised combatives practice; not hypertrophy trial evidence.
  - `20646.pdf`: FM 21-76 **Survival** (1992); unrelated to optimal set/repetition dosing.
  - `20737.pdf`: Army Marksmanship Unit **Pistol Marksmanship Training Guide** (physical conditioning chapter); occupational specificity, not general hypertrophy.
  - `20673.pdf`: Army FM 5-33 **Terrain Analysis** (1990).
  - `20655.pdf`: a **commercial Delta/SEAL Civilian Security and Personal Defense Manual**, not official US military hypertrophy doctrine; source ownership/permissions require separate review.
  - `20669.pdf`: 2011 Marine Corps martial-arts publication displays **Distribution Statement B: authorized to US Government agencies for official use only**; **exclude from public LMS/app re-publication until explicit rights/distribution authorization**. It also says the material is not meant as independent self-instruction and must not be presented as such.
  - `20657.pdf`: Army pistol training FM 3-23.35 (2003).
- **Limits:** This is a **nine-document spot check**, not a complete audit of all 28 PDF bodies; other manuals were not categorized. No claim that the folder contains a current FM 7-22/H2F manual was established. Historical files' training recommendations require age/validity qualification and rights review.
- The external current fitness source is **US Army Holistic Health and Fitness (H2F)**, with a new official publication guide [Army H2F Doctrine Update, September 3, 2026](https://www.army.mil/article/295085). Related official resources: [H2F system](https://h2f.army.mil/), [H2F physical domain](https://h2f.army.mil/Domains/Physical-Domain/), [official H2F resource listing](https://h2f.army.mil/Unit-Resources/) and [Army Fitness Test](https://www.army.mil/aft/). These provide primary **doctrine and occupational readiness frameworks**, not proof that a particular military circuit causes superior hypertrophy.
- The current **FM 7-22** and **ATP 7-22.02** are linked from the September 2026 Army update. Their full current PDFs and program tables were **not independently page-by-page qualified in this note**. Do not claim full appraisal or overwrite v1 policy based on these references alone.

## H2F ideas relevant to our architecture

| Military / H2F idea | Appropriate product adaptation | Do not infer |
| --- | --- | --- |
| Individualized physical needs assessment | A distinct user's **goal priority**: hypertrophy, tactical performance, or hybrid; equipment, time, skill and real-world demands | All soldiers have the same optimal workout; tactical training automatically accelerates hypertrophy |
| Work capacity and aerobic fitness | Optional sustainable aerobic/anaerobic conditioning; track workload/time, recovery and change in measurable task performance | More running/rucking always yields more muscle growth |
| Loaded movement/carries | Optional task-specific progressive work capacity using actual load, distance, duration, footwear/terrain where observable | A heavy ruck is a substitute for knee-flexor hypertrophy work or a safe first exposure for an untrained user |
| Power/agility/strength-endurance | Purpose-built *additional* training qualities with outcome-relevant tests; specify exposure type | One 1RM or muscle circumference measures all tactical capabilities |
| Preparedness and warmups | Feasible prep, skill, technique, fatigue constraints, steady progression and safer movement selection | Required 20-minute rituals have independently shown a universal hypertrophy advantage |
| Recovery, sleep, nutrition, mental readiness | Optional contextual information with privacy minimization and user consent; protect reliability of longitudinal comparison | Sleep score predicts a recovered muscle, exact injury probability or correct training dose |
| Standards / physical testing | Use **goal-specific** field tests or validated task performance observations as optional benchmarks | AFT/CFT performance is a clinical injury screen or a direct muscle-growth measure |

Army doctrine emphasizes assessing a Soldier's unique mission and physical abilities and combines different disciplines; our deterministic coaching should likewise **optimize to the user's chosen objective**. Prescribe strength, aerobic training, loaded carries, and power work only where they serve that objective and respect time/recovery constraints.

## Scientific constraint: concurrent resistance + endurance training

- [2026 umbrella review, PMID 41762427](https://pubmed.ncbi.nlm.nih.gov/41762427/) synthesized 17 meta-analyses and found combined resistance/endurance training can improve aerobic performance while producing broadly comparable average strength/power/hypertrophy outcomes versus resistance training alone in represented samples. It does **not** prove exact equivalence for every trained individual, endurance dose or high-impact military regimen; heterogeneous studies and overlapping source data must be considered.
- [2024 meta-analysis, PMID 37847373](https://pubmed.ncbi.nlm.nih.gov/37847373/) analyzed 59 studies/1,346 adults and found small interference in **male lower-body strength** under included conditions; direct hypertrophy information was insufficient to make firm sex-specific conclusions.
- Therefore, do **not** automatically append intense intervals, long rucks or high-volume calisthenics to an already demanding three-day hypertrophy program. Combined load, completed training time and next-session performance must inform scheduling and recovery choices. Poor outcomes can reflect adherence, added endurance fatigue and inadequate total recovery, not simply incorrect RIR.

## Proposed separable goals and constraints

1. **Hypertrophy-first (existing issue #85):** program design optimized for muscle development and time feasibility; military physical training **not enabled by default**. Optional low-conflict aerobic conditioning, warmup and task skill remain deliberate user choices. Do not inject new unapproved volume defaults into C1.
2. **Hybrid hypertrophy + tactical readiness (separately gated future):** multi-objective allocation of available training time toward both growth and a selected operational capability. User sees honest tradeoffs, e.g., some extra ruck/run work may consume recovery/time otherwise available for muscle-specific volume; do not promise maximal results in both simultaneously.
3. **Tactical-readiness priority (separately gated future):** apply an independent evidence-reviewed doctrine/rule policy emphasizing endurance, loaded movement, muscular strength/endurance, power, movement quality and particular occupational tests. May be relevant to police/fire/first responder users as an optional profile, but **not** a claim of military credential or completed supervised qualification.

A single person may eventually choose a profile and change it explicitly, with program version/reasons and training history intact. Goal choice **must not silently shift** a user's existing program, prior sets, source-owned Authored plan or permitted load coaching.

## Evidence and implementation gates

**Present C1:** unchanged. Focus on deterministic original Full Body hypertrophy and working-load calibration; protect Authored/production histories and PR #83 scheduling work.

**Potential C2 expansion after review:**
- H2F authoritative edition/date/provenance registry; training modality ontology covering resistance, aerobic, interval, carry/ruck, balance/mobility and recovery; no raw runtime PDF parsing.
- Fully separate goal-mode policies with explicit acceptance, user consent, relative emphasis, equipment, quantified time burden and fatigue/collision rules. Distinguish conditioning exercises from hypertrophy direct/secondary set accounting.
- Review load-carriage safety and occupational tests from authoritative sources, with explicit supervision/proficiency prerequisites where relevant.
- Compare only outcomes of matching training modalities: muscle growth and strength vs aerobic endurance, load-carriage ability or speed. No opaque one-number “optimal soldier/hypertrophy score.”
- Subject matter/risk and intellectual-property review, independent test data, explicit owner authorization and new PR before live activation.

**Do not copy modern military program tables blindly, assume military source is scientifically superior to controlled hypertrophy trials, or publish any restricted/proprietary military PDFs.**

## Architectural decision requested

**Recommendation:** Accept military H2F as a *supplemental reviewed knowledge source* and authorize **planning/research for a future Hybrid/Tactical goal mode**, while **not altering in-flight M4-C1 code scope**. Actual training rules, dose/recovery schedules, safety requirements and deployment remain subject to explicit later approval.
