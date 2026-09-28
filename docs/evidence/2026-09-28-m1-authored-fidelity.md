# M1-A authored source fidelity qualification

Status: application candidate awaiting review; no M1 deployment, live migration,
whole-M1 acceptance or ADR acceptance. Base main:
`6e9b93ebc2f4570eeb0517131332e135b1d5c566`.
Branch: `m1/authored-source-fidelity`. This original qualification is pinned to
`6d835db4d0511b4eed360e6dfef6ed550ef48fc4`; its
[manifest](2026-09-28-m1-authored-fidelity.manifest.json) binds that snapshot,
not subsequent corrections. [Review-fix qualification](2026-09-28-m1-authored-fidelity-review-fixes.md) records the later candidate. Owner-authorized [bounded plan](../plans/m1-authored-source-fidelity.md).
The preceding [HIST-B activation](2026-09-28-m0-hist-b-activation.md) is separate.

## What was qualified

An independent OpenPyXL reader enumerated the locally authorized Full Body sheets
without asking the importer or committed artifacts which rows exist. All 315
Phase 1 and 310 Phase 2 slots were compared in source order through import,
canonical artifact, runtime loader and source-preserving execution/Today payloads.
Failures identify phase/week/day/slot/stage/field; they do not print source paragraphs.
Phase 2 weeks 6–10 each retain the AMRAP push-up slot with two working sets and a
typed `amrap` target, with no invented numeric compatibility range.

The comparison covers exercise text, working/warm-up counts, rep cells,
early/last effort, rest, last-set intensity, four tracking cells, substitutions
and notes. Source numeric-cell display and whitespace representations are normalized
for comparison; this is not a claim of byte-identical Excel formatting. Distinct
positional set targets remain distinct, including Phase 1 comma-separated targets;
`3+` and compound source expressions remain textual rather than guessed. Effort
ranges retain raw text and bounds rather than averages. Missing source cells stay
unknown. Explicit common RIR and top/backoff labels have synthetic tests. Absent
warm-up percentages/reps do not generate authored warm-up steps.

Artifacts use version 0.3.0 and `authored-prescription-v1`. Workbook SHA-256,
compiler-input SHA-256, semantic artifact SHA-256, physical row and stable
program/week/session/slot/set lineage travel to execution. Companion provenance
links its hash to the canonical artifact. Source IDs accompany the existing
occurrence UUIDs; catalog identity does not replace slot/occurrence identity.
A repeat compile reproduced the four artifacts byte-for-byte. Both original
workbooks and the read-only disposable copies retained their hashes. No workbook,
manual, private account payload or raw qualification output is published here.
Hashes are content/provenance evidence, not an independent source-authenticity claim.

Synthetic API tests cover AMRAP, distinct numeric sets, textual targets and missing
reps: actual receipts, identical retry, retained correction/undo, no resurrection,
source snapshot preservation after plan mutation and no fabricated observed RPE.
Invalid authored root/parent set references return 409 before history is persisted.
Unsupported numeric target cohorts do not enter the existing numeric progression
or session-state reducers. Their bounds/deltas remain null and effective counts
come from retained occurrence-scoped records. Numeric-owner negative tests prevent
a fallback 8–12 prescription. Numeric progression and load defaults retain their
existing compatibility behavior; these defaults are not licensed-source prescriptions.
Weekly-review numeric fault classification excludes incompatible cohorts explicitly
while retaining their planned/performed counts. M2A exposure/load intelligence is
not qualified by this work.

## Environment and results

Qualification used disposable copied Git source, two separately copied read-only
licensed workbooks, synthetic SQLite targets and cleared Python environments.
DATABASE_URL and TEST_DATABASE_URL, copied program/knowledge paths, temporary log
paths, disabled bytecode/cache/plugin autoload, socket/database guards and an
explicit disposable root were supplied. Node used copied dependencies and a
network guard. Tests never ran from the production checkout. Application/test
bytes were checked against the frozen qualification copy. Raw outputs, scripts
and guards remain in owner temporary storage outside Git; output hashes in the
manifest do not imply durable public artifact availability.

The broad API snapshot precedes the final set-index rejection and offline
metadata counting correction and resumed-authored warm-up assertion update.
Those changed code/test files are separately
qualified in the final occurrence/correction/typed-execution/metadata and resume runs; the
manifest identifies that exact snapshot. This is not a claim that one full suite
ran against every final file. Web evidence uses byte-equal final application/test
sources, with the final artifact snapshot also passing the offline build.

