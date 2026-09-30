# M1-B merge and live activation

The owner authorized the three PR #42 correctness fixes, fresh review, merge and
affected API/web activation. This records that bounded cutover; it does not
accept whole M1, an ADR or the release.

- Original reviewed head: `88380ca2f6b6fe8fdcc23389a0856b955bc769de`.
- Corrections: `b2f16242a496f03eec7005821f8ce60e3b063daf` and final
  `f55a3da0540ccbbd7f50b8d8cc04fb48451e2295`.
- PR #42 merge / production main:
  `a2c9289bc73d475d1f71f67820b5f80b62d88a7c`.
- Exact final-head Codex review completed 2026-09-29 09:06:58 UTC with no new
  findings; original three threads resolved. Skipped CodeRabbit/Copilot reviews
  were not substantive successful reviews.

The [candidate qualification](2026-09-29-m1-authored-constraints.md) records the
load projection, refreshed feasibility and variant-media fixes. Final focused
API/core/web checks passed. Final full CI: API 560 passed, 8 known baseline/
missing-workbook failures, 15 skipped; core 378 passed, same four baseline
failures; web 73 passed, same calendar failure. TypeScript retained the same 102
test-global diagnostics in three existing tests. Documentation, tooling, web
build/lint, CodeQL and GitGuardian passed. No baseline runtime behavior was
changed merely to clear qualification.

A clean source archive built API/web images with final source labels. A fresh
private PostgreSQL dump was nonempty and archive-list validated, not restore
qualified. Production main advanced by fast-forward, preserving its unrelated
tracked log modification. Only API/web were recreated with the reviewed code;
effective environment and signing key were preserved. Postgres/Caddy container
identities stayed unchanged. Direct uvicorn startup avoided Compose Alembic;
a read-only preflight found every declared table already present. Live schema
revision stayed `0020_workout_set_amendments`; no migration or live DB write/
wipe/reset/reseed/history creation was performed.

API/web are running and HTTP-healthy; they have no Docker healthcheck, so Docker
health-status qualification is not claimed. Public health/homepage/Today/Week
returned 200 with normal request headers. Internal health returned 200; protected
workout/plan endpoints rejected unauthenticated requests with 403. Signing
configuration passes. No configured secret value was exposed in evidence.

In-memory loader/core/Today checks retain 315 Phase 1 and 310 Phase 2 slots,
raw warm-ups/lineage and five typed Phase 2 AMRAP slots with two sets/bodyweight
zero load. The constraint/profile/consent/load smoke also passed. No recorded
real-account fixture was available: authenticated existing-workout smoke was
not performed, and no account, plan or history was manufactured to replace it.

Remaining M1 source relationship/order, browser/background, metadata/fixtures
and PostgreSQL boundaries stay open. The subsequent
[security dependency triage](2026-09-29-security-dependency-triage.md) pauses M1-C
for a separate unmerged Caddy remediation candidate.
