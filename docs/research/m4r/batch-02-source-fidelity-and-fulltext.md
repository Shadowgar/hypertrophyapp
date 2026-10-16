# Batch 02 — Raw source fidelity and methods-level scientific verification

**Date:** 2026-10-16. **Research status:** partial original-source verification plus selected full-text literature examination; **not** a registered systematic review, independent risk-of-bias review or approved workout-generation policy.

**Scope:** This report extends [Batch 01](batch-01-source-to-science.md) without modifying any application, Authored Plan, prescribed source data, training history or production server. Private source PDFs/XLSX remain **outside Git**. See [machine-readable source register](source-audit-batch-02.csv).

## 1. What was actually verified, and what wasn't

We retrieved original raw bytes (not only connector-rendered text) from five owner-supplied training documents, inspected file signatures/sizes and recorded SHA-256 hashes. Two PDFs were opened directly using a PDF page renderer, and three XLSX workbooks were read at the underlying Office Open XML cell/style level. Two PDF manuals were partially verified by checking specific original physical pages; **we did not inspect every page or validate the whole 78-file archive**.

| Source | Raw verification | Result |
| --- | --- | --- |
| Fundamentals Hypertrophy Program.pdf | 12,347,651 bytes, 97 physical pages; PDF pp.84–86 examined/rendered | Physical page numbers match printed pages; frequency, effort and volume text confirmed |
| Comeback Bridge Program.pdf | 2,686,817 bytes, 43 physical pages; PDF p.6 examined/rendered | Re-entry instruction varies by extent/type of prior training |
| Essentials 4x.xlsx | 163,243 bytes; raw workbook cell values/types and number formats checked | 232 numeric cells have the custom Excel `m\-d` format |
| Pure Bodybuilding Phase 2 Full Body.xlsx | 167,265 bytes; raw cell/style inspection | 460 numeric cells have the same custom format |
| Pure Bodybuilding Phase 1 Full Body.xlsx | 145,847 bytes; raw cell/style inspection | 110 numeric cells have the same custom format |

**802** custom `m\-d`-formatted numeric cells were found across these three tested workbooks. This count records formatting, **not 802 proven incorrect prescriptions or 802 distinct semantic mistakes**. Many encode displayed *ranges*, but each needs context-specific interpretation.

The historical `docs/guides/asset_catalog.json` metadata SHA-256 exactly matched raw bytes of the two Pure Bodybuilding full-body XLSX files and Comeback Bridge PDF. This verifies their byte identity to three catalog entries, **not** that the prior metadata-only extraction ever interpreted their data properly. The retrieved Fundamentals and Essentials 4x raw hashes did not match entries in that earlier catalog; a similarly titled edition must not be assumed identical.

### Critical workbook finding: training ranges masquerading as dates

Excel's `m\-d` display format is applied to numeric serials in source workbooks. An unsophisticated reader can represent these as calendar dates, losing the intended original displayed training range. Examples from the **raw Essentials 4x.xlsx**:

| Original cell | Underlying numeric XML value | Original number format | Correct display context | Wrong generic date interpretation |
| --- | ---: | --- | --- | --- |
| D5 (warm-up sets) | 44595 | `m\-d` | `2-3` | `2022-02-03` |
| H5 (RPE) | 44782 | `m\-d` | `8-9` | `2022-08-09` |
| H6 (RPE) | 44814 | `m\-d` | `9-10` | `2022-09-10` |

In Pure Bodybuilding Phase 2, for example, formatted repetitions and warm-up ranges include F80 (45514 -> `8-10`) and D80 (45325 -> `2-3`). Phase 1 includes date-styled warm-up ranges such as D59. Do not treat `2022-08-09` as a workout date or treat 44782 as numeric effort. **The Excel workbook isn't necessarily wrong; naive conversion is wrong.**

The correct parser must combine original **cell type, raw value, number-format code, field column, source context, workbook date system, and original displayed semantics**. In particular, do not blindly convert every date-formatted field to a training range; a different sheet might contain a genuine date. Preserve raw-cell provenance and flag unresolved cases for review.

This is a **research-pipeline ingestion hazard**, not a demonstrated production-app defect. Existing imported Authored rows require independent parity tests against source artifact semantics before any code change.

### Original-page source anchors confirmed

