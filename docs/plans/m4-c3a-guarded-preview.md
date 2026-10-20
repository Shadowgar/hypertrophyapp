# M4-C3A guarded Customized preview implementation plan

Authorized by Issue #89 and direct owner direction, 2026-10-16. Execute inline, then independent whole-diff review. Stack on corrected C2 `cce0d811e6025a226e120a44cb742c8dd7a47ed5`. No deployment/merge/migration, workout activation, live data or changes to scheduling PR #83. The focused C2 correction is already published separately on PR #88 (33-set alternative, 57.5/59/57.5-minute synthetic upper bounds, six dose-floor tradeoffs).

**Goal:** a usable disabled-by-default, read-only profile-to-preview adapter and real server-owned future policy-admission boundary; no approved policy/catalog/inventory ships.

**Architecture:** pure core registry resolves IDs only from immutable server-owned records and verifies independently rooted science/owner HMAC endorsements bound to complete record content, source pins, audience/version/expiry, qualified metadata and inventory attestations. Empty registry/roots by default. No client-submitted policy/reviewer/approval is accepted. HMAC authenticates provisioned authorities, not professional credentials; assigning and validating actual reviewer authority remains C3B.

New isolated FastAPI app factory is never imported/mounted by production `main.py`; default disabled, no database/startup dependencies. Server-only environment/flag, principal resolver/allowlist and synthetic bundle map guard requests before planning. Production environment rejects synthetic access even with flags. A typed schedule-context port avoids existing scheduling routes. Use existing `build_generated_training_profile`, then explicitly normalized C1 `CustomizedProfile`; legacy numerical trace-only defaults cannot prescribe. Fixed C2 designs are named comparisons, not personalized optimization. HTML renders the same response through an escaped, consumer-readable preview with no activation/start/log control.

**Tech stack:** existing Python/FastAPI/Pydantic, standard-library HMAC/hash/HTML escaping, existing C1/C2 core. No new dependencies. Spec: [Issue #89](https://github.com/Shadowgar/hypertrophyapp/issues/89), [PR #88 review](https://github.com/Shadowgar/hypertrophyapp/pull/88), existing common/generation/metadata/load/date/security contracts and Proposed ADR statuses.

## Review focus

- A client adds approved/reviewer/source/catalog fields, forges a signature or replays a stale/wrong-audience record: reject without exercises or writes.
- A deployment accidentally enables the flag in production, or an ordinary/nonallowlisted user calls the isolated seam: fail closed before mapping/planning.
- Missing/contradictory recency, dates/timezone/skill/equipment/restrictions cannot become invented defaults or clearance; distinguish absent inputs from infeasibility.
- A short candidate fits time but misses dose floors: show explicit limited coverage, exact losses and no equivalence/optimality claim.
- Unknown observed effort and unsupported legacy controls remain unknown/trace-only; renderer cannot invent causal or prescription authority.

## Task 1: trusted policy admission

Create `packages/core-engine/core_engine/customized/admission.py` and `packages/core-engine/tests/test_customized_admission.py`.

- [x] Write failing tests: empty/unknown/unsigned/forged/replayed/expired/revoked authority; wrong source/audience/hash; unqualified/synthetic catalog/inventory; two distinct pinned authorities; only synthetic fully endorsed test record can pass future admission, never activate.
- [x] Implement immutable authority/endorsement/record/registry/decision types, domain-separated canonical payload and fail-closed ID resolution. Include explicit record/policy/source versions and freshness; no signing endpoint or client manifest loader.
- [x] Run targeted tests and commit. Expected: tests pass, no shipped approved records/keys.

## Task 2: guarded normalization and read-only preview integration

Create `apps/api/app/customized_preview_models.py`, `customized_preview_service.py`, `customized_preview_http.py`, `customized_preview_view.py`; tests `apps/api/tests/test_customized_preview.py`. Offline fixtures/CLI only under new `research/m4c3a/`.

- [x] Write failing tests for strict request, consent distinct from manual/auto/Authored, flags/environments/principal, missing or conflicting input, date/zone replay, absent context and no default numerical admission. Existing normalized GeneratedTrainingProfile retained with explicit active/trace-only mapping; core never receives raw request.
- [x] Implement `preview_program(request, server, context)` orchestration of server-owned bundles, mapping, admission and C2 planner. Distinct `synthetic_review_preview` / `approved_prescription` audience; production-approved request without registry returns policy-not-approved with no exercises; even endorsed test admission returns activation-disabled. No activation API.
- [x] Implement `create_preview_app` unregistered factory, off by default, authenticated server principal port and allowlist, request size bounds, safe validation errors and no persistence. No production auth/database/main/router edits.
- [x] Render complete dates/exercises/targets vs unknown observations, time intervals and cap conflicts, coverage/dose omissions and calibration caveats. Escape all dynamic content. No Start/Activate/logging controls. Developer fixture CLI uses TestClient and explicit flag to produce a synthetic HTML artifact from the actual adapter.
- [x] Verify behavior, unauthorized requests, production rejection, request tampering, isolation/no runtime I/O and renderer escaping. Commit. Expected: scoped tests pass; C1/C2 remain unchanged/nonactivatable.

## Task 3: qualification and draft

- [x] Run focused C1/C2/admission/preview and applicable existing GeneratedTrainingProfile/M2A/Authored regressions with cleared environment and explicit disposable URLs, before imports. No destructive reset fixtures or full unrelated suites.
- [x] Inspect desktop/mobile rendered artifact using Playwright; record actual limitations. Use Context7 for FastAPI API details and Codex Security for this narrow admission/request/rendering diff. Independent final read-only code review.
- [x] Record exact altered-file manifest, test/visual/security results and inherited hosted CI. Review C2 final API outcome once; do not rerun unrelated failures.
- Delivery: publish C3A-only stacked draft targeting corrected C2. Return demonstration and genuine C3B decisions: verified professional/owner policy and authority roots, qualified real inventory/metadata, #83 date persistence/two-week context, owned revision/consent/activation and real-device qualification.

## Execution record

Preflight: direct implementation authority already granted; no repeated skill approval pause. Existing dirty production checkout remains untouched. Native inline execution chosen; isolated `/tmp` worktree follows the accepted session convention. No new real numerical values, professional signatures or credentials are created. Staging/demo authentication is a server-supplied port and not a replacement for production account authentication.

Task 1 complete: f9233d0, 28 admission tests passed. Task 2 complete: ce36e99, 25 preview tests initially passed. Final independent review found missing-vs-empty restrictions and hidden calibration abstention reasons; both reproduced in four RED tests, fixed together, then 29 preview tests passed. Final combined local suite: 365 passed (14.85 s; one harness assertion-rewrite warning). Browser checks completed on static adapter artifact; scoped security export blocked by host guard, not falsely sealed. Pinned-dependency compatibility check also passed 365 cases in 14.16 s (one existing httpx/TestClient deprecation); its HTML was byte-identical. Final evidence/PR records publication. No independent second review or unrelated CI retry.

Final provenance ruling: optional field absence must not be labeled an explicit answer. Added a failing regression, preserved identical sessions for missing vs explicitly empty exclusions, and distinguished their trace origins. Final pinned suite 366 passed in 13.97 s; HTML remains byte-identical across pinned/ambient environments. This changes trace accuracy, not science policy or visible workout prescriptions.
