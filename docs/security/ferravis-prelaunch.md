# FERRAVIS prelaunch security remediation

Date: 2026-10-29. Baseline: `8693ede061428b5202ca3661092b5d030d372bca`.
This is engineering evidence for an unmerged candidate, not deployment approval
or whole-host certification. Production services, accounts and release controls
remain unchanged. The reset procedure is separately owned in
[the clean-start runbook](../operations/ferravis-clean-start.md).

## Findings and changes

| Boundary | Baseline evidence | Candidate behavior |
|---|---|---|
| Recovery concurrency | Two simultaneous confirmations of the same token, and two different pending tokens for one account, both returned success on disposable PostgreSQL. | Account-first row lock, fresh expiry check and conditional one-row token claim; password change and invalidation of all pending tokens share one transaction. Conditional claiming also protects SQLite. |
| Session revocation | Tokens without `cv` remained valid after recovery; missing expiry was accepted. | Every protected route requires well-typed `sub`, `exp`, `cv` and the current password-hash fingerprint. Issuance requires the current hash. No schema migration. |
| Authentication abuse | Login/registration reached bcrypt, reset confirmation reached 600,000-iteration PBKDF2, and recovery reached mail without attempt limits. | Atomic process-wide budget of 60 admitted operations/minute, four concurrent auth requests, per-target login 10/minute, registration 5/minute, confirmation 5/minute, recovery request 3/15 minutes. Hashed target keys, maximum 2,048 entries and expiry bound retained state. Target rejections do not spend unrelated accounts' global budget. |
| Private diagnostics | General rejected values, validator context/messages and malformed path segments entered logs. | Validation responses/logs use an allowlist; operational paths use registered templates; unhandled exception text/tracebacks are not copied to application diagnostics. |
| Test data safety | Reachable inherited production coordinates could become the test engine before destructive fixtures. | Explicit test URL required before imports; contained SQLite root or explicitly declared loopback PostgreSQL target, non-default port and exact database/user markers. URL query overrides are forbidden. No runtime-setting fallback. |
| Password bounds | bcrypt 4 silently truncates passwords after 72 bytes. | New registration/reset credentials are limited to 72 UTF-8 bytes; reset tokens and names are bounded. Login retains compatibility for existing longer credentials up to 1,024 characters. |

Legacy tokens without credential binding will require fresh sign-in at deployment.
Credential-bound tokens survive deployment until expiry or password change. Do not
roll back to a verifier that ignores binding after declaring revocation active.
Old historical seed scripts that issue one-argument tokens are revision-specific;
current fixtures and active staging probes supply the actual stored hash.

The limiter is intentionally scoped to the current single Uvicorn process. State
resets on restart; multiple workers/replicas require shared enforcement before
scaling. It does not trust forwarded IP headers. Distinct attackers/targets can
exhaust the shared safety budget and temporarily deny legitimate authentication;
the bound limits expensive work and is not a distributed availability guarantee.

## Runtime and dependency applicability

All three `apps/web/Dockerfile` stages pin
`node:24.22.2-alpine3.24@sha256:8a32c8cf649a49915a66e81e7a609223c708d0adabf288ee3f4077d765542f85`.
Registry inspection verified an OCI multi-architecture index; its `linux/arm64/v8`
child is `sha256:e643984449ad25c88c0ff45094c74916806c9ee9dd1bc26c3593686ba2b853e4`.
Native, network-disabled base-image smoke returned Node `v24.22.2`, `arm64`,
Brotli `1.2.0`, OpenSSL `3.5.9` and a successful Brotli round trip.

