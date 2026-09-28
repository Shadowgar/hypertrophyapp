# Evidence policy and audit references

Status: **Proposed policy**. This file is a portable provenance registry and migration plan, not a completed test run or managed security export. The source audit date is 2026-09-28; application revision is `df9965232ce731f8234d222acc526a90bc6be620`. This registry is not evidence that any new application test, live probe, migration, build or deployment was performed.

## Evidence and acceptance

Use stable reference keys for existing records; allocate a new run ID only for a real procedure. Each manifest records requirement/criterion IDs, revision/dirty state, source/rule/engine hashes, UTC time/operator, exact safe procedure, dependency/database/device/dataset versions, expected/observed result and exit code, artifact hashes/location/access class, limitations, reviewer and separate owner-acceptance reference. A proposed test or evidence package is labeled Proposed, never linked as a successful existing run.

Retain failures and append corrected evidence. Do not replace the full audit result with selected rechecks. Keep software correctness, source fidelity, PostgreSQL concurrency/migration, live deployment security and training-outcome science as separate claims. Owner acceptance names revision, reviewed criteria/evidence, accepted deviations and remaining limits; never derive it from historic checkmarks.

## Audit reference and migration plan

Reference key **AUD-20260928** identifies the completed audit, not a new certification. The original files remain in the owner’s external audit collection and are **not retained or publicly available as raw artifacts in Git**. Record basename + hash + source revision rather than a broken host path. This registry preserves provenance without implying reviewers can fetch the artifacts. Repository source links locate implementation areas; the audited revision, rather than the current source tree, controls historical claims.

| Original artifact | SHA-256 | Availability |
|---|---|---|
| `Hypertrophy-Audit-2026-09-28.md` | `644270e609723fa1d84861819020680aba7bd9e6a7e817134e51cacf84ecf923` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `Documentation-Migration-Inventory.md` | `e60fd1f698bc67124651e20d1ed504d6a96fb898ade98f64ccf582ed383ff13b` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `document-inventory.json` | `10bb2c734eaac14136d2a008cbda53fa769064d6db5357ce1bd109721e2da45f` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `Verification-Notes.md` | `03106056973c1810c26a3265fec9d70cc89a31cab711d9a99d76c5d8ce138130` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `security-worker.json` | `492606278267a75f6a9ab2d556110eddb309fddfac021b36ec28694ee3bce5e2` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `security-architecture.json` | `fbdea27049fa4dce4409ba15bd2e04091a51a2e986d3b001de2d43721f9afae7` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `environment.json` | `1fb0ece0bae3d59940d50fd3ae47816ae296c18cc112c5bd243684135c2b26b1` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `core-tests.txt` | `3e52e52b44282f69783b294413f9297f675adb42169cd5539f81f7f3027560c4` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `api-tests.txt` | `c2bc207b7c560ad27267f240889c9b1bebdd253a37f1ea498e6b6da8ec2cbb85` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `api-recheck.txt` | `3504cccfe53d1bf02eaaba30124236eae8d7db5fb2ad5446093451507867d9e0` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `api-behavior-recheck.txt` | `7348ee6e4b245a0976720d51503eaf02e65db3500c92218e90611fb6702ed3b3` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `web-tests.txt` | `12e6fe9099447ee782b62c9424a9a58f667f2c1819f8034cd6345dd6384599e1` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `web-types.txt` | `b3fe15ce3facb7f631ed6fef5352e5db1e2fe51dcc33ca02b6628e284533fd2f` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `fidelity-probe.json` | `9b195a5a5977ea4ef7497a63ea0fe75315f3984a5bf4ca994d73d0fe64faf0e0` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `restriction-probe.json` | `4be8a481196f93e054582fd2ddb216d2467c14c64505622b604eaf695fa873e0` | Original retained outside Git; sanitized derivatives below do not replace it. |
| `phase2-source-diff.txt` | `4a7ee64df5d7c7be5bc2ac5dae7811055289f60494116901ac368d4ccb2c5386` | Original retained outside Git; sanitized derivatives below do not replace it. |

Stable repository-facing derivatives are now retained: [sanitized audit/verification summary](../audits/2026-09-28-codebase-product-documentation-audit.md), [complete 199-file registry](../audits/2026-09-28-documentation-migration-registry.md) / [JSON](../audits/2026-09-28-documentation-migration-registry.json), [legacy evidence map](legacy/README.md) and [documentation migration report](../audits/2026-09-28-documentation-authority-migration.md). Derivative content is committed documentation; original hashes above identify the external originals, not the derivative files. Git identifies each derivative revision separately.

No raw output, environment/secret/private state, copyrighted workbook/manual or managed scan export is copied. The registry retains safe file-level metadata and dispositions, not source contents. Complete raw-package durable restricted storage, retention/access owner and public-versus-restricted disclosure policy remain unresolved; no active contract depends on its owner-machine path. Future raw-artifact publication needs an explicit licensing/privacy review and stable manifest, not a blanket copy.

Original bodies, negative findings, task dispositions, runtime path exceptions, guides/catalog/provenance relationships and context references are accounted for in this integration. Historical generated evidence stays at tool-consumed paths and remains scoped to the original procedure; its presence is not current acceptance.

## Recorded audit baseline

**AUD-20260928:source**: source-traced architecture/security and isolated probes, not live deployed qualification. Phase 1 315/315 rows matched over eleven tested fields; Phase 2 310 source/305 retained with five AMRAP omissions. Eighty unrestricted prescription-multiset cases passed; ordering, all notes/relationships and missing rows were not thereby certified. Use the aligned Phase 2 comparison, not positional fallout counts. Restriction probes changed authored dose (88 unrestricted versus 85/86 or 91).

