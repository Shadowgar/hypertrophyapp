# M4 integrated candidate: security qualification

Date: 2026-10-20. Two completed Codex Security **diff scans** qualify the integrated application and release-only code through `c3ebc61d419ac2ef0215fb26200adbe4b27aaa8b`. Both returned **zero reportable findings**, complete changed-source coverage and no deferred review units. This is static revision-scoped qualification, not a full-repository/dependency scan, production inspection, deployment approval or release acceptance.

| Scan | Immutable range | Coverage | Result |
|---|---|---|---|
| `72fdb442-3fa8-419c-a577-0054d4eef929` | `27231cfe98631de7eaebf21e13b60c6d145aeeba` → `7466cfef0a1e02c8deaa7952490a001a61185112` | All 91 plugin source-inventory items reviewed; all 181 changed paths accounted, including supporting tests/docs and Compose configuration | Completed, sealed; 0 candidates/findings/deferred |
| `9d5559ca-410b-45d5-a7a8-d7fa1459bb4e` | `7466cfef0a1e02c8deaa7952490a001a61185112` → `c3ebc61d419ac2ef0215fb26200adbe4b27aaa8b` | All 3 plugin source-inventory items and all 8 changed paths reviewed, including operator commands and supporting tests/docs | Completed, sealed; 0 candidates/findings/deferred |

The application scan reviewed authentication/session checks, parameterized SQL and account ownership, transaction/replay integrity, explicit content/session-bound consent, activation/replacement/date amendments, source-calendar/frozen occurrence boundaries, workout correction/history, browser rendering/stale-account state, deterministic planning and bounded inventory enumeration. The release delta reviewed the matched-image Compose overlay, marker-only bootstrap, full-chain migration/recovery runner, containment regression and the [actual release procedure](../operations/m4-release.md). No application runtime source changed in the release delta.

The repository [security policy](../../SECURITY.md) and supplied [historical threat model](../security/threat-model.md) governed review. The model's exact text was retained unchanged; its historical source revision `df9965232ce731f8234d222acc526a90bc6be620` was not promoted to current deployment evidence. Read-only preflight was ready with the documented single-reviewer fallback; no extra scan workers ran. No persistent Codex configuration changes were required. Daybreak access was granted for Daybreak Blue. Measured scan token usage was unavailable from the plugin.

## Private artifacts and permission recovery

The existing failed artifact attempt `d1f7b090-b337-4ffd-9fda-b40a6d2facc8` belongs to a different historical working tree, `/tmp/hypertrophy-m4-c3b2b`, based at `46b57a603499fcb54f8b7e954008aaa5808e321c`. It remains preserved and is not represented as a completed candidate scan.

Read-only permission inspection confirmed mode `0775` on `/home/rocco/.codex` and its state/plugin/scan ancestry. The plugin correctly rejects group/world-writable non-sticky ancestors because another writer could substitute artifacts. No host directory was chmodded, and no real Codex configuration, secrets or production environment files were edited.

Recovery used the supported **per-process** `CODEX_SECURITY_SCAN_ROOT` and `CODEX_SECURITY_STATE_DIR` overrides in an isolated instance of the existing plugin launcher. A fresh `umask 077; mktemp -d /tmp/hypertrophy-m4-security.XXXXXXXX` root is private `0700`; `/tmp` itself is `1777`. Initialize the launcher's MCP stdio session and supply the authentic inherited `CODEX_THREAD_ID` as `_meta["openai/threadId"]` on tool calls. Set the overrides only on that child process. Existing running MCP processes do not inherit later shell environment changes. The plugin's typed start/inventory/draft/completion tools own canonical writes; no canonical report was authored by shell.

Private root: `/tmp/hypertrophy-m4-security.5lJWPCgq`. Both the root and scan directories were verified `0700`. Reports are:

- Application: `scans/hypertrophy-m4-release/7466cfef0a1e02c8deaa7952490a001a61185112_20261020T140706Z_q8e0827p/report.md`.
- Release delta: `scans/hypertrophy-m4-release/c3ebc61d419ac2ef0215fb26200adbe4b27aaa8b_20261020T141837Z_yctebibi/report.md`.

Each directory also contains sealed `scan-manifest.json`, `findings.json`, `coverage.json`, retained `threatmodel.md` and `exports/results.sarif`. The application scan retains `artifacts/permission-recovery.md`; the local MCP driver is `<private-root>/call.py`. These are private temporary artifacts subject to OS cleanup, not committed outputs or a permanent storage configuration.

## Limits and remaining operations

This reviewer ran no application tests/imports, database connections, application startup or production operations. Focused negative-boundary assertions were inspected; actual runtime results belong to the separate [migration/recovery evidence](2026-10-20-m4-integrated-migrations.md) and browser/release qualification records. No source changes were required by these scans.

Effective production signing/session/ingress/rate settings, legacy JWT revocation, dependency baseline, database identity/grants, index lock duration, real backup confidentiality/retention, RPO/RTO and actual cutover remain unqualified here. Existing compatibility and Proposed security mechanisms were not silently activated or declared resolved. A disabled creation flag preserves already activated execution/history as described by the recovery regression; it is not a global execution kill switch. Production schema remains inferred until an independently authorized metadata check. The release procedure preserves the explicit deployment/data authorization boundary.

Later documentation-only publication commits do not change these immutable code ranges. Any later runtime, configuration or operator-command change needs its own bounded review; this record must not be described as a scan of an unreviewed final head.

Publication identity: GitHub code commit `83861a6bfc5ec0471a0d67a3edfc5350421bfbe3` and local qualification commit `c3ebc61d419ac2ef0215fb26200adbe4b27aaa8b` have the exact same Git tree `d2e31bd60cf401d9d43eb590212b0873cf41b5de`, verified after fetching the published branch. Both retain parent stack head `7466cfef`. The final publication delta adds evidence/navigation only; no application, operator-command or build configuration differs from the qualified code tree.