[Node's 24.22.1 security release](https://nodejs.org/en/blog/release/v24.22.1)
identifies the CVE-2026-111497 fix as Brotli cherry-pick
`0ed4268a4401abcb44720963`; the unchanged bundled Brotli version string does not
mean that the fix is absent. [24.22.2](https://nodejs.org/en/blog/release/v24.22.2)
is its October 28 successor. Baseline live Node was 24.21.0 ARM64. The vulnerable
runtime was present; a direct attacker-controlled Brotli decoding route in this
application was not demonstrated. No exploit was sent to production.

`npm audit --package-lock-only --ignore-scripts --json` returned zero advisories
across 588 lockfile dependencies. A complete installed-package inventory from the
live API was checked with `pip-audit --disable-pip --no-deps`: only pip 25.0.1
returned advisories (12 duplicate records, six distinct CVEs). The API Dockerfile
now pins pip 26.2.2 before dependency installation. [pip's release notes](https://pip.pypa.io/en/stable/news/)
record the relevant installation/extraction fixes. These are package-installation
boundaries; no public package-install route was found. Python 3.12 also avoids the
older fallback-tar prerequisite of CVE-2025-8869. Internal `core-engine` is not on
PyPI and is not covered by the advisory service. Candidate-image inventory must
be audited again after build; the installed baseline is not the final image.

The requested [PHP OOM](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w)
and [stale-state](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp)
advisories require a PHP runtime. Scoped API/web package and executable inventory,
host PHP package status, process names and listeners found none. The host's
`php-crypt-gpg` entry has status `un` (uninstalled). This rules out the examined
application surface; it does not certify unrelated applications or the host.

## Review and qualification

Codex Security baseline scan `981d0d3f-d89b-4250-94fc-95c4fef9917b` was resumed and
sealed successfully: three medium findings (recovery race, legacy sessions,
auth abuse) and one low finding (private diagnostics). The destructive-test
fallback is a confirmed operational hazard, separately classified. The scan
retains partial whole-repository coverage: the requested security boundaries
were reviewed, not every training/import/release implementation. Token usage was
unavailable. An accidental unused duplicate created during rejoin supplied no
evidence and is not qualification.

Independent source review found and the patch corrected URL-query overrides in
the test guard, a fixture import regression, global-budget starvation by rejected
attempts, SQLite's missing row locks and malformed-path diagnostic leakage.
Latest focused PostgreSQL checks: **104 passed** (29.22 s), covering lifecycle,
attempt limits, private diagnostics, test targets, route observability and
candidate rendering. SQLite lifecycle: **14 passed, one PostgreSQL-only lock
test skipped** (12.93 s). Earlier recovery/dependency/signing/staging selection:
94 passed; the existing reset suite also passed in the initial broader run.
PostgreSQL proves same/different-token single winners, failed-commit rollback,
expiry after lock waiting and request/confirmation overlap. SQLite evidence is
reported separately. Tests use synthetic accounts and fake email only.

Reproduction requires an isolated checkout/environment before imports. Set
`DATABASE_URL` and `TEST_DATABASE_URL` to the independently verified disposable
target. SQLite also needs `CI_TEST_ROOT` or `TEST_DATABASE_ROOT`; PostgreSQL needs
`TEST_DATABASE_DISPOSABLE=1`, exact `TEST_DATABASE_NAME`, `TEST_DATABASE_USER`,
loopback host and a non-5432 port. Clear inherited configuration; use synthetic
signing settings, program/knowledge paths and private temporary logs. Run the
focused files named above with `python -m pytest ... -q`, then applicable full
API/core/web and exact-image qualification. These markers do not replace the
operator's database/container ownership verification.

GitHub baseline read-only review found zero open Dependabot and secret-scanning
alerts. CodeQL #9/#10 flag SHA256 fingerprints of already-bcrypt-hashed passwords
or bearer credentials, not raw password storage; bcrypt remains the password
KDF. #11 points at the isolated candidate HTML renderer: dynamic strings are
escaped and revision numbers are server-generated; no injectable HTTP dataflow
was established. Alerts were not dismissed. Baseline GitGuardian status was
unavailable and is not reported as passed.

Pending before release qualification: candidate OS/container scans and SBOM,
actual production-built Next/API images, full regression and exact-head CI,
final remediation diff scan and combined browser qualification. CORS uses the
same-origin proxy; no permissive CORS middleware was found. Source Caddy publishes
plain HTTP on port 18080, while effective outer TLS/origin restrictions remain
unverified. CSP/least-privilege container hardening remains follow-up context;
no script-injection or container-escape finding was established. No Cloudflare
changes were made. Merge, deployment through the release controller and the
one-time production reset each require separate exact authorization.