- **Fundamentals, physical PDF p.84:** frequency discussion citing source reference `[17]` and practical distinction between equal-volume comparisons and real-session dose distribution.
- **Fundamentals, physical PDF p.85:** training status and actual-effort guidance; beginners and trained participants are not given the same effort framework.
- **Fundamentals, physical PDF p.86:** weekly training volume, caveat that adding more isn't always productive and a historical ballpark rather than individualized optimum; source references `[18–21]`.
- **Fundamentals, physical PDF p.94:** reference `[17]` is Schoenfeld, Ogborn, Krieger 2016 on resistance-training frequency (PMID [27102172](https://pubmed.ncbi.nlm.nih.gov/27102172/)).
- **Fundamentals, physical PDF p.95:** reference `[21]` is Schoenfeld, Ogborn, Krieger 2017 on weekly volume (PMID [27433992](https://pubmed.ncbi.nlm.nih.gov/27433992/)).
- **Comeback Bridge, physical PDF p.6:** distinguishes near-complete detraining, partial training and continued heavy training. Its exact short bridge is a *source protocol*, not yet proven a general optimum.

These source positions were checked against raw, rendered physical pages or per-page text; remaining workbook cells, source-reference mapping and other manuals still need full verification. We reproduce only original paraphrases, not the copyrighted program pages.

## 2. Nippard's older citations were genuine evidence, not invented doctrine

The historical Fundamentals frequency recommendation is based on a **2016 meta-analysis of 10 studies** (PMID 27102172), which reported a statistically significant aggregate difference when comparing different per-muscle frequencies under its inclusion criteria. A 2017 dose-response meta-analysis (PMID 27433992) analyzed **34 treatment groups from 15 studies** and found an aggregate positive volume association.

These are defensible **historical** evidence foundations. They should not be called fabricated or dismissed because the reference dates are old. They also do **not** justify freezing their interpretations as universal rules in a 2026 generator.

The newer 2026 meta-regression (PMID [41343037](https://pubmed.ncbi.nlm.nih.gov/41343037/)) analyzes 67 studies/2058 participants with a different dose and fractional-indirect-set model, indicating volume gains with diminishing returns and an uncertain independent hypertrophy effect of frequency. Comparison across different studies, models and literature dates is *reconciliation*, not a direct trial of Nippard's programs. The 2024 split/full-body review (PMID [38595233](https://pubmed.ncbi.nlm.nih.gov/38595233/)) likewise does not prove universally identical outcomes.

**Research disposition C01/C02:** The original source recommendation has a trackable primary review rationale; evidence updates **weaken any universal frequency mandate or one-size set count**, but don't establish that frequency or high-volume programming never matters for a particular user. **No new numerical rule approved.**

## 3. Four research papers read at full-text level

All **four PMC full texts** below were accessible under provider-checked retrieval permissions, and their full bodies were obtained across nonoverlapping paginated text offsets. Selected methods, results and limitations were examined. This is **not** independent RoB 2/AMSTAR 2 scoring, exhaustive extraction of supplemental tables, or a completed full systematic-review process.

### E01 — ACSM 2026 resistance-training position stand

[PMID 41843416 / PMC12965823](https://pmc.ncbi.nlm.nih.gov/articles/PMC12965823/)

- An overview of **137 systematic reviews**, over **30,000** participants across their reported reviewed studies. Its own literature search ran **through October 2024**, despite publication in April 2026.
- The full text says training itself improves strength/hypertrophy versus not training, while fewer manipulation variables offer consistent incremental benefits.
- **Key limitation from full text:** overlapping primary studies across reviews were quantified using corrected covered area for *strength*, **not** other outcome families including hypertrophy. The authors explicitly warn that reviews can share included trials and that an overview of reviews cannot determine comparative effectiveness of complete interventions.
- They additionally caution that benefits are group-level and individualization/adherence matter.
- **Disposition:** Anchor high-level scientific framing; do **not** treat the number of reviews as independent replicated trials, or derive a globally optimal Full Body/PPL program from this position stand.

### E02 — 2024 inter-set-rest Bayesian systematic review

[PMID 39205815 / PMC11349676](https://pmc.ncbi.nlm.nih.gov/articles/PMC11349676/)

- Included **nine randomized training studies** with heterogeneous muscles, exercises and assessment methods.
- Pairwise effects broadly pointed toward a small advantage of longer versus very short rest for certain site-specific outcomes, with imprecise credible intervals. Whole-body proxies included non-muscle components of fat-free mass.
- The full-text limitations acknowledge substantial heterogeneity, limited direct comparisons across all rest categories, uncertain applicability by training status and exercise type.
- **Disposition:** Supports maintaining appropriate performance recovery and avoiding a universal extremely short timer. Does **not** determine a unique optimal 90-, 120- or 180-second rest for each exercise.

### E03 — 2026 advanced-training network meta-analysis/review

[PMID 41951916 / PMC13457283](https://pmc.ncbi.nlm.nih.gov/articles/PMC13457283/)

- Its review searched literature in June 2024 and updated through **October 2025**. Despite the title, **a network meta-analysis for hypertrophy could not be run**: the hypertrophy network lacked enough studies across methods for the paper's minimum-node rule.
- Most included samples were not highly trained: where a training age was reported, the average was **about 1.9 years**. Several studies were assessed as `some concerns` or `high risk`; interventions varied by dose and load.
- The authors discuss inconsistent muscle-specific results and limitations of direct comparisons.
- **Disposition:** Do not give advanced methods a general hypertrophy superiority multiplier. **Crucially, do not misstate this paper as a formal pooled network result that proves equivalence among all hypertrophy methods.** This is a sparse-comparison limitation.

### E04 — 2026 drop-set systematic review/meta-analysis

[PMID 41920484 / PMC13043944](https://pmc.ncbi.nlm.nih.gov/articles/PMC13043944/)

- The 12-study sample includes acute and chronic outcomes. Chronic analyses comprised **16 comparisons nested in nine studies**; pooled hypertrophy contrast was SMD **0.04** with **95% CI −0.29 to 0.36**.
- The full text reports greater acute **perceived exertion** during drop sets. Acute stress is not itself proven to cause superior long-term hypertrophy.
- **Reporting-quality caution:** The results section reports significant pooled lactate increases while an end-conclusion passage states lactate (alongside heart rate) lacked significant pooled differences. The reported fixed-effect lactate line also appears internally inconsistent between its CI and p value. These discrepancies merit verification against figures/supplement and possible corrections; don't lift lactate effect sizes into our policy registry.
- **Disposition:** Drop sets can be considered a time-saving tool with fatigue trade-offs. The reported non-significant hypertrophy contrast does **not** establish rigorous equivalence for every population, volume or program length.

## 4. Exact implications for future independent workout design (research proposals only)

| Future design dimension | Supported direction | Explicitly blocked inference |
| --- | --- | --- |
| User-selected Full Body / Upper-Lower / PPL | Evaluate schedule, equipment, work distribution, history and preference | "PPL grows X% more muscle" from a split label |
| Weekly workload | Count both direct/indirect exposure with disclosed classification; acknowledge diminishing returns | "Every lifter needs exactly 10/15/20 sets" |
| Frequency | Fit workload into recoverable, repeatable high-quality sessions | Immutable at-least-twice-per-muscle optimum claim |
| Failure/effort | Distinguish beginner calibration from qualified experienced effort | RPE 10 all sets because one source block uses it |
| Rest | Allow sufficient recovery and time-budget trade-off | A source stopwatch value is optimal across all exercises |
| Long-length/partials | Distinguish trained length, full-ROM alternative and beyond-failure extensions | Every partial technique is superior to full-ROM |
| Advanced methods | Conditional practical tools rather than magic hypertrophy scores | "The network meta-analysis proved the best advanced method" |
| Multiweek plans | Stable, repeatable logs and reasoned changes; manage accumulated work | Guaranteed hypertrophy supercompensation from an arbitrary high-volume phase |
| Original program sources | Preserve raw source in private storage and keep Authored reproduction governed by source | Copy copyrighted workouts into a generic `Customize My Workout` generator |

## 5. Research-quality gates remaining

This work **does not** approve any new training threshold. Before proposing generator rules:

1. Complete original XLSX cell/style/formula checks for all **21** archived workbooks, not just sampled three, and record suspicious date formats, formulas, source row/column identities and normalized *display strings* with provenance. Do not assume a calendar date or convert a display range to an actual workout date.
2. Reconcile the **57 PDFs** by SHA-256; differentiate exact duplicates from trimmed editions. Record actual physical/printed page mapping on citation-bearing chapters; inspect images where diagrams/tables are the evidence.
3. Trace each Nippard referenced scientific paper against DOI/PMID, full text or publisher abstract, publication date, population, exposure and directly reported outcome. Preserve positive and contradictory evidence.
4. Complete an independent paper-by-paper risk-of-bias/quality assessment and avoid double-counting reviews' overlapping RCTs. Evaluate the limited comparisons for lengthened-partials, load/repetition schemes, muscle-specific exercise choice, age/sex and training experience.
5. Produce original candidate program blueprints *only after* research reconciliation and a formal owner-approved qualitative/non-numeric design standard. Human expert and prospective evidence are required before stronger superiority claims.

**No production data was accessed, modified, reseeded, wiped or reset. No application source, runtime policy, database schema or Authored prescription has been changed by this research.**
