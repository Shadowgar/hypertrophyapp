# Batch 03 — All-PDF source audit and exercise-selection evidence

**Date:** 2026-10-16. **Status:** original-file verification complete for the 57 PDFs; targeted exercise-science appraisal is preliminary. This is research only, with **no approved new prescription rule**, application change, migration, or production workout-history operation.

## 1. Raw source audit: 57 of 57 PDFs

All 57 PDF references in the user's private training archive were obtained as original bytes and opened; no download/parse errors occurred. We recorded private per-file SHA-256, byte size, PDF page count and sampled PDF text metadata. Original source bytes, original program tables, full program text and private Drive URLs are **not** committed to GitHub.

| Metric | Count |
| --- | ---: |
| PDF references opened | **57** |
| Unique PDF byte hashes | **50** |
| Redundant references | **7** |
| Exact duplicate clusters | **5** |
| PDF pages across all references, including duplicates | **4,557** |
| PDF bytes across references, including duplicates | **2,140,188,036** |
| Files flagged as primarily image-only from sampled page text | **1** |
| File/open/parse errors | **0** |

**Duplicate identities established by exact original-file SHA-256** (members below are separate archive references, not separate studies):

- Powerbuilding 2.0 4x manual: `4X - Training Manual.pdf` and `Powerbuilding 2.0 -  Training Manual - 4X.pdf`.
- Powerbuilding 2.0 5–6x manual: `5-6x - Training Manual.pdf` and `Powerbuilding 2.0 - Training Manual - 5-6X.pdf`.
- Get Ready manual: `Get Ready Manual.pdf`, `Get-Ready-Manual-Powerbuilding.pdf`, `Get-Ready-Manual.pdf`.
- Glute guide: `Glute Hypertophy(men & women).pdf` and `Jeff Nippard_s Glute Hypertophy(men & women).pdf`.
- Technique handbook: `Technique Handbook.pdf`, `Technique-Handbook.pdf`, `Technique-Handbook_3.0.pdf`.

**The 50 unique hashes are file-level identities, not necessarily 50 independent training systems, scientific papers or unique authored programming logics.**

### Near-duplicate, trimmed and routine-only comparisons

Original full manuals and trimmed/routine-only variants have **different byte hashes**. We checked whether every *text-bearing* page of the shorter edition had a corresponding normalized-text page in the full edition:

| Source pair | Full pages | Short edition pages | Short-edition text pages matched |
| --- | ---: | ---: | ---: |
| Upper/Lower full → trimmed | 87 | 59 | 59 / 59 |
| PPL full → trimmed | 110 | 80 | 80 / 80 |
| Ultimate PPL 4x full → trimmed | 102 | 74 | 74 / 74 |
| Ultimate PPL 5x full → trimmed | 115 | 87 | 87 / 87 |
| Ultimate PPL 6x full → trimmed | 128 | 100 | 100 / 100 |
| Powerbuilding 2.0 4x full → routine-only | 125 | 90 | 90 / 90 |
| Powerbuilding 2.0 5–6x full → routine-only | 123 | 88 | 88 / 88 |
| Powerbuilding 1.0 full → routine-only | 113 | 79 | 79 / 79 |

This demonstrates **normalized text inclusion for the compared pages**, not byte-for-byte equivalence, proof that all page graphics are identical, or proof that version metadata/annotations are identical. For scientific claims use full editions first, and retain the shorter edition as an archival alternative. Do not count the trimmed version as an independent source publication.

A separate comparison of Pure Bodybuilding Phase 1 versus Phase 2 full-body editions matched **0/54 text-bearing pages**; they are distinct editions and must not be collapsed as duplicates.

### Image-only review exception

`My-Favorite-Exercise-for-Each-Body-Part.pdf` contains **14 pages** and lacked extractable text in the sampled pages. Page renders exist for manual visual inspection, but the document **has not been converted into a verified text-and-citation index**. Do not claim that its guidance has been read exhaustively or score images as evidence without inspecting the page. OCR is not an automatic substitute for author-verifiable source content.

## 2. What newer research actually supports about exercise choice

The sources below were retrieved by PMID with titles, publication dates and abstracts. **This subsection is an abstract-level evidence screen**, not full-text risk-of-bias appraisal or an approved dose/exercise ranking.

### E17 — Controlled versus varied exercise selection

