# M1-A merge and live activation

Owner separately authorized PR #41 merge and affected API/web activation after
correctness fixes and fresh review. No whole-M1, ADR or release acceptance.

- Reviewed source: `54894624cc819d1da0a88ac84841e0e41111ad23`.
- PR #41 merge and production main: `32865d4f36ca11538e5762dab3029d5bafd5d517`.
- Fix revisions: `b8a992cfeca22d2fda855483d3fdc967e0585b1b`,
  `daa612cb5d223c74e9585ceb919d3977cb220897`,
  `32c43e2e1917e36f7dbc1de740ee009b96324424`,
  `54c659250a84fabef2d63106b5ec48c33ddddcba`,
  `54894624cc819d1da0a88ac84841e0e41111ad23`.
- Current-head Codex review completed 2026-09-29 05:41:39 UTC with no major issues;
  all earlier threads resolved. Initial service error was retried successfully.
- Final API CI: 539 passed, 8 failed, 15 skipped. Six documented application
  baseline failures and two absent licensed-workbook fixtures. Core retains four
  baseline failures; TypeScript retains 102 diagnostics in three existing tests.
  Calendar duplicate-link baseline remains; settings CI failure passed on base
  and candidate locally and was classified transient. Documentation, workflow,
  web lint/build, CodeQL and GitGuardian passed. Skipped automated reviews are
  not substantive successful reviews.

A clean Git archive of the reviewed source built API/web images successfully;
image source labels were checked. A fresh private PostgreSQL dump was nonempty and
passed archive listing validation (not an isolated restore qualification).
Production main advanced by fast-forward, preserving its unrelated tracked log
modification. Only API/web were recreated; PostgreSQL/Caddy identities and effective
runtime environment stayed unchanged. API command used uvicorn directly, avoiding
the Compose migration command. Live schema revision remains
`0020_workout_set_amendments`; no M1 migration/reset/reseed/wipe/history deletion.

API runs with zero restarts and health returns 200. Public homepage, Today, Week,
and health return 200 with normal request headers; bare urllib requests initially
received edge HTTP errors. Signing configuration passes. Startup logs were checked
in memory for configured secret values; none found. This is not comprehensive
log/security certification; no credential/private record was published.

Running loader/core/Today checks in memory retain **315 Phase 1 / 310 Phase 2**
slots, raw authored warm-ups and lineage over all ten weeks. All five Phase 2
weeks 6–10 AMRAP push-up slots remain typed, two working sets each, bodyweight,
zero recommended external load. No synthetic plan or workout history was persisted.
Authenticated real-account Today/Week smoke was unavailable because no suitable
existing recorded-account fixture was found; no account/history was created to
manufacture a passing result. Unauthenticated API workout/plan endpoints reject
requests (403); frontend pages were checked separately.

M1-B constraint/consent work follows on a separate unmerged application branch.
Remaining source relationship/order, metadata/fixture, browser/background and
PostgreSQL qualification boundaries are not accepted by this activation record.