**AUD-20260928:tests**: core 364 passed/4 failed; initial API 430 passed/18 failed/8 skipped; selected API recheck 12 passed (11 formerly failing and one previously passing); six persistent behavioral API failures; web 51 passed/1 failed across 20 files; TypeScript 102 diagnostics (90 TS2304, 12 TS2582). See [current state](../architecture/current-state.md) and [test strategy](../quality/test-strategy.md) for interpretation. No production build, real-browser/device, PostgreSQL or live smoke run is established.

**AUD-20260928:limits**: copied disposable source/dependencies with network/database guards, cleared environment and temporary persistence/logs; no production records/config/log inspection. Initial fixture-copy problems prevent claiming an initially byte-identical complete snapshot. Rule fixture hashes matched at recheck. SQLite does not establish PostgreSQL behavior. No copyrighted source workbook/manual was republished.

**AUD-20260928:security**: independent source findings retained; managed export **failed** its ancestor-directory privacy check. No permissions changed and no sealed complete scan, dependency inventory, live-ingress, secret/session/backup or deployed-image certification exists. This registry references those findings; it does not establish another scan.

## Future evidence by claim

| Claim | Required artifact and limit |
|---|---|
| Authored source fidelity | Independent source parser, source hash, diagnostic reconciliation, per-slot stage/relationship/ordering matrix; licensed fixture strategy. |
| Load/recommendation behavior | Synthetic effective exposures, actual units/effort, rule version, actions/overrides and correction replay; no outcome guarantee. |
| Scheduling | Selected dates/timezone, occurrence revisions, relationship/dose diffs, spacing conflicts and browser journey. |
| History/migrations | Idempotency/conflict/concurrency and correction reconstruction; isolated PostgreSQL upgrade/backfill/recovery manifests. |
| Security | Negative credential/TLS/redaction/version tests, sanitized effective-state review and independently scoped controls. |
| Mobile/accessibility | Actual target device/browser, focus/screen reader/background/network conditions; static bundle size is insufficient. |
| Recovery | Backup manifest, approved compatible isolated restore, integrity/timing and RPO/RTO; a dump existing is not restoration proof. |
| Training outcome | Predeclared observation/review design with sufficiency/confounders; associations are not causal optimization proof. |

No artifact in the external audit becomes release owner acceptance. Publication of this policy also grants no authority to run the described procedures against production.

## Previous planning-batch documentation checks

2026-09-28; starting documentation revision `311dc00b5a8c97f5df4f0f33188303d27bbdfc91`; application tree `df9965232ce731f8234d222acc526a90bc6be620`. Scope: 6 existing documents updated plus 27 new documents; 10 Proposed ADRs; 80 unique requirements and trace rows; ledger D-001–D-022 present. Static path/heading/code-line anchor checks resolved 865 local link occurrences; two external pinned references were not fetched. Changed paths were documentation Markdown only; runtime rules/application changes absent. Markdown table/fence, diff-whitespace and cross-document authority/status review passed. Bounded source checks resolved the constructor filename, current persisted-model fields and threat-model citation anchors; no new broad scan or independent review was performed. This is documentation-check evidence only, not application/security/device/scientific verification. Production branch/HEAD/status remained the original main/audited revision/pre-existing modified debug log.

## Authority integration checks

The subsequent documentation-only integration starts from `64c3269dd33bea8c6a72e5a6151d985cf9ea8470`. Its complete static checks, scope and historical exceptions are recorded in the [migration report](../audits/2026-09-28-documentation-authority-migration.md). Previous 865-link/33-file counts above describe the earlier batch and are not reused as the integration result. No application checks or security certification were added.

## M0-HIST-A implementation candidate

[Occurrence/retry qualification](2026-09-28-m0-hist-a.md) records the bounded
application candidate, isolated PostgreSQL migration/concurrency results, legacy
compatibility and remaining undo/ExerciseState defects. This is separate from
the historical audit and does not establish deployment or release acceptance.

## M0-HIST activation and correction candidate

[HIST-A merge/live activation](2026-09-28-m0-hist-a-activation.md) records the
separately authorized PR #39 deployment and live migration 0019.
[HIST-B qualification](2026-09-28-m0-hist-b.md) and its
[manifest](2026-09-28-m0-hist-b.manifest.json) describe the pre-merge correction
candidate and disposable migration 0020. [HIST-B merge/live activation](2026-09-28-m0-hist-b-activation.md) records the
subsequent separately authorized deployment and outstanding HIST qualification.
None of these records constitutes whole-M0,
ADR or release owner acceptance.

## M1-A authored source fidelity candidate

[Source-to-runtime qualification](2026-09-28-m1-authored-fidelity.md) records the
authorized 315/310-row source-preservation candidate, typed execution boundaries
and remaining work. No M1 deployment, whole-M1 acceptance or ADR acceptance is claimed.

[PR #41 review-fix qualification](2026-09-28-m1-authored-fidelity-review-fixes.md)
and its [manifest](2026-09-28-m1-authored-fidelity-review-fixes.manifest.json)
record the later warm-up, bodyweight and occurrence-cohort correction snapshot.
The original M1-A manifest remains bound to its earlier revision.

[Bodyweight summary follow-up](2026-09-28-m1-bodyweight-summary.md) records
the subsequent current-head summary/load/rep-bound corrections.

[Persisted-plan review identity follow-up](2026-09-28-m1-weekly-review-source-identity.md)
records production serialization/source-slot cohort matching.

[Explicit all-set technique qualification](2026-09-28-m1-all-set-techniques.md)
records the subsequent compiler/runner source-scope correction.