Kassiano et al., 2022 systematic review, [PMID 35438660](https://pubmed.ncbi.nlm.nih.gov/35438660/): eight studies, 241 **young men**. The authors suggest some systematic variation may influence region-specific hypertrophy, but frequent random/redundant exercise changes can interfere with progress. The conclusion is not proof that more exercise variation always grows more muscle, particularly in women, older adults or beginners.

A later 2025 randomized comparison in **70 young women**, [PMID 39388663](https://pubmed.ncbi.nlm.nih.gov/39388663/), tested constant exercise selection versus a deliberately varied set of lower-body exercises during 10 weeks. Muscle thickness and strength outcomes were similar across the two conditions. The protocol compared specific lower-body menus; no inference about every split or whole-body program follows.

**Preliminary reconciliation:** Consistent exercises provide comparability and practice; deliberate variation can address different muscles/angles or user constraints. No universal weekly-rotation bonus is supported. This is a reason to design exercise stability into a multiweek generator, not to forbid all variation.

### E18 — Hamstrings can respond differently to different movements

Maéo et al., 2021 seated versus prone leg-curl within-person trial, [PMID 33009197](https://pubmed.ncbi.nlm.nih.gov/33009197/): 20 healthy adults trained each leg with a different curl position for 12 weeks. MRI-measured whole-hamstrings muscle-volume changes were larger for seated than prone in the studied protocol (**14% versus 9%**). This is not proof that seated curls are always optimal, that a difference applies identically to all muscle heads or that any stretched-position technique is superior to every alternative.

A September 2026 experimental/modeling study, [PMID 42735209](https://pubmed.ncbi.nlm.nih.gov/42735209/), reported that Nordic hamstring and stiff-legged-deadlift interventions preferentially affected different hamstring muscles. EMG-informed predictions of muscle-specific outcomes were promising but do not validate a universal mechanical ranking of all exercises.

**Preliminary reconciliation:** A future exercise database should distinguish specific muscle groups and actions (e.g., hamstring hip extension vs knee flexion), not simply label every hinge and curl "hamstrings = 1.0". Muscle-specific evidence remains limited.

### E19 — Do not turn "long-muscle-length" into a magic score

A December 2025 Bayesian systematic review/meta-analysis, [PMID 40570881](https://pubmed.ncbi.nlm.nih.gov/40570881/), combined 12 studies comparing longer- versus shorter-length training for regional hypertrophy. Average differences were small, and practical-equivalence regions were substantial; the authors caution that length contrasts were relatively modest.

**Preliminary reconciliation:** Distinguish full-range repetitions, long-length exposure, lengthened-only partials, and lengthened-position technique extensions. A mechanistic label alone is insufficient to assert a muscle-growth advantage.

### E20 — Sex-specific outcomes should not be inferred from source-book labels

A 2025 Bayesian meta-analysis, [PMID 40028215](https://pubmed.ncbi.nlm.nih.gov/40028215/), synthesized 29 studies with men and women following the same interventions. Relative muscle-size changes were similar on average, while some absolute changes differed. This neither eliminates individual differences nor validates automatic sex-based set multipliers.

**Preliminary reconciliation:** Customize based on observed ability, preferences, exercise accessibility and response, not unsupported assumptions from a "women's program" or "men's program" filename.

## 3. Consequences for original Customize My Workout design

These are **future research hypotheses, not authorized executable workout rules**:

1. Maintain a stable set of comparable primary exercise anchors over meaningful time windows; vary exercises deliberately for anatomy, equipment, pain/constraints or user intent, rather than randomly each week.
2. Model muscles and functions, not only movement labels. Store target/secondary muscles, joint actions, loading context, skill, equipment and the **strength of evidence** linking that movement to specific outcomes.
3. Distinguish quantitative **workload exposure models** from proven physiology. A half-credit compound set or invented "muscle-stimulus score" must be clearly labeled an assumption until validated.
4. Keep plan goals distinct: hypertrophy, strength, power, time efficiency, re-entry and adherence cannot be optimized using an unproven universal ranking.
5. Keep Authored programs faithful to their purchased source regardless of newer research. Source-authorized substitutions are not necessarily equivalent to arbitrary generated replacements.
6. A user's preference for Full Body, Upper/Lower or PPL is a design constraint when feasible—not a scientifically proven performance penalty.
7. Require prospective human expertise and user-outcome evaluation before superiority claims; tests of code invariants and synthetic programs prove software properties, not muscle-growth outcomes.

## 4. What remains

- **Technical source indexing:** Exact SHA inventory is privately held; expose no source binaries. Validate figure-only pages and source-title/license details before using them as evidence. Original workbook parsing was structurally audited in Batch 02 but not fully semantically transcribed.
- **Scientific evidence:** Retrieve available full text, check bias, population, muscle-measurement validity, certainty, volume equating and actual intervention adherence, especially for E17–E20. Compare related recent randomized studies and conflicting results. Avoid double-counting overlapping trials in meta-analyses.
- **Product qualification:** Draft original sample programs *only* after a scientific design rubric is reviewed. Do not implement, activate, or self-approve a new program generator based on this preliminary research.

**Batch 03 conclusion:** The archive is file-level accounted for and accurately deduplicated. Evidence strongly motivates **anatomy-aware, stable, constraint-driven program construction** as an engineering design direction; it does **not** establish a universal optimal exercise list or algorithmic hypertrophy score.
