# M1-B constraint and consent candidate qualification

Status: implemented application candidate for owner review; unmerged/unreleased.
Base: `32865d4f36ca11538e5762dab3029d5bafd5d517`.
[Bounded plan](../plans/m1-authored-constraint-authority.md).
[File/output manifest](2026-09-29-m1-authored-constraints.manifest.json) identifies
application bytes; the containing commit binds documentation. No acceptance claim.

## Behavior evidence

| Owner case | Tested result |
|---|---|
| 1. No restriction | Source prescription remains identical; API both phases at 3/5 days. |
| 2. Unmatched restriction | Same prescription; no generic weak-point/review overlay. |
| 3. Supported restriction | Only the conflicting slot becomes unresolved; other source work retained. |
| 4. Source-approved option | Offered with source permission; not automatically applied. |
| 5. Confirm | Separate performed variant and explicit consent/time; original prescription/slot unchanged. |
| 6. Decline | Visible unresolved status; logging blocked. |
| 7. No approved alternative | Visible infeasible slot; generic library choice rejected. |
| 8. Unrelated programming | Sets/reps/effort/rest/techniques/block/volume unchanged; hostile review overlay ignored. |
| 9. Regeneration | New occurrence lacks prior consent/variant; unresolved source remains. |
| 10. Today/resume/history | Same occurrence/source identity, frozen variant/consent, real receipt load; correction/undo retain context. |
| 11. Generated boundary | Existing generated restriction behavior retained; no authored constraint state injected. |

Additional negatives cover retry digest, stale source/consent revision, foreign
ownership, changing a started variant, pain/safety pause, profile conflicts,
legacy missing permission, and ordinary external-load zero rejection. Variant
receipts cannot update source-exercise progression, weekly load advice or original
exercise PR/trend comparisons. A raw persisted-plan/source-slot test also prevents variant receipts from producing
false missed-set/load advice for their original source slot, while keeping a
same-ID numeric weighted cohort. Summary explicitly declares comparable load advice
unavailable; compatibility numeric zeros are not an external-load recommendation.

## Isolation and procedures

Tests use a Git-archived/copied checkout under a verified disposable root,
cleared environment, explicit SQLite URLs/log/program/knowledge paths, disabled
plugin autoload/cache/bytecode, and Python guards rejecting network/other DB
backends/paths. Web uses a disposable copied source with a Node socket guard.
Dependencies are reused only from a prior disposable installation. Licensed XLSX
fixtures are separately copied read-only, never published; no live env/config,
private database, log or user record is copied into qualification/Git.

- API constraint/source/typed/occurrence/correction/resume compatibility: **62
  passed, 6 PostgreSQL-only skipped**. Final identity/consent subset: **14 passed**.
- Core constraint/prescription/review/history boundary subset: **29 passed**.
  Full core: **377 passed, 4 existing baseline failed**.
- Focused runner/constraint/typed/week UI: **25 passed**.
  Full web: **71 passed, 1 existing calendar duplicate-link failure**.
- Production web build: passed. ESLint: no errors, one pre-existing hook warning.
  TypeScript: the same **102 baseline diagnostics**, solely in three existing
  tests; no application/new-test diagnostics.
- Static documentation check retains existing exceptions, with no new link failure.

Initial broader API run had two expected fixture conflicts: resume tests declared
only home dumbbell/bodyweight equipment while executing unavailable authored
source equipment. Those fixtures now explicitly select Phase 1 and declare its
complete equipment, preserving the resume test's intended behavior. Missing
source equipment has separate must-fail coverage. Initial UI test also exposed
an inaccurate disabled-action label; it now says "Resolve authored slot first".
Passing runs qualify the corrected bytes, not the earlier failed snapshots.

Source/runtime tests retain 315 Phase 1 and 310 Phase 2 slots. Canonical artifacts
and compiler-input files are unchanged from merged M1-A; no source version or
historical consent is invented. No schema/migration files change.

## Baselines and limits

Full API is not rerun/claimed wholly green; merged M1-A CI documented six baseline
application failures plus two missing licensed-workbook fixtures. Core retains its
four known minimum-set/state/muscle-coverage failures; web retains the calendar
query failure; TypeScript retains its pre-existing test-global diagnostics.

SQLite does not qualify PostgreSQL concurrency. Six existing concurrent/migration
cases remain skipped; consent uses the established per-user write lock but is not
claimed independently concurrency-qualified here. Metadata coverage is incomplete:
many raw source alternatives do not uniquely resolve in current catalog metadata;
they remain unresolved, not guessed. Empty equipment profiles remain unknown.
Conservative equipment tags may reject choices requiring later metadata review.
Real-browser/background, legacy reconciliation, typed relationships/order and
complete authored/manual source semantics remain further M1 work. M2 dates/load
and broader generated changes remain outside this candidate.

No M1-B deployment, live DB reset/reseed/wipe, history deletion or migration. M1-A's
separate prior activation is recorded in its [activation evidence](2026-09-29-m1-authored-fidelity-activation.md).


## PR #42 review correction qualification

Review of head `88380ca2f6b6fe8fdcc23389a0856b955bc769de` identified three
real defects. Confirmation now projects no variant starting-load advice and
retains the original load separately; external variant input starts blank even
if a stale client payload carries a source recommendation. Only explicit variant
media is usable, and the source guide is disabled while a variant is active.
Current profile feasibility is recomputed in Today, consent commands and logging.
Frozen consent stays confirmed, while separate execution status blocks a newly
incompatible variant; user-reported pain/safety conflicts survive profile changes.

Final focused checks: 19 API cases passed, 13 constraint/prescription core cases
passed, and 23 web cases passed. Full core: 378 passed and the same four baseline
failures. Web build passed; lint retains one prior hook warning and no errors.
TypeScript retains the same 102 diagnostics in the three existing test files.
The broader API compatibility run and fresh GitHub checks/review are pending at
this correction commit; their final disposition is required before activation.

The original PR CI had 25 API failures: eight baseline/absent-source-fixture
failures and 17 assertions affected by the newly enforced authored boundaries.
Positive execution fixtures now declare source equipment rather than attempting
to execute unavailable source exercises. The rotated restriction test verifies
retained source slots and blocking conflict annotations. The authored repeat-failure
test rejects generic substitution advice; generated substitution coverage remains.
These are explicitly changed expectations, not described as baseline failures.
Separate missing-equipment, stale-profile and pain/safety negative tests remain.
No unrelated baseline application behavior is repaired by these fixture changes.