| Procedure | Result | Limits |
|---|---|---|
| Independent source-to-runtime plus existing Phase 1 source checks | 4 passed | Both locally authorized workbooks available; normal source-preserving path, ten weeks/five source sessions. |
| Focused source/import/schema/typed execution/occurrence/correction tests | 58 passed, 6 skipped | SQLite; six PostgreSQL-only HIST cases skipped. |
| Final typed boundary and offline metadata compatibility | 47 passed, 6 skipped | Exact final guard/metadata files; existing strong-field expectations pass. Scoring remains frozen. |
| Debug/account tests with explicit disposable dev-endpoint flag | 10 passed | Explains nine failures with endpoints disabled in the broad run; live endpoints were not enabled. |
| Final authored resume tests | 3 passed | Resume/complete/no-plan behavior; retained raw warm-up count and no synthesized source steps. |
| Complete core suite | 368 passed, 4 known baseline failures | Includes three new typed-target/effort/review-boundary tests. |
| Focused runner/logging/week tests | 14 passed | Includes AMRAP runner and distinct set target tests; JSDOM, not a real browser. |
| Complete web suite | 60 passed, 1 known baseline failure | Existing calendar test finds multiple Open Today Workout links. |
| TypeScript | 102 existing diagnostics | Existing undeclared test globals in today.logset, today.runner and week.program; no new diagnostics. |
| Web build | Passed | Offline build; not deployed. |
| Changed web lint | Passed, one existing hook-dependency warning | No lint errors. |
| Four-artifact repeat compilation | Passed | Source copies unchanged; existing workbook block/week/banner metadata retained. |
| Complete API snapshot | 531 passed, 17 failed, 7 skipped | Frozen snapshot before final corrections; disposition below. No whole-final-tree full-suite claim. |
| Documentation checks | Passed | No new active link failures; 28 existing failures retained, external links not fetched. |

The complete core failures retain their existing names: Today working-set
normalization, legacy state-count merge, and the two canonical muscle-coverage
expectations. The web calendar failure and TypeScript test-global diagnostics
were already present at PR #40's head. None was hidden or repaired in this package.
The existing importer test was changed only where it expected invented warm-up
steps or averaged effort; its synthetic source now verifies exact effort ranges,
explicit set roles and the original raw warm-up count instead.

## API failure disposition

Six failures match the pre-existing application baseline: both Phase 1/2
`test_today_total_sets_matches_progress_planned_total` cases,
`test_adaptive_gold_generate_week_includes_core_slot_when_equipment_available`,
`test_adaptive_gold_generate_week_uses_authored_deload_week_six`,
`test_generate_week_uses_saved_weekly_review_adjustments`, and
`test_adaptive_gold_fourth_exercise_today_and_log_set_preserve_substitution_guidance`.
Their names/assertions were compared with the retained HIST-B broad-run output
and PR #40 CI. No baseline runtime behavior was repaired.

Nine failures were the two development-wipe-dependent account tests and seven
generated-profile debug tests receiving 403 with `ALLOW_DEV_WIPE_ENDPOINTS`
absent from the cleared process. An isolated rerun with that flag explicitly true
passed all ten selected account/debug cases, including the already-passing log
case. This flag was supplied only to that disposable process.

One introduced compatibility failure was
`test_strong_fields_remain_unchanged_for_reference_exercises`: the offline
extractor treated typed individual set entries as a one-set group. It now uses
the authored total and passes the complete extraction tests, including a negative
case retaining legacy grouped-set accounting. No compiled metadata was changed.

The remaining failure was `test_workout_today_resumes_incomplete_session`
expecting nonempty synthesized warm-up weights for an authored row. The source
contains a warm-up count/range, not percentage/rep steps. The updated test checks
that count is retained and invented steps are absent; all three final resume
tests pass. The broad output retains the original failure honestly.
Both existing licensed Phase 1 source tests pass with the authorized local copies;
this does not solve CI fixture availability or publish those workbooks.

## Remaining scope and acceptance

No migration is introduced or applied for M1-A. No completed history is rewritten;
ambiguous legacy provenance remains unknown. Wider PostgreSQL concurrency,
real-browser/background journeys, source prose beyond tested table columns,
relationship/redistribution behavior and load/variant/unit semantics remain
unqualified. Movement restriction authority, substitution-confirmation UI,
actual-date scheduling, M2A exposure/load behavior and Customized generation are
separate slices. No source-layout replay is represented as original generation,
no metadata-v2 scoring is activated, and no whole release is owner-accepted.
