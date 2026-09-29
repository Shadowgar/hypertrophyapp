# M1-A weekly-review working receipt boundaries

Status: scoped PR #41 correctness candidate; not milestone/ADR/release acceptance.
Parent revision: `54c659250a84fabef2d63106b5ec48c33ddddcba`.

The completed parent Codex review identified technique children counted as work and
numeric bodyweight receipts receiving external-load progression advice. Weekly
review now excludes parented/non-work receipts before aggregation. Numeric
bodyweight receipts retain completion accounting but do not enter load-based
fault/advice cohorts. Occurrence/source-slot matching preserves ordinary numeric
weighted cohorts, including the same primary exercise ID.

A copied package in a verified disposable SQLite/network-guard environment,
cleared environment, disabled plugin autoload/cache/bytecode: **23 core tests passed**
(authored prescriptions and weekly review). New production-serializer coverage
checks two working sets plus two technique children and a warm-up remain 2/2,
with unchanged working reps and no false below-target fault. The bodyweight case
checks above-target bodyweight receipts cannot influence a same-ID weighted
below-target cohort or produce load-increase advice. An initial local run found a
missing renamed helper reference; it was corrected before the passing run.

Parent CI: API **539 passed, 8 failed, 15 skipped**: the six documented baseline
application failures and two missing licensed-workbook fixtures. Core/web/TypeScript
baseline failures remain recorded in preceding qualification. No baseline fixes,
compiler/artifact changes, production operations or database migrations in this patch.
Source 315/310-row and all-set technique qualification remains scoped to the
[preceding snapshot](2026-09-28-m1-all-set-techniques.md); this patch changes review only.

| File | SHA-256 |
|---|---|
| `packages/core-engine/core_engine/decision_weekly_review.py` | `38e45af8628d4b845df4707dd1b7c0b13e02720247a9e8aac9ffdee00a1012f0` |
| `packages/core-engine/tests/test_authored_prescription.py` | `4d0f122f3aeda293e7a88f59147bf1347b943190c7d92182a85903085d689d74` |
