# M1-A authored source fidelity

Status: PR #41 merged and owner-authorized API/web activation completed;
[activation evidence](../evidence/2026-09-29-m1-authored-fidelity-activation.md). Explicit owner
2026-09-28 authorization covers importer/canonical/runtime preservation, isolated
qualification and an unmerged PR. Subsequent explicit owner authorization covers
the three PR #41 correctness fixes, fresh review, merge and API/web activation
if no introduced fidelity blocker remains. No M1 migration is expected. Base main: `6e9b93ebc2f4570eeb0517131332e135b1d5c566`.
Branch: `m1/authored-source-fidelity`. Whole M1 and ADR-003 remain unaccepted.

Controlling context: [product contract](../requirements/product-contract.md),
[ADR-003](../adr/0003-authored-source-immutability-and-compilation.md),
[authored source](../contracts/authored-source.md),
[execution](../contracts/execution-plan.md),
[AUTH-FID catalog](../requirements/catalog.md#auth-fid),
[traceability](../requirements/traceability.md), [M1 roadmap](../roadmap/milestones.md).
[Candidate evidence](../evidence/2026-09-28-m1-authored-fidelity.md) records limits.

## Implemented boundary

The two authorized Full Body workbooks compile to version 0.3.0 artifacts:
315 Phase 1 and 310 Phase 2 source slots, including Phase 2 weeks 6–10 AMRAP
push-ups with two working sets each. Raw source cells and individual working-set
rep/effort/rest/intensity targets are retained. Positional lists with one entry
per set stay positional. Explicit top/backoff labels remain distinct. Expressions
without an unambiguous numeric interpretation stay textual; absent values stay
unknown. Effort ranges are not averaged and prescribed effort is never recorded
as observed RPE. A warm-up count does not create invented percent/rep steps.
Existing workbook week/block/banner metadata and independent onboarding guidance
remain represented. Only the missing restored exercise's catalog entry is added;
metadata-v2 scoring stays inactive.
The existing offline metadata extractor counts typed individual sets using the
authored slot total, preserving its existing strong-field accounting. No compiled
metadata or scoring policy is changed.

Source program/week/session/slot/set IDs and physical source rows accompany
workbook, compiler and canonical-artifact hashes/version. These source IDs attach
to the existing workout/exercise occurrence UUIDs; they do not replace occurrence
identity. Started occurrences and captured log context retain their old payloads.
Legacy rows without lineage remain unknown and are not backfilled.

The execution payload adds `authored_prescription` and `source_lineage`.
`rep_range` remains the numeric compatibility field only when all sets share one
numeric target; otherwise it is null. The runner renders the actual current-set
target and requires actual reps for AMRAP rather than prefilling an invented
range. Unsupported numeric targets use occurrence-scoped receipt/count tracking,
with retry, retained undo/correction and frozen context. Numeric feedback bounds
and rep deltas are null; no numeric progression/session projection is invented.
Existing numeric progression behavior remains unchanged. Weekly-review numeric
fault classification excludes incompatible target cohorts with an explicit trace,
while retaining their planned/performed counts. This does not qualify future
load/exposure intelligence.

## Qualification and source safety

Independent OpenPyXL source enumeration compares every slot and the tested source
columns through import, canonical artifact, runtime loading and execution/Today
payloads. Missing locally authorized workbooks produce an explicit source-parity
skip in the new tests, never an assertion of source qualification. Synthetic
boundary tests run independently of licensed fixtures.

[Compiler](../../importers/compile_authored_fidelity.py) requires explicit source
and output directories. Run only in a disposable copy with a cleared environment,
verified disposable database targets and socket/database guards. Runtime never
reads XLSX. No workbook/manual or private audit output is added to Git. Source
hashes are checked unchanged; generated diagnostics remain outside this PR.
No migration is introduced. M1-A activation is recorded separately; whole-M1 acceptance remains pending.
[Review-fix evidence](../evidence/2026-09-28-m1-authored-fidelity-review-fixes.md) records raw warm-up visibility, explicit bodyweight load handling and
occurrence-scoped weekly-review filtering.

## Remaining M1 work

Movement restriction authority and substitution confirmation are the separate
[M1-B candidate](m1-authored-constraint-authority.md). Actual-date scheduling,
load intelligence/M2A exposure semantics, Customized generation and broad authored
redistribution remain separate slices. Unparsed prescription prose is preserved,
not claimed as executable policy. Whole-program relationships, variant/units,
real-browser/background behavior and broader concurrency remain unqualified.
Historical/unstarted plan refresh and occurrence-revision policy are not redesigned;
legacy snapshots do not gain invented provenance. Unrelated CI baseline failures
remain visible. Owner review and release acceptance are still required.
