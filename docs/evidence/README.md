# Evidence policy and audit references

Status: **Proposed policy**. This file is a portable provenance registry and migration plan, not a completed test run or managed security export. The source audit date is 2026-09-28; application revision is `df9965232ce731f8234d222acc526a90bc6be620`. No application tests, live probes, migrations, builds or deployments were performed in this documentation batch.

## Evidence and acceptance

Use stable reference keys for existing records; allocate a new run ID only for a real procedure. Each manifest records requirement/criterion IDs, revision/dirty state, source/rule/engine hashes, UTC time/operator, exact safe procedure, dependency/database/device/dataset versions, expected/observed result and exit code, artifact hashes/location/access class, limitations, reviewer and separate owner-acceptance reference. A proposed test or evidence package is labeled Proposed, never linked as a successful existing run.

Retain failures and append corrected evidence. Do not replace the full audit result with selected rechecks. Keep software correctness, source fidelity, PostgreSQL concurrency/migration, live deployment security and training-outcome science as separate claims. Owner acceptance names revision, reviewed criteria/evidence, accepted deviations and remaining limits; never derive it from historic checkmarks.

## Audit reference and migration plan

Reference key **AUD-20260928** identifies the completed audit, not a new certification. The original files remain in the owner’s external audit collection and are **not integrated or publicly available on this branch**. Record basename + hash + source revision rather than a broken host path. This registry preserves provenance without implying reviewers can fetch the artifacts. Public source links elsewhere resolve against this branch’s unchanged application tree; the audited revision is authoritative if that tree later changes.

| Original artifact | SHA-256 | Availability |
|---|---|---|
| `Hypertrophy-Audit-2026-09-28.md` | `644270e609723fa1d84861819020680aba7bd9e6a7e817134e51cacf84ecf923` | Retained outside Git; integration pending. |
| `Documentation-Migration-Inventory.md` | `e60fd1f698bc67124651e20d1ed504d6a96fb898ade98f64ccf582ed383ff13b` | Retained outside Git; integration pending. |
| `document-inventory.json` | `10bb2c734eaac14136d2a008cbda53fa769064d6db5357ce1bd109721e2da45f` | Retained outside Git; integration pending. |
| `Verification-Notes.md` | `03106056973c1810c26a3265fec9d70cc89a31cab711d9a99d76c5d8ce138130` | Retained outside Git; integration pending. |
| `security-worker.json` | `492606278267a75f6a9ab2d556110eddb309fddfac021b36ec28694ee3bce5e2` | Retained outside Git; integration pending. |
| `security-architecture.json` | `fbdea27049fa4dce4409ba15bd2e04091a51a2e986d3b001de2d43721f9afae7` | Retained outside Git; integration pending. |
| `environment.json` | `1fb0ece0bae3d59940d50fd3ae47816ae296c18cc112c5bd243684135c2b26b1` | Retained outside Git; integration pending. |
| `core-tests.txt` | `3e52e52b44282f69783b294413f9297f675adb42169cd5539f81f7f3027560c4` | Retained outside Git; integration pending. |
| `api-tests.txt` | `c2bc207b7c560ad27267f240889c9b1bebdd253a37f1ea498e6b6da8ec2cbb85` | Retained outside Git; integration pending. |
| `api-recheck.txt` | `3504cccfe53d1bf02eaaba30124236eae8d7db5fb2ad5446093451507867d9e0` | Retained outside Git; integration pending. |
| `api-behavior-recheck.txt` | `7348ee6e4b245a0976720d51503eaf02e65db3500c92218e90611fb6702ed3b3` | Retained outside Git; integration pending. |
| `web-tests.txt` | `12e6fe9099447ee782b62c9424a9a58f667f2c1819f8034cd6345dd6384599e1` | Retained outside Git; integration pending. |
| `web-types.txt` | `b3fe15ce3facb7f631ed6fef5352e5db1e2fe51dcc33ca02b6628e284533fd2f` | Retained outside Git; integration pending. |
| `fidelity-probe.json` | `9b195a5a5977ea4ef7497a63ea0fe75315f3984a5bf4ca994d73d0fe64faf0e0` | Retained outside Git; integration pending. |
| `restriction-probe.json` | `4be8a481196f93e054582fd2ddb216d2467c14c64505622b604eaf695fa873e0` | Retained outside Git; integration pending. |
| `phase2-source-diff.txt` | `4a7ee64df5d7c7be5bc2ac5dae7811055289f60494116901ac368d4ccb2c5386` | Retained outside Git; integration pending. |

