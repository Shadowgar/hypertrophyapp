# M4-R research protocol — version 0.1

**Drafted:** 2026-10-16. **Status:** working protocol, not preregistered, not a systematic review. This is a research-quality process specification for developing future original Customized workout logic; it is not a replacement for clinical or strength-coach supervision.

## I. Research aims

Primary: which resistance-training decisions most reliably support skeletal muscle hypertrophy for healthy adult populations, after accounting for feasibility, experience, session time, equipment, individual constraints and adherence?

Secondary: which changes primarily benefit strength, power, skill, efficiency or enjoyment, and should not be sold as unique hypertrophy gains?

No "best workout known to man" claim will be made: between-person heterogeneity, study quality and missing direct head-to-head tests preclude proving a universally optimal training program.

## II. Questions, exposures and outcomes

Use separate, predeclared PICO/PICOTS questions, initially:

| RQ | Comparison | Main outcomes and caveats |
| --- | --- | --- |
| Q1 | Per-muscle weekly sets; direct vs indirect sets; baseline vs additional work | Muscle thickness/volume/CSA; recovery and diminishing returns |
| Q2 | Frequency at equal dose; split and weekly distribution | Hypertrophy, strength, work quality and adherence; distinguish named split from exposure frequency |
| Q3 | Rep range, relative load and proximity to failure | Hypertrophy, strength, fatigue, effort-estimation reliability |
| Q4 | Full ROM, trained muscle length, lengthened-only and post-failure partials | Muscle-specific imaging results; avoid collapsing distinct interventions |
| Q5 | Inter-set rest, exercise order, pairing/supersets and session duration | Hypertrophy and actual time; acute volume load is not growth |
| Q6 | Periodization, progression, deloads and autoregulation | Longitudinal hypertrophy; distinguish strength and training organization |
| Q7 | Exercise choice, substitutions and region-specific adaptations | Specific muscle region/action, comparability and equipment/mechanics |
| Q8 | Comeback, novice/advanced profiles, age, sex and other constraints | Applicability, adherence, individual variability and safety |

Primary efficacy outcomes favor muscle imaging (MRI, ultrasound) or direct biopsy where appropriate. Dual-energy X-ray absorptiometry/lean mass and bodyweight are secondary proxies with limits. Actual performance, fatigue, pain, dropout, time and adherence are separate secondary outcomes. No single proxy defines net muscle growth.

Separate acute experiments, mechanistic hypotheses, narrative reviews and randomized training interventions. An EMG signal, a metabolite, a pump or an extrapolated fascicle length cannot stand alone as proof of more chronic hypertrophy.

## III. Source document audit

1. Enumerate all folders/files, preserving original path, type, size, name, edition, author, date, language and private source ID in a **private** record.
2. For each raw PDF obtain SHA-256, page count, text-readability/scan status, and section/page anchors. Use raw per-page extraction when permitted; cross-check text against a page image for unusual symbols/numbers.
3. For each XLSX obtain file hash, workbook and sheet names, raw cell values/types, formatted display values, merged ranges and formulas. Flag every apparent date conversion of RPE, rep range or load; no direct text-preview numeric import.
4. Deduplicate exact hashes separately from near-duplicate titles/trimmed editions. Keep distinct copyrighted editions and sheets separate until reconciled.
5. Extract *claims*, their context and cited academic studies as short **paraphrases**, not long copyrighted passages or copyable program tables.
6. Retain Authored-source provenance as authoritative for **that specific purchased program only**; do not let it become generic scientific doctrine.

Pilot status: 78 file metadata records across 18 folders obtained from private Drive; seven PDF manuals sampled at selected sections and two workbook text projections inspected. No binary hashes or exhaustive full-text manuscript appraisal have been completed.

## IV. Literature discovery and screening

- Search PubMed/MEDLINE, Cochrane, SPORTDiscus and citation networks where accessible; use trial registries to detect protocols and unpublished/ongoing work.
- Record **exact search string, search date/time, database, returned count, screening decisions and deduplication identifiers** in the private master index.
- Include seminal older controlled trials plus systematically updated evidence through 2026-10-16. Prefer well-controlled human hypertrophy studies. Include negative/null findings and conflicting outcomes.
- Use filters that reflect each PICO; record methodological and study-population exclusions explicitly. Do not silently exclude a study because its outcome contradicts a favored coach.
- Apply title/abstract and full-text screening. One model-assisted screening pass is only provisional; independent human verification is needed before describing an output as a formally qualified systematic review.
- Track primary RCTs underlying multiple reviews and avoid adding overlapping samples, analyses or meta-analyses as if independent.

