# FERRAVIS prelaunch security remediation

Date: 2026-10-29; evidence reconciled 2026-10-30. Baseline: `8693ede061428b5202ca3661092b5d030d372bca`.
Qualified security source/image revision: `0f028c5c2851a1173ede0e62f334fc7a4a238096`.
This is engineering evidence for an unmerged candidate, not deployment approval
or whole-host certification. Production application revision, accounts and release
controls remain unchanged. An operator-scheduled host reboot interrupted disposable
qualification on October 30; this assignment issued no host/live-service restart.
The reset procedure is separately owned in
[the clean-start runbook](../operations/ferravis-clean-start.md).

## Findings and changes

| Boundary | Baseline evidence | Candidate behavior |
|---|---|---|
| Recovery concurrency | Two simultaneous confirmations of the same token, and two different pending tokens for one account, both returned success on disposable PostgreSQL. | Account-first row lock, fresh expiry check and conditional one-row token claim; password change and invalidation of all pending tokens share one transaction. Conditional claiming also protects SQLite. |
| Session revocation | Tokens without `cv` remained valid after recovery; missing expiry was accepted. | Every protected route requires well-typed `sub`, `exp`, `cv` and the current password-hash fingerprint. Issuance requires the current hash. No schema migration. |
| Authentication abuse | Login/registration reached bcrypt, reset confirmation reached 600,000-iteration PBKDF2, and recovery reached mail without attempt limits. | Atomic process-wide budget of 60 admitted operations/minute, four concurrent auth requests, per-target login 10/minute, registration 5/minute, confirmation 5/minute, recovery request 3/15 minutes. Hashed target keys, maximum 2,048 entries and expiry bound retained state. Target rejections do not spend unrelated accounts' global budget. |
| Private diagnostics | General rejected values, validator context/messages and malformed path segments entered logs. | Validation responses/logs use an allowlist, preserving exact trusted schema guidance; operational paths use registered templates; unhandled exception text/tracebacks are not copied to application diagnostics. |
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
pins pip 26.2.2 during dependency installation, then removes pip from the final
runtime. [pip's release notes](https://pip.pypa.io/en/stable/news/)
record the relevant installation/extraction fixes. These are package-installation
boundaries; no public package-install route was found. Python 3.12 also avoids the
older fallback-tar prerequisite of CVE-2025-8869. Internal `core-engine` is not on
PyPI and is not covered by the advisory service. The final actual installed
inventory audit covered **43 public packages with zero advisories**; pip was
absent. The internal package remains covered by source review and tests.

The first hosted scan exposed a limitation of lockfile/package-inventory audits:
eight additional records came from [pip's vendored libraries](https://raw.githubusercontent.com/pypa/pip/26.2.2/src/pip/_vendor/vendor.txt),
and 17 came from global npm's dependencies. These tools were unnecessary at
runtime. The web runner now removes npm/yarn and invokes the existing Next start
command through Node directly. Build stages retain their tools. The rebuilt
images passed startup/absence checks, and **all 25 bundled-library records were
absent on rescan**. Application dependency versions and startup flags are unchanged.

The requested [PHP OOM](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w)
and [stale-state](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp)
advisories require a PHP runtime. Scoped API/web package and executable inventory,
host PHP package status, process names and listeners found none. The host's
`php-crypt-gpg` entry has status `un` (uninstalled). This rules out the examined
application surface; it does not certify unrelated applications or the host.

## Exact-image evidence and remaining OS risk

[Hosted ARM64 run 40824500414](https://github.com/Shadowgar/hypertrophyapp/actions/runs/40824500414)
built tracked inputs at `0f028c5`, verified matching API/web revisions, API startup
on disposable tmpfs SQLite, guest routes, native Sharp, musl and zero server
actions. Runtime: Node 24.22.2, Next 16.4.1, Sharp 0.35.5. The normal image's API
rewrite is `http://api:8000`; optional browser artifacts record their separate
disposable loopback target and are not deployment artifacts.

| Image | Exact image ID | Trivy 0.69.3 result | CycloneDX components |
|---|---|---|---|
| API | `sha256:df6399c6380de3acd249ef2b7c8097097793ffdd3f989ec16c9e7ea36da07800` | 44 high, 58 medium, 61 low, 1 unknown; all Debian OS records | 133 |
| Web | `sha256:b176429f45952798ecb9d75e9c8846c2d0093ee0174de8f34bb299725e6579eb` | Zero findings | 523 |

Scanner image IDs matched the runtime receipt. Full JSON, SBOMs, installed-package
inventory and pip-audit 2.10.1 results are retained in the run's `arm64-security-*`
artifact and Codex scan `056faf7b-1a73-497c-a2bd-87ee14cc25ae`. No severity filter,
ignore-unfixed option or suppression file removed records.

The combined FERRAVIS source `38db151b1ce3584d539ab92f344a7f843db7f095`
also passed [native run 40825000117](https://github.com/Shadowgar/hypertrophyapp/actions/runs/40825000117).
Its API image is `sha256:6eaad450303db0e5a4ede7781a22d2f8e087eee694cf6fbdcb35610fab3ece08`;
web image is `sha256:a8302b3697d9b0aafe9b5902a7849d911e96aa5deac0870faee64ded2c077714`.
The scanner IDs match that receipt. All component identities and vulnerability
tuples equal the security candidate above; Python installed/public inventories
and advisory results are byte-identical. The exported production-built web
artifact uses the recorded disposable API rewrite for isolated browser testing.

The **164 remaining API records represent 71 advisories across 20 source-package
families**. None has a fixed version in this Debian 13.7 feed; some have fixes in
other Debian releases. They remain vulnerable-package evidence, not a clean scan
or 164 demonstrated remote application exploits. The per-record disposition is
retained as `artifacts/hosted-0f028c5/debian-os-disposition.json` in that scan.

| Source family | Records | Application assessment; package remains present |
|---|---:|---|
| apt | 2 | Repository/key-management tooling; no application invocation. |
| bash | 1 | Local shell privilege handling; startup command is fixed. |
| util-linux | 54 | Mount/nsenter/local-account prerequisites; no API/core invocation or privileged container configuration found. |
| coreutils | 4 | Crafted local CLI inputs or file races; no request-driven invocation. |
| dash | 2 | Shell pattern/escape inputs; no request-driven shell evaluation. |
| diffutils | 1 | Crafted diff input; no application invocation. |
| gcc-14/libstdc++ | 6 | Native extensions exist; affected native reachability remains unresolved. |
| acl | 2 | Privileged ACL operations on attacker-controlled paths; no application caller found. |
| attr | 1 | Local extended-attribute utility races; no application caller found. |
| bzip2 | 1 | `bzip2recover` crafted-file prerequisite; no recovery/upload route. |
| glibc | 42 | Core dependency: affected native paths are not exhaustively proven unreachable; DNS configuration risk remains. |
| ncurses | 8 | Includes `infocmp` CLI overflow; headless app does not invoke it. |
| pam | 4 | PAM userdb authentication prerequisite; app uses bcrypt/JWT. |
| sqlite3 | 4 | Production uses PostgreSQL; no arbitrary SQL, changeset or SQLite ZIP route found. |
| systemd | 14 | Inventory contains shared libraries; homed/oomd/journal service prerequisites are not established in the Uvicorn container. |
| shadow | 6 | Local OS account/provisioning prerequisites; app accounts are database records. |
| perl | 4 | Archive/regex/temporary-file/Pod processing; no application Perl invocation. Unknown severity stays unknown. |
| sysvinit | 1 | Local installer configuration prerequisite; not the container startup path. |
| tar | 5 | Crafted archive extraction/restore prerequisites; no API/core extraction route. |
| zlib | 2 | Specific native CRC/gzip-write transitions; complete linked-library reachability remains unresolved. |

These are source-based reachability assessments, not vendor VEX declarations.
Debian identifies the high-severity [util-linux](https://security-tracker.debian.org/tracker/CVE-2026-76642),
[ncurses](https://security-tracker.debian.org/tracker/CVE-2025-69720),
[ACL](https://security-tracker.debian.org/tracker/CVE-2026-54369),
[systemd-homed](https://security-tracker.debian.org/tracker/CVE-2026-16742) and
[Perl archive](https://security-tracker.debian.org/tracker/CVE-2026-9538)
prerequisites and deferred/no-DSA release status. No corresponding remote app path
was demonstrated. A meaningful residual is [glibc's long DNS search-domain abort](https://security-tracker.debian.org/tracker/CVE-2026-8674):
host DNS configuration influenced by DHCP/VPN can affect name-resolving processes,
including database/SMTP clients. Native glibc/libstdc++/zlib exposure is not fully
closed. Refresh and rescan the base when stable fixes become available; review
these residuals before deployment. No unstable-distribution package substitution
or broad base migration was introduced to hide the counts.

## Review and qualification

Codex Security baseline scan `981d0d3f-d89b-4250-94fc-95c4fef9917b` was resumed and
sealed successfully: three medium findings (recovery race, legacy sessions,
auth abuse) and one low finding (private diagnostics). The destructive-test
fallback is a confirmed operational hazard, separately classified. The scan
retains partial whole-repository coverage: the requested security boundaries
were reviewed, not every training/import/release implementation. Token usage was
unavailable. An accidental unused duplicate created during rejoin supplied no
evidence and is not qualification.

The complete remediation changes are covered by these sealed immutable diff reviews:

| Range | Codex Security scan | Changed files | New reportable source findings |
|---|---|---:|---:|
| `8693ede..9f899b2` | `971cd6e0-23db-40d6-98d8-50fea7d08426` | 45 | 0 |
| `9f899b2..7d5dd71` | `63ab38e9-492f-481a-abec-26c9a29b7f42` | 6 | 0 |
| `7d5dd71..0f028c5` | `056faf7b-1a73-497c-a2bd-87ee14cc25ae` | 3 | 0 |

The final review retains the unresolved OS risk above. Measured token usage was
unavailable for these scans. The reset-client follow-up binds all three PostgreSQL
clients to the inspected container's local socket with a cleared environment;
its fresh restore, rollback and complete reset rehearsal passed separately.

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

Full API CI initially caught one compatibility regression: generic validation
responses removed a fixed scheduling guidance message (1 failed, 1,036 passed,
123 skipped at `9f899b2`). The correction uses exact canonical constants, never
partial matches or input/context interpolation. **46 focused tests passed**
(64.12 s), including the unchanged original message assertion, both preview/apply
validators and private-input/prefix/suffix rejection tests. Full CI passed at
`0f028c5` ([run 40824500406](https://github.com/Shadowgar/hypertrophyapp/actions/runs/40824500406))
and combined `38db151` ([run 40824946178](https://github.com/Shadowgar/hypertrophyapp/actions/runs/40824946178)):
the latter API suite reported **1,044 passed, 123 skipped**, and web **526 passed**.
Documentation-only final heads retain their own applicable CI; private source
fidelity remains a full protected-main gate after future authorized integration.

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
was established. Those three baseline alerts were not dismissed. New PR alert
[#16](https://github.com/Shadowgar/hypertrophyapp/security/code-scanning/16)
was formally dismissed as a false positive after its exact SARIF showed email or
random reset-token values entering transient limiter keys, never password
storage. Passwords still use bcrypt; recovery verification uses PBKDF2. No CodeQL
rule was weakened; its check became successful. Baseline GitGuardian status was
unavailable; subsequent candidate checks are separate evidence.

Before release acceptance, review residual OS risk and the final PR/browser
receipts. CORS uses the same-origin proxy; no permissive CORS middleware was
found. Public GETs to `/login` and `/api/health` returned 200 and no CSP, HSTS,
X-Frame-Options, X-Content-Type-Options, Referrer-Policy or Permissions-Policy
headers. These are measured defense gaps, not a demonstrated script-injection
or authenticated clickjacking exploit. Cross-site storage/credential behavior
was not established by a header inventory. No headers or edge settings changed.

Actual API/web containers run as the default root user, without privileged mode,
added capabilities or direct host publication of ports 8000/3000; their root
filesystems are writable. Source Caddy publishes HTTP on port 18080, while
effective outer TLS/origin restrictions remain unverified. Container least
privilege and header hardening remain explicit follow-up context, not a
container-escape finding or a claim of complete perimeter security. No Cloudflare
changes were made. Merge, deployment through the release controller and the
one-time production reset each require separate exact authorization.
