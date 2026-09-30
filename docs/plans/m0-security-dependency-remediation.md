# M0 security dependency remediation

Owner-authorized implementation on 2026-09-29 under the task to finish PR #42
and triage available security findings. Scope: BLOCK NOW dependencies only;
publish an unmerged review PR. Deployment and whole-release acceptance are not
authorized by this package.

Base: `a2c9289bc73d475d1f71f67820b5f80b62d88a7c`. Branch:
`m0/security-dependency-remediation`.

## Current package

The deployed Caddy 2.8.4 binary was built with Go 1.22.3. Its HTTP ingress and
fixed API/web proxy transports use affected Go processing:

- [GO-2024-2963 / CVE-2024-24791](https://pkg.go.dev/vuln/GO-2024-2963):
  early final responses to `Expect: 100-continue` can leave an upstream
  connection invalid, failing a subsequent request. CISA ADP rates it High.
  The transport is reachable; exact Caddy timing/exploit reproduction is unproved.
- [GO-2025-3563 / CVE-2025-22871](https://pkg.go.dev/vuln/GO-2025-3563):
  bare-LF chunk terminators can permit smuggling with an incompatible peer
  parser. CISA ADP rates it Critical. The peer-parser prerequisite is unproved;
  classify conservatively under the owner's uncertainty rule.

Change only the Compose Caddy image to official `2.11.4-alpine`, pinned to the
reviewed multi-platform digest. Its actual Go 1.26.3 binary exceeds both fix
floors. This is a same-major minor-line upgrade of one component. No newer 2.8
patch image appears in the inspected official catalog; 2.11.4 is the current
published stable release. Application code, other dependency pins, Caddyfile,
database schema, credentials and auth/history policy stay outside the patch.

## Qualification and delivery

Require the exact binary/digest, unchanged Caddyfile adaptation/validation, and
isolated HTTP compatibility using the qualified API/web images. API startup must
use explicit disposable SQLite and a guard rejecting other engines/paths; never
inherit Compose DB/environment/volumes. Cover API prefix routing, frontend routes,
unauthenticated protection, generic non-account recovery without credentials,
compression and early-final/ordinary request sequences. Inspect malformed chunk
rejection as an alternate parser input; ordinary successful sequences are not an
exact exploit reproduction or PostgreSQL qualification.

The [triage and candidate evidence](../evidence/2026-09-29-security-dependency-triage.md)
records the tests, private-alert access gap, before-M2 tasks and deferred tools.
No unrelated baseline test repair or blanket upgrade is authorized. Separate
operator approval is required before Caddy cutover; until then the production
binary remains old and M1-C stays paused. Existing S2 lifecycle, concurrency,
auth-version and distributed-abuse work remains incomplete.

Status: implemented candidate / local qualification recorded / external review
pending. No merge, Caddy deployment, ADR acceptance or milestone acceptance.
