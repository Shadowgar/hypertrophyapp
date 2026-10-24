# Security/provider qualification: still incomplete

## Canonical scan

The old managed scan `4dd811ac-78b3-4cd8-b36b-2c583ed97644` covers immutable
`fc3bd0c..7c05f9a`, predating this combined candidate. It has no sealed canonical
report. The managed writer previously rejected its saved authoritative path:
“Scan output parent must not be group- or world-writable without the sticky bit.”
Temporary preparation did not redirect that writer; group-writable shared Codex
ancestors remain incompatible. No supported setup correction was established.

This request explicitly retains that limitation: no repeat blocked export, chmod
of shared host state, fabricated shell canonical report or claim of current-head
coverage. Complete a supported isolated managed scan/export of the actual candidate
before treating the canonical security gate as passed. Build, unit tests,
GitGuardian and CodeQL are separate evidence, not substitutes.

## PR #111 GitGuardian — incident-specific static triage

Fresh GitHub check lookup at pinned `c656988` returned check `120547843992`,
**failure**, zero annotations. Its provider output links incident
[38908114](https://dashboard.gitguardian.com/workspace/772539/incidents/38908114)
and two occurrences `306621747` / `306621748`, at original commit `96ef19d`,
[full-migration-preservation.json lines 17 and 40](../starting-load-2026-10-23/implementation/full-migration-preservation.json).
Both entries are the before/after digest under the empty `password_reset_tokens`
table label. The original file, both values and history are retained unchanged.

| Occurrence | Static verdict | Evidence and boundary |
| --- | --- | --- |
| 306621747, before | **not_actionable**, high confidence | The exact value is SHA-256(empty bytes). The generator hashes sorted row JSON joined by newline; no rows yield empty input. This public deterministic digest is not a reset credential, password, signing secret or bearer token. It is documentation-only synthetic preservation evidence, with no path consuming it as authorization. No supported security boundary crossed. |
| 306621748, after | **not_actionable**, high confidence | Identical value, same empty table and producer; second occurrence preserved individually. A duplicate-looking report does not erase its provenance. |

This is a scoped static false-positive adjudication, not provider closure or an
application-wide scan. Root SECURITY.md and data-safety policy apply; no scoped
policy changes this evidence surface. No runtime exploit/production credential
check is needed or authorized for a public empty-input digest.

Supported provider documentation permits an incident-specific **Ignore → False
positive (not a secret)** disposition through its authenticated dashboard or
incident API; it is different from disabling a detector or repository check.
[Incident lifecycle](https://docs.gitguardian.com/internal-repositories-monitoring/incidents/overview),
[provider API](https://api.gitguardian.com/docs).

There is no authenticated GitGuardian connector or provider API credential available
in this environment. GitHub check read access cannot impersonate the provider or
update its incident state. No API mutation was attempted, no provider secret was
sought in files, and no blanket allowlist/suppression/history rewrite was added.
Smallest provider action: an authorized workspace member reviews the two linked
occurrences, records the empty-table digest evidence and closes **only incident
38908114** as false positive through that supported workflow, then refreshes the
check. Until confirmed by the provider, PR #111's check remains failed. Fresh
candidate GitGuardian/CodeQL outcomes are reported independently in its head-linked
PR qualification comment; a later green check does not retroactively close #111.
