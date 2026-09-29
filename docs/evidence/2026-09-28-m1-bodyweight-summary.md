# M1-A bodyweight summary follow-up

Status: PR #41 correctness candidate awaiting fresh review and separately
owner-authorized activation; no milestone, ADR or release acceptance.
Parent: `b8a992cfeca22d2fda855483d3fdc967e0585b1b`.
The containing commit and [manifest](2026-09-28-m1-bodyweight-summary.manifest.json)
bind this snapshot. [Previous fixes](2026-09-28-m1-authored-fidelity-review-fixes.md)
remain pinned to their earlier revision.

The completed Codex review of the parent found a P1 legacy-state next-load leak,
a P2 loss of valid numeric bodyweight rep bounds, and a P2 summary display that
presented zero added load as a prescribed pound value. All three are corrected.
Explicit authored bodyweight summary/load receipts force planned/next external
load to zero, regardless of pre-existing positive ExerciseState. Old state is
retained without being recommended or rewritten. Uniform numeric source targets
retain their bounds in receipts/live feedback and summaries; AMRAP/text targets
retain null bounds. Receipt-only load tracking still invents no numeric progression.
Day Summary labels Bodyweight, and positive actual external load appears explicitly
as added load; it is not converted into a new source prescription.

The independent 315/310-row source-to-runtime checks plus typed API boundaries
pass: **15 passed**. Synthetic AMRAP and numeric bodyweight cases seed a positive
legacy state, then verify summary next/planned load zero, source bounds, correction
and retained actual receipt/context. Core summary/prescription tests: **23 passed,
1 unchanged baseline set-normalization failure**. Focused runner/logging/Week and
summary UI tests: **18 passed**. The initial summary UI mock mistakenly described
an incomplete workout, so its summary was not requested; that failed output is
retained and the test now exercises the existing completed-workout summary flow.
Four-artifact repeat compilation is byte-equal; source hashes remain unchanged.

Tests used the same guarded disposable copy, cleared Python environment and
explicit synthetic SQLite targets described by the preceding evidence. Web tests
are JSDOM; this does not certify PostgreSQL concurrency, real browsers or all API
routes. No licensed source workbook, raw output, private account or environment
is published. Updated artifacts carry the new compiler/artifact lineage.
No M1 schema migration or completed-history rewrite is introduced. The previously
recorded core/calendar/TypeScript and generated API/fixture failures remain outside
scope. Fresh current-head review and CI disposition precede the authorized merge.