Candidate stable destinations are `docs/audits/2026-09-28-df99652/` for a sanitized audit/inventory/verification summary and `docs/evidence/audit-2026-09-28/` for approved small manifests. These are proposed destinations, not existing links. Large raw output belongs in stable versioned artifact storage with retention/access/hash metadata, not automatically in Git. No raw artifact is copied by this batch.

Proposed migration procedure:

1. Review each artifact for secrets, personal records, filesystem identifiers and source licensing; never republish proprietary workbooks/manuals. Record redacted derivative hashes separately from the immutable original hash.
2. Retain the audit, 199-file inventory and verification notes together; preserve all failure dispositions, snapshot/fixture caveats, negative findings and the failed managed export status.
3. Select owner-approved public versus restricted retention and a durable location for each item; unresolved availability remains explicit. Large outputs receive a manifest, stable locator and access/retention owner.
4. Integrate only approved summaries/manifests, then replace registry availability with real repository/artifact links and validate them from a fresh checkout and GitHub. Keep provenance and original-to-successor mappings.
5. Reconcile the complete documentation inventory, path consumers, unresolved tasks, indexes, context references and successor notices in a separately approved integration. Keep executable `docs/rules/**` and generated-guide ownership intact.

## Recorded audit baseline

**AUD-20260928:source**: source-traced architecture/security and isolated probes, not live deployed qualification. Phase 1 315/315 rows matched over eleven tested fields; Phase 2 310 source/305 retained with five AMRAP omissions. Eighty unrestricted prescription-multiset cases passed; ordering, all notes/relationships and missing rows were not thereby certified. Use the aligned Phase 2 comparison, not positional fallout counts. Restriction probes changed authored dose (88 unrestricted versus 85/86 or 91).

**AUD-20260928:tests**: core 364 passed/4 failed; initial API 430 passed/18 failed/8 skipped; selected API recheck 12 passed (11 formerly failing and one previously passing); six persistent behavioral API failures; web 51 passed/1 failed across 20 files; TypeScript 102 diagnostics (90 TS2304, 12 TS2582). See [current state](../architecture/current-state.md) and [test strategy](../quality/test-strategy.md) for interpretation. No production build, real-browser/device, PostgreSQL or live smoke run is established.

**AUD-20260928:limits**: copied disposable source/dependencies with network/database guards, cleared environment and temporary persistence/logs; no production records/config/log inspection. Initial fixture-copy problems prevent claiming an initially byte-identical complete snapshot. Rule fixture hashes matched at recheck. SQLite does not establish PostgreSQL behavior. No copyrighted source workbook/manual was republished.

**AUD-20260928:security**: independent source findings retained; managed export **failed** its ancestor-directory privacy check. No permissions changed and no sealed complete scan, dependency inventory, live-ingress, secret/session/backup or deployed-image certification exists. This batch drafts documents from those findings, not another scan.

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

## Documentation checks for this review batch

2026-09-28; starting documentation revision `311dc00b5a8c97f5df4f0f33188303d27bbdfc91`; application tree `df9965232ce731f8234d222acc526a90bc6be620`. Scope: 6 existing documents updated plus 27 new documents; 10 Proposed ADRs; 80 unique requirements and trace rows; ledger D-001–D-022 present. Static path/heading/code-line anchor checks resolved 865 local link occurrences; two external pinned references were not fetched. Changed paths were documentation Markdown only; runtime rules/application changes absent. Markdown table/fence, diff-whitespace and cross-document authority/status review passed. Bounded source checks resolved the constructor filename, current persisted-model fields and threat-model citation anchors; no new broad scan or independent review was performed. This is documentation-check evidence only, not application/security/device/scientific verification. Production branch/HEAD/status remained the original main/audited revision/pre-existing modified debug log.