Public methods:
- PRISMA 2020: https://www.prisma-statement.org/prisma-2020
- Cochrane RoB 2 (randomized trials): https://methods.cochrane.org/bias/resources/rob-2-revised-cochrane-risk-bias-tool-randomized-trials
- AMSTAR 2 (systematic reviews): https://www.amstar.ca/Amstar-2.php
- GRADE Working Group: https://www.gradeworkinggroup.org/

**Caveat:** PRISMA is a *reporting* framework. Adopting its checklist does not itself guarantee systematic-review conduct or low bias.

## V. Extract and critically appraise

Each evidence record should include:

- PMID/DOI, year, full bibliographic citation, exact verified source location and full-text access state;
- participant number analyzed, population, sex distribution, mean age, baseline training experience, duration and attrition;
- randomized cluster/within-participant/parallel design, allocation, blinding where relevant, pre-registration;
- exercise(s), muscle(s), dose, distribution, effort, volume equating, rest, control intervention and intervention fidelity;
- primary outcome method, mean changes, effect/uncertainty (CI or CrI), practical relevance and measurement limitations;
- potential confounding, publication bias, risk of bias domains, indirectness, imprecision, inconsistency and selectively reported outcomes;
- overlap with other reviews/studies, sponsoring organizations and declared conflicts where documented;
- applicability to novices, trained adults, other ages, equipment-restricted users and actual personalized schedules.

Use RoB 2 for applicable randomized trials; AMSTAR 2 for eligible systematic reviews; GRADE principles for outcome-specific certainty where evidence permits. Neither a manuscript's publication in a high-profile journal nor its newness is enough for high confidence. **Do not assign a GRADE grade from an abstract alone.**

Study conclusion, author interpretation, source-book recommendation, our inference and candidate app rule must occupy **separate fields**.

## VI. Reconciliation and recommendation boundaries

Use at least these provisional statuses:

1. **Located:** source/publication identified, not verified.
2. **Extracted:** wording/inputs captured with reliable page/cell anchors.
3. **Checked:** original reference and reported findings verified.
4. **Appraised:** design/bias/heterogeneity/comparators/precision and applicability checked.
5. **Reconciled:** evidence weighed across independent findings and contradictory outcomes.
6. **Proposed:** a *bounded*, testable user-facing policy with uncertainty and exceptions drafted.
7. **Owner approved:** explicit acceptance of the scientific claim's operating conditions, numerical parameters and release scope.
8. **Qualified implementation:** independent program construction, replay, invariants, mode separation and real-device UX tested.

All Batch 01 claims are at step 2–3 **at most**; some source anchors await raw-page validation and external evidence is abstract-level. No numerical parameter has step 7.

A sample proposed rule must identify:
- target population and intended outcome,
- evidence/citation IDs and minimum proof quality,
- permission boundary (Authored advisory only vs explicit Customized program authority),
- context required (actual equipment, source distinction, effort, session length),
- transparent allowed/default/abstain cases,
- robust alternatives when constraints conflict,
- audit/version trace and evidence update/reversal rule.

## VII. Modeling and evaluation phase

A future generator should preserve independence from purchased program topologies. Use original formalized features such as:
- equipment, movement and muscle-action ontology,
- per-muscle intended direct and indirect exposure,
- feasibility and interference of actual selected dates,
- session time/setup/recovery estimates and uncertainty,
- skill/technique constraints, substitutions with reasons,
- consistent multiweek progression and recorded actual outcome comparison.

Test candidate Full Body, Upper/Lower, PPL and hybrid programs across training ages, equipment pools, selected days/time budgets, interruptions, pain/restrictions and explicit priorities. Outcomes should be evaluated with human expert review and, if pursuing superiority claims, prospectively collected valid human outcome evidence; automated property tests certify correctness, not physiological optimality.

## VIII. Security and rights

Research sources live in the owner's private cloud. Do not publish private URLs, entire guides, complete proprietary tables, in-document confidential identifiers, licensing-restricted source bytes or raw training history. The original app's databases and prescriptions remain untouched. Public code/research documentation may contain original paraphrased analyses and DOI/PMID citations.

## IX. Immediate work packages

**Batch 02, source qualification:** validate original PDF page maps and XLSX types for the seven sampled source families and their workbooks; deduplicate editions with hashes.

**Batch 03, full-text science:** inspect P01–P16 and their cited primary RCTs; log formal bias/applicability and full-text conflicts.

**Batch 04, exercise metadata:** region-specific hypertrophy and length/ROM by muscle, exercise mechanics, actual equipment, dose counting and practical split feasibility.

**Batch 05, human-reviewable prototype prescriptions:** construct original schedule-specific examples and a qualification rubric, without altering the runtime until owner approval.
