# Batch 03 — Complete private PDF inventory, deduplication, and edition relationships

**Date:** 2026-10-16. **Status:** original-byte/page metadata verified; not a complete interpretation of every PDF page and not a scientific effectiveness judgment.  
**Machine-readable manifest:** [57 PDFs (SHA-256, bytes, page count and sampled text)](pdf-audit-57.csv). The full copyrighted PDF bytes, extracted manuscript text and private Drive identifiers remain **outside the repository**.

## Exact original-file qualification

All **57 private PDF file references** in the provided `JN` archive were downloaded and checked at their original bytes using streaming SHA-256. PyMuPDF opened every document and reported page count. Text was sampled on first, middle and final pages. One colliding filename (the 3.0 and 1.0 copies of `Technique-Handbook.pdf`) was locally copied to a disambiguated temporary filename for audit; the private originals were not changed.

| Measured fact | Result |
| --- | ---: |
| File references successfully byte-hashed/opened | **57 / 57** |
| Distinct original SHA-256 identities | **50** |
| Exact duplicate SHA groups | **5** |
| Extra duplicate references beyond one per unique file | **7** |
| Total pages across references | **4,557** |
| Total source bytes including duplicates | **2,140,188,036** |
| Distinct-file bytes when each hash counted once | **2,090,543,369** |
| Failed/unopenable/encrypted originals | **0 reported** |
| Image-only suspected from sample-page text | **1 PDF** |

The previous Batch 02 **21-workbook** audit is separate; combined archive size from the initial Drive inventory remains **2,142,492,278 bytes**.

### Duplicate groups confirmed at the original bytes

- **Powerbuilding 2.0 4x Training Manual:** two different filenames but identical SHA-256, 125 pages per reference.
- **Powerbuilding 2.0 5–6x Training Manual:** two filenames, identical SHA-256, 123 pages per reference.
- **Get Ready Manual:** three filenames across Powerbuilding groups, identical SHA-256, 23 pages each.
- **Technique Handbook:** three filenames/copies, identical SHA-256; one pair has a filename collision disambiguated for the audit.
- **Glute Hypertrophy Program:** two locations/names, identical SHA-256, 36 pages each.

These five groups explain exactly **seven extra duplicate references**. Different editions with different hashes are **not** automatically interchangeable.

### Nine specific cross-file page-text comparisons

Normalized each page's extracted text (whitespace/case) and matched page SHA-256 as a multiset. **Text equality is not byte-for-byte PDF page graphics/links/layout equality**; this verifies text inclusion only.

| Compared pair | Full / short page counts | Exact normalized-text page matches |
| --- | --- | --- |
| Upper/Lower vs trimmed | 87 / 59 | 59 / 59 |
| Push/Pull/Legs vs trimmed | 110 / 80 | 80 / 80 |
| Ultimate PPL 4x vs trimmed | 102 / 74 | 74 / 74 |
| Ultimate PPL 5x vs trimmed | 115 / 87 | 87 / 87 |
| Ultimate PPL 6x vs trimmed | 128 / 100 | 100 / 100 |
| Powerbuilding 2.0 4x vs Routine Only | 125 / 90 | 90 / 90 |
| Powerbuilding 2.0 5–6x vs Routine Only | 123 / 88 | 88 / 88 |
| Powerbuilding 1.0 full vs Routine Only | 113 / 79 | 79 / 79 |
| Pure Bodybuilding Phase 2 Full Body vs Phase 1 Full Body | 55 / 55 | 0 / 54 nonempty P1 pages |

**Implication:** trimmed/Routine Only PDFs in the first eight comparisons are text-subsets of their full counterparts, not independent scientific replication. **Pure Bodybuilding Phase 1 and 2 are distinct source programs**, not duplicates; preserve independent Authored provenance. No file, source data or database row was deleted or deduplicated.

### Image-only exercise favorites booklet

`My-Favorite-Exercise-for-Each-Body-Part.pdf` has **14 pages** and yielded no useful embedded PDF text; it cannot be silently treated as an empty scientific source. Five pages were rendered and a few visually inspected as a limited sampling. For example, one page uses a *paused standing calf raise* and another uses *Egyptian cable lateral raises* to explain the author's favorites. These pages emphasize accessibility, technique, user engagement, biomechanics or author's personal preference; **they do not independently establish human hypertrophy outcome superiority**. Do not run OCR as a presumed high-fidelity substitute for original visible page content.

### Interpretation limits

- The hash inventory covers **all 57 original PDF references**, but scientific claims have been extracted only from selected sections. Do not call this a complete 4,557-page scientific appraisal.
- Sample-page text counts can miss image/scanned pages elsewhere in otherwise searchable documents.
- Page text-subset matches do **not** prove identity of hyperlinks, annotations, bitmap artwork, embedded videos or layout.
- Private originals may have copyright or licensing constraints. Do not publish PDF source images, program tables, entire manuals or extracted complete source text into this public repository.

## Operational research policy

Use the **50 unique original PDFs** as the version-resolved source basis, with trimmed editions mapped as short views of a *particular full version* rather than wholly separate studies. Retain full provenance for all 57 file placements in the private library. Read each work's evidence/references independently; never let full vs trimmed copies inflate the apparent number of supporting authors or studies.

The [Batch 03 exercise-selection analysis](batch-03-exercise-selection.md) extends scientific interpretation. All claim status remains provisional; no generator thresholds or rules are activated by this source audit.
