# M1-A explicit all-set technique qualification

Status: PR #41 correctness candidate awaiting fresh review and separately
owner-authorized merge/activation. Parent:
`32c43e2e1917e36f7dbc1de740ee009b96324424`.
The containing commit and [manifest](2026-09-28-m1-all-set-techniques.manifest.json)
bind this snapshot. No milestone, ADR or release owner acceptance.

The parent Codex review found a P1: 25 source slots explicitly prescribe a
technique on all sets, while typed targets assigned it only to the last set.
The compiler now honors explicit all-set scope and preserves raw source text:
15 Phase 1 slots and 10 Phase 2 slots. Last-set-only instructions, including
“all reps of the last set,” remain confined to that set. Unknown/free-form source
prose does not gain invented execution policy.

The runner reads the current set's recorded technique for cues, confirmation and
supported technique-child handling. A first-set mechanical dropset launches its
panel after working set 1 rather than waiting for the final set. Integrated
partials remain visible on each prescribed set. Raw N/A markers are retained but
do not become required execution cues. Authored technique panels show the source
instruction and require actual reps/load, without half-rep, percentage-load or
rest-duration defaults. Existing generated technique behavior remains separate.

In a newly copied guarded disposable snapshot with explicit SQLite URLs, cleared
Python environment, read-only licensed fixture copies and isolated Node dependencies:

- Independent source/import/canonical/runtime/Today plus typed API boundaries:
  **16 passed**; all 315/310 rows and five two-set bodyweight AMRAP slots retained.
- Authored core prescription/review boundaries: **6 passed**.
- Focused runner/logging/Week/UI boundaries: **22 passed**. All-set mechanical and
  integrated cues apply on the first set; last-set-only cues do not; missing actual
  child values cannot log fabricated receipts. A first-parent child API test retains
  source scope and does not inflate working-set completion.
- Four-artifact repeat compile: byte-equal; both licensed sources unchanged.
- Final web build: passed. TypeScript: the same 102 baseline test-global diagnostics.
- Changed web lint: no errors, one existing hook-dependency warning.

Initial new UI tests used an incorrect disabled-button name and ambiguous numeric
input query; those failed outputs remain outside Git and the corrected queries
exercise the actual runner. An initial TypeScript check raced the build removing
generated Next type files; it was rerun after the build completed. No raw test output, workbook/manual, private account
or secret is published. JSDOM is not real-browser qualification; SQLite is not
PostgreSQL concurrency evidence. The broader API compatibility snapshot belongs
to the preceding revision, not this final helper/artifact snapshot.
No migration, live history rewrite or production activation occurred for this fix.
Whole M1 remains pending, including the separately authorized M1-B slice.
