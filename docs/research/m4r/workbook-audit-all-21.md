# Batch 02 extension — All 21 program workbooks, original-byte structural audit

**Date:** 2026-10-16. **Status:** all-workbook **structural** checks completed; content-level exercise prescription interpretation, formula evaluation and source-authority approval **not completed**. All originals remain private. Machine-readable register: [workbook-audit-21.csv](workbook-audit-21.csv). [Core Batch 02 report](batch-02-source-fidelity-and-fulltext.md).

### Source identity correction (2026-10-16)

A same-basename local attachment originally led the audit to count a historical `Pure_Bodybuilding_-_Full_Body.xlsx` reference of **145,847 bytes** (SHA-256 prefix `9a4021f5`) in place of the **143,246-byte** file actually present in the user-supplied `JN` folder (SHA-256 prefix `9d67b025`). The mismatch was discovered by reconciling the Google Drive folder's 21 declared file sizes against the raw working-copy totals and was resolved by fetching the *exact Drive file ID* again. The re-run preserved the same **110** `m\-d` range-formatted cells and **0** formula cells for that workbook but counted **721**, rather than **924**, numeric cells. The resulting all-21 totals are corrected above. The historic workbook and archive workbook are **different source identities**; no equivalence of their exercise content has been established, and the deployed Authored importer/source must not be rewritten as if the files were interchangeable.

The 21-file raw-size sum now matches the exact archive metadata: **2,140,188,036 PDF bytes + 2,304,242 XLSX bytes = 2,142,492,278 bytes**.

## Scope and results

The 21 archived XLSX files were retrieved by their original authorized Drive identities and inspected **locally as original ZIP/Office Open XML source**, not through lossy CSV projections. No third-party OCR and no assumption that a text converter displays training-range cells correctly. SHA-256 calculated for each original byte sequence; `xl/workbook.xml`, `xl/styles.xml`, and every `xl/worksheets/sheetN.xml` were parsed.

| Measured structure | Count |
| --- | ---: |
| Raw XLSX files located and opened | **21 of 21** |
| XML worksheets present | **30** |
| Total original bytes (corrected exact archive) | **2,304,242** |
| Numeric-format cells in worksheet XML (corrected) | **22,587** |
| Numeric cells formatted custom `m\-d` | **3,771** |
| Formula cells | **460** |
| Error-type cells stored in source XML | **0** |
| Other numeric date-formatted cells under the surveyed formats | **0** |
| Exact duplicate SHA-256 workbooks | **0** |
| Missing files, corrupt ZIPs or worksheet-count discrepancies | **0** |

**These counts do not prove that 3,771 cells are semantically broken.** Many originally display intended ranges such as 8–10 reps, 2–3 warm-ups, or 9–10 target RPE by using an Excel serial number plus a custom date-like display format. The original Excel workbook may display correctly; a tool that treats the serial as a *calendar date* misinterprets the training cell.

### Illustrative original-cell verification

From *Essentials 4x*'s first worksheet:

- `D5`: raw number 44595 with custom `m\-d` → formatted `2-3` warm-up sets; generic text projection can show `2022-02-03`.
- `H5`: raw number 44782 with custom `m\-d` → `8-9` RPE; generic projection can show `2022-08-09`.
- `H6`: raw number 44814 with custom `m\-d` → `9-10` RPE; generic projection can show `2022-09-10`.

From *Pure Bodybuilding Phase 2 Full Body*, examples include a warm-up range (D80, `2-3`) and a rep range (F80, `8-10`). Reconstructed display is conditional on confirming the XLSX 1900 date system, custom cell formatting and correct surrounding source column headings. **Do not make a global `date→range` transformation without per-field validation.**

### The 460 formulas are another independent trap

Formula cells are concentrated in **six** workbooks:

| Source group | Formula count |
| --- | ---: |
| High-frequency Full Body 4x / 5x | 67 / 68 |
| Powerbuilding 2.0 4x / 5–6x | 76 / 76 |
| Powerbuilding 3.0 | 87 |
| Powerbuilding 1.0 6x | 86 |
| **Total** | **460** |

Every formula examined had a stored cached value, but a cached result does **not** guarantee the formula has been freshly calculated for the intended user inputs. The formulas include `IF` branches selecting kg/lb and `MROUND` calculations based on input cells. They therefore represent **conditional training guidance** dependent on user baseline and declared units, not immutable authored numerical loads. The formula checks found **no external workbook-link syntax, explicit `#REF!`/`#VALUE!` formula text or stored Excel error-type cells** in this scoped structural scan. No formula execution/validation against all inputs was performed.

Source models must distinguish:
- immutable author targets (sets, reps, effort, techniques, substitution options);
- editable user calibration/1RM or training baseline;
- formula-evaluated suggested load tied to inputs and equipment/units;
- a potentially stale formula **cached** value that must not be mistaken for the source's fixed prescription;
- absent versus literal zero versus intentionally textual/AMRAP instructions.

**Nothing here demonstrates a deployed app bug.** It establishes import hazards and a concrete future regression corpus. The production Authored source versions require independent exact-cell-to-compiled-artifact comparison before a corrective patch.

### Workbook distribution and edge cases

- Four worksheets occur in *The Essentials Program.xlsx*; three worksheets occur in each Ultimate PPL 4x/5x/6x workbook. Treat each original worksheet independently, and don't assume every XLSX has only one routine tab.
- Custom `m\-d` formatting is present in many Essentials, Pure Bodybuilding, PPL and Powerbuilding workbooks, but absent from both high-frequency Full Body 4x/5x and the Essentials base file. The problem is **not universal across all workbooks**.
- All surveyed workbooks use the 1900 Excel date system. The custom format's mere existence is not sufficient to decide whether a cell is a range; column and author instructions remain governing.
- Each of the 21 workbook SHA-256 fingerprints is distinct. A trimmed PDF or other workbook not in this 21-file set may still be textually redundant; identity/near-duplicate testing of the **57 PDFs** remains separate.

## Recommended importer qualification, not an implementation authorization

For a subsequent independently reviewed import tool:

1. Verify the exact source hash and workbook edition, then enumerate all worksheets and their lineage; do not collapse similar names.
2. Parse original cell raw values, cell types, number formats, formulas, cached values, units, context and merged headers. Use one declared versioned rule for `m\-d` displayed training ranges.
3. Mark a value as a fixed authored target only when its source meaning is demonstrated. Preserve formulas and dependencies separately from immutable targets.
4. Admit `2-3`, `8-10`, `9-10`, AMRAP, bare zero, missing cells and numeric decimal zeros as distinct test fixtures; compare the source display, typed semantic meaning and compiled app output.
5. Keep Authored Plans as source-owned, and apply newly researched general principles only to independently constructed, opt-in Customized workouts.
6. Run isolated importer/parity tests with private source files in an authorized environment. Never use copyrighted source files as public CI fixtures, never reset production data to qualify parsing, and do not infer author approval from successful parsing.

This audit is an **R2 structural milestone** for the research corpus, not a declaration that every set, program week, exercise, RPE, load or equipment instruction has been correctly extracted or scientifically endorsed.
