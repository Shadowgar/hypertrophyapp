# M4-R — Independent workout-generation science research

**Status:** Research-only, provisional; no new workout programming policy is approved.  
**Snapshot:** 2026-10-16.  
**Scope:** Scientific foundations for **Customize My Workout**, independently of the immutable Jeff Nippard Authored Plan families.

## Why this exists

The future generator must create original full-body, upper/lower, PPL and other feasible programs from evidence-based principles, athlete preferences, equipment, constraints, and actual dates. It must **not** clone a proprietary training program, infer scientific superiority from marketing labels, or activate new numerical prescriptions before evidence and owner review.

Existing Authored Phase 1/2 source prescriptions and workout histories remain unchanged. This research branch contains **no application code or migration**.

## Source corpus reviewed and indexing status

A user-supplied private Google Drive archive named `JN` was enumerated on 2026-10-16, including nested folders:

| Corpus inventory | Count |
| --- | ---: |
| Folders enumerated, including root | 18 |
| Files enumerated | 78 |
| PDFs | 57 |
| XLSX workbooks | 21 |
| Combined reported file sizes | 2,142,492,278 bytes (~2.142 GB, ~2.00 GiB) |
| Folder-listing truncations/errors reported | 0 |

Collections include Pure Bodybuilding Phase 1/2, Ultimate PPL and other PPL, Powerbuilding, Fundamentals, Essentials, high-frequency Full Body, Upper/Lower, body-part specialization, strength, return-to-training and other manuals. **A complete listing is not a complete raw-file/hash or full-text validation.** Some editions and trimmed PDFs may be duplicates. One nested PPL folder was empty when enumerated.

**Update through Batch 03 (2026-10-16):** All **57 PDF byte streams have been SHA-256 verified and opened**, comprising **50 unique PDF hashes**, five exact duplicate groups and 4,557 page references. The **21 XLSX workbook identities and counts were rechecked against the exact shared folder**, correcting a same-basename Phase 1 source collision (archive copy 143,246 bytes vs the 145,847-byte historical catalog version). Eight trimmed/routine-only pairings were verified as full-text-page subsets of the corresponding complete manuals. All **21 XLSX workbooks** have been separately byte-hashed and structurally inspected. **Neither verification amounts to a complete scientific interpretation of every source page/cell.**

Seven high-priority manuals were read at selected sections through Google Drive's text extraction in the pilot: Fundamentals, Pure Bodybuilding handbooks Phase 1 and Phase 2, Comeback Bridge, Upper/Lower, Ultimate PPL 4X, and Essentials 4x. Program workbooks were sampled but **not** admitted as exact raw-cell evidence: one connector text projection rendered numeric load/RPE-like fields as dates. Their original types/formats must be checked before any quantitative source extraction.

**Private-source boundary:** No purchased PDF/XLSX source bytes, substantial excerpts, user Drive credentials/IDs, or private download links belong in this public repository. File names and short original paraphrases are for provenance only. The private archive remains in the owner's Drive.

## Research artifacts

- [Batch 01: source-to-science comparison](batch-01-source-to-science.md): individual hypotheses, Nippard source anchors, independent scientific findings, limitations and *nonbinding* programming implications.
- [Batch 02: raw-file fidelity and full-text methods review](batch-02-source-fidelity-and-fulltext.md): original PDFs/pages, OOXML cell formatting traps, historical citation validation and four full-text scientific assessments.
- [Batch 02 raw-source register](source-audit-batch-02.csv): verified source SHA-256/byte identity and page anchors for the first five files.
- [All 21 workbooks: structural audit](workbook-audit-all-21.md) and [metadata CSV](workbook-audit-21.csv): original file hashes, worksheet counts, 3,771 range-format cells and 460 formulas. **Not** full source-semantic qualification.
- [Batch 03 PDF verification](pdf-source-audit-all-57.md) and [57-PDF source fingerprint register](pdf-audit-57.csv): all original PDF hashes, duplicate editions and shortened-view mapping.
- [Batch 03 exercise-selection science](batch-03-exercise-selection.md): head-/muscle-specific comparisons, exercise variation, source preferences versus comparative outcomes and unresolved evidence.
- [Batch 04: original Customized program design standard](batch-04-customized-program-design-standard.md): source-versus-evidence boundaries, hard constraints, and acceptance scenarios for Full Body, Upper/Lower, PPL and rolling schedules; **not an approved prescription**.
- [Research protocol](protocol.md): appraisal workflow, evidence hierarchy, source licensing, scope and approval gates.
- [Claim register](claims.csv): machine-readable status for research tasks; **never consume this CSV as runtime prescription rules.**

The prior `docs/guides/asset_catalog.json` records 46 metadata-only assets from an earlier ingestion phase. Those records are not evidence that all 46 were fully extracted or that this new 78-file archive has been validated. Do not combine source counts without raw-byte hashing and edition reconciliation.

## Evidence-status terminology

- **Source observed:** a publisher/program claim was located in a supplied document; truth is not established.
- **Literature identified:** an external review/trial was located and its abstract checked.
- **Preliminary reconciliation:** a limited comparison was performed; formal appraisal outstanding.
- **Appraised:** verified full text, design, bias, applicability, overlapping evidence and uncertainty.
- **Approved:** the owner has separately accepted a bounded versioned policy and tests.

Batch 01–03 claims remain provisional. Raw byte identity/page counts for **all 57 PDFs** and original OOXML structural features of **all 21 XLSX workbooks** are verified. Selected program sections and eligible scientific full texts have been examined, including exercise-specific comparisons. **This does not certify every source page/cell's intended programming semantics, all cited scientific studies, full supplemental tables, independent review or any numerical recommendation.** No review has been registered or independently double-screened; neither abstracts nor limited full-text examinations justify confident GRADE ratings.

## Non-goals and prohibitions

1. No generated workout engine, numerical rules, automated AI prescription or live training-state changes in this PR.
2. No source programs copied as disguised independent programs.
3. No implicit consent to convert an Authored plan into Customized mode.
4. No "optimal" ranking of split names without comparative outcome evidence and conditions.
5. No copying of paid source tables/manual content into public docs, tests or model outputs.

## Release pathway

Research observation → raw-source/page verification → bibliography validation → systematic searches → full-text critical appraisal → reconciled evidence statement → candidate generator rule → independent subject-matter review → explicit owner decision → deterministic tests → separate implementation PR.

**Research publication is not owner acceptance of a training recommendation.**
