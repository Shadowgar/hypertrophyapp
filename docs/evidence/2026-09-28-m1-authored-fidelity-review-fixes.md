# M1-A review-fix qualification

Status: owner-authorized PR #41 correctness candidate, awaiting fresh review and
the separately authorized merge/activation. No milestone, ADR or release acceptance.
Parent: `6d835db4d0511b4eed360e6dfef6ed550ef48fc4`. This record is pinned to
`b8a992cfeca22d2fda855483d3fdc967e0585b1b`; that commit and
[manifest](2026-09-28-m1-authored-fidelity-review-fixes.manifest.json) bind this
correction snapshot. [Summary follow-up](2026-09-28-m1-bodyweight-summary.md)
records the next corrections. [Original qualification](2026-09-28-m1-authored-fidelity.md)
remains pinned to its earlier revision rather than being relabeled as a final run.

## Corrected boundaries

Today renders the raw authored warm-up count/range independently of calculated
warm-up steps. Counts such as 2 and 2–3 remain visible without invented percentages,
reps or loads. The source-to-runtime tests retain the raw value through every stage.

Explicit authored bodyweight semantics travel through canonical and companion
artifacts, loader, scheduling, Today and history. Restored Phase 2 AMRAP pushups
recommend zero external load and display Bodyweight. The runner accepts actual
reps with no invented external weight. Zero-load log/correction requests are
allowed only for explicit authored bodyweight context; ordinary external-load
exercises still reject zero before persistence or voiding. Bodyweight receipts
retain actual weight and frozen semantics without entering numeric load progression.
This is a bounded compatibility fix, not M2 load/exposure qualification.

Weekly-review exclusion uses exercise occurrence identity, with source-slot
lineage as fallback, instead of excluding every matching catalog exercise.
Numeric occurrences sharing a primary exercise with typed targets remain eligible
for numeric fault classification. Ambiguous legacy receipts are counted but are
explicitly excluded from numeric classification rather than assigned an invented
cohort. Existing numeric aggregation policy is otherwise retained.

The newly introduced CI collection failure is corrected by explicitly adding
the repository root before importer imports in both new test modules. Tests no
longer depend on collection order or CI including the root in PYTHONPATH.

## Results and limits

All Python procedures used copied source, cleared environments, socket/database
guards, explicit disposable SQLite URLs and temporary logs. The two authorized
workbooks were copied read-only; neither source was changed or published. Node
procedures used isolated dependencies and a network guard. No application tests
ran from the production checkout. Raw outputs and harnesses remain temporary owner
evidence outside Git; their hashes do not imply durable public availability.

| Procedure | Result | Limit |
|---|---|---|
| Independent source → importer → canonical → loader → execution/Today | Passed within selected API run | 315 Phase 1 and 310 Phase 2 rows; raw warm-ups, distinct set reps/effort/rest/techniques and lineage retained. |
| Phase 2 AMRAP slots | Passed | Five slots, weeks 6–10, two working sets each, nonnumeric targets, bodyweight semantics and zero external recommendation. |
| Selected source/typed/occurrence/correction/session API tests | 56 passed, 6 skipped, 1 baseline failure | PostgreSQL-only history cases skipped; generated fourth-exercise substitution-guidance baseline remains. |
| Final standalone typed/load boundaries | 13 passed | Includes ordinary numeric external-load zero rejection and frozen correction/history context. |
| Complete core suite | 368 passed, 4 baseline failures | Same set-normalization, legacy count merge and two muscle-coverage failures; before the additional source-slot fallback test. |
| Final authored core boundaries | 4 passed | Mixed occurrence/source-slot cohorts retain numeric faults; ambiguous legacy receipts are explicit. |
| Focused Today/logging/Week web tests | 16 passed | Raw count/range visible, Bodyweight shown, submitted external weight zero; JSDOM rather than real browser. |
| Web build / changed web lint | Passed / no errors | One pre-existing hook-dependency warning. |
| TypeScript | 102 baseline diagnostics | Same undeclared globals in three existing test files. |
| Repeat compile | Four artifacts byte-equal | Both source copies and originals unchanged; compiler/artifact hashes refreshed. |

The earlier failed rechecks are retained outside Git: a bodyweight name-inference
defect and a test assertion key were corrected; a nonexistent test path and a
missing harness hash file were operator setup errors; a standalone importer test
then exposed the second root-path dependency, now fixed. They are not hidden as
successful procedures. Final qualification is scoped to the recorded procedures,
not a whole-final-tree API or PostgreSQL concurrency claim.

No database migration is introduced. No completed history, source workbook,
metadata-v2 scoring or unrelated baseline behavior is modified. Current PR CI
and the fresh Codex disposition must be inspected before the authorized merge;
this local record alone does not assert that remote review has completed.

Remaining M1 scope includes authored constraint authority and explicit
source-approved confirmation, relationships/order/redistribution qualification,
source-version transitions and real-browser journeys. Whole M1 remains pending.
