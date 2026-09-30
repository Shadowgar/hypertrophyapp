# Security dependency triage and Caddy candidate

Date: 2026-09-29. Source/main: `a2c9289bc73d475d1f71f67820b5f80b62d88a7c`.
[Authorized package](../plans/m0-security-dependency-remediation.md).

GitHub Dependabot, CodeQL and secret-scanning alert APIs were inaccessible:
CLI REST returned HTTP 401; the installed connector does not expose the alert
endpoints. The owner directed completing available triage and recording the gap.
Each category has **0 records retrieved, total open unknown**. Passing PR checks
do not establish empty alert queues or secret history. No alert was dismissed.

Read-only inventory inspected six open dependency PRs (#25, #26, #31–#34),
actual manifests/locks, deployed API package metadata, web manifests and
container/binary versions. Independent npm, pip-audit and Go/OSV queries were
run from disposable storage. No GitHub alert ID/state is invented for these
independent advisories. This is not a full repository or OS-image vulnerability
scan. No Trivy/Grype was available; other Caddy binary modules and private alerts
remain unqualified.

The managed standalone collection outside Git retains raw npm/pip/Go results,
binary inventory, `triage-finding/v0` JSON, per-advisory report and qualification
harness/output. Its display summarizes **167 component/advisory groups: 2 BLOCK
NOW, 4 FIX BEFORE M2, 161 DEFER**. All 215 imported records, including repeated
aliases/version matches, remain in the JSON; counts are not GitHub alert totals
or severity. Supplemental artifact retention succeeded; it does not repair the
earlier failed managed full-audit export or claim a sealed scan.

| Finding | Severity | Installed / exposure | Fix / risk | Disposition |
|---|---|---|---|---|
| [GO-2024-2963](https://pkg.go.dev/vuln/GO-2024-2963), CVE-2024-24791 | High, CISA 7.5 | Caddy 2.8.4 / Go 1.22.3, affected HTTP transport; early-final/reuse condition plausible, exact exploit unproved | Go 1.21.12/1.22.5 first fixes; candidate Caddy 2.11.4 / Go 1.26.3; medium compatibility risk | BLOCK NOW |
| [GO-2025-3563](https://pkg.go.dev/vuln/GO-2025-3563), CVE-2025-22871 | Critical, CISA 9.1 | Go 1.22.3 ingress chunk parser; incompatible peer-parser prerequisite unproved | Go 1.23.8/1.24.2 first fixes; same Caddy candidate | BLOCK NOW, precautionary |
| [PyJWT detached-payload parsing](https://github.com/jpadilla/pyjwt/security/advisories/GHSA-w7vc-732c-9m39) | Moderate | 2.12.1; preliminary Bearer-token parsing occurs before rejection, no detached workflow; effective size/amplification unqualified | 2.13.0 minor; focused auth negatives required | FIX BEFORE M2 |
| [Starlette Host-path poisoning](https://github.com/Kludex/starlette/security/advisories/GHSA-86qp-5c8j-p5mr) | Moderate | 0.41.3; auth diagnostic selection uses request.url.path, while authorization uses route dependencies; effective malformed-Host edge rejection unqualified | 1.0.1 first fix; compatible FastAPI migration needed, no incompatible override | FIX BEFORE M2 |
| [Go query-parameter budget](https://pkg.go.dev/vuln/GO-2026-4341) | Unrated by imported Go record | Query utility caller and parameter budget unqualified; no form handler | Go 1.24.12/1.25.6; candidate includes fix, qualify limits before growth | FIX BEFORE M2 |
| [Node 20 EOL](https://nodejs.org/en/about/previous-releases) | Maintenance issue, no CVE severity inferred | Deployed 20.20.2 serves Next application | Supported 22/24 line needs separate major-line build/runtime qualification | FIX BEFORE M2 |
| Next 16.2.6 / sharp 0.34.5 | Critical/High/Moderate installed advisories | Linux; actual manifests have zero actions, zero remote-image patterns/domains, WebP output, no i18n; no upload/AVIF asset/next-image source. Rewrite host is operator-controlled. No supported untrusted image/Server Action path established | Next 16.2.11 for older nine; 16.3.3 for later AVIF/Windows findings; sharp 0.35.0/0.35.4 | DEFER; reconsider on feature/input changes |
| Other PyJWT / Starlette findings | High/Moderate/Low | No mixed algorithm/JWK/JWKS decoder, form/file/static response or HTTPEndpoint consumer; Linux defeats Windows condition. No remote auth bypass established | PyJWT 2.13.0; Starlette per-advisory fixes up to 1.3.1 require compatible framework migration | DEFER |
| pypdf 6.10.2 / pip 25.0.1 | High/Moderate/Low | PDF extraction is operator-only offline ingestion; no runtime PDF upload/parser. pip runs during build, not HTTP handling; Python 3.12 defeats old fallback-tar condition | pypdf fixes through 6.16.1; pip per-advisory fixes through 26.2 | DEFER; constrain hostile build/ingestion input |
| Web tooling and other conditional Caddy/Go version matches | Critical through Low; some Go records unrated | Vite/Vitest UI/mocker/esbuild servers absent; no remote CSS/YAML/glob compiler. Dev bytes are copied into runner but are not active servers. Caddy enables encode/plain proxy only; file/PHP/template/mTLS/remote-admin/h2c conditions absent | Per-advisory report retains every version, condition and uncertainty | DEFER; no blanket upgrade |

## Concrete before-M2 and coverage tasks

- **SEC-DEP-01 — BLOCK NOW:** review pinned Caddy candidate; merge and activate
  only under separate authorization. The current task publishes an unmerged PR.
- **SEC-DEP-02:** PyJWT 2.13.0 minor package, with invalid signature/algorithm,
  malformed/detached token and login/recovery compatibility tests. No S2 policy.
- **SEC-DEP-03:** coordinated FastAPI/Starlette qualification for Host/path and
  auth diagnostic boundaries. Current FastAPI pin caps Starlette; do not bypass
  dependency compatibility with a forced override.
- **SEC-DEP-04:** query/header budget and caller qualification. Candidate Go
  incidentally fixes the query issue; future parser/form features need negatives.
- **SEC-DEP-05:** supported Node 22/24 image qualification before M2.
- **SEC-DEP-06 — coverage gap:** retrieve exact private security alert state when
  authenticated access is available. Owner accepted completing available triage,
  not an assertion that no private alerts or secrets exist.

Dependency PRs are proposals, not acceptance: Next #34 misses later 16.3.3
findings; brace #31 misses later 1.1.18/nested 5.0.9 fixes; pypdf #32 misses later
6.16.1 findings; Vite/Vitest #25 uses disruptive majors and misses mocker 4.1.11;
ESLint #33 is a major tooling migration although js-yaml has 4.x fixes. PyJWT #26
offers the relevant 2.13.0 fix. No update PR was blindly merged or modified.

## Candidate qualification

Compose pins `caddy:2.11.4-alpine` to official multi-platform digest
`sha256:6aeddd44c3078b0f9a35206472a11420648a79c184603ef95957d0a20044cb2b`.
Actual Linux/arm64 binary: Caddy 2.11.4, Go 1.26.3, x/net 0.55.0. Other
architectures were not independently qualified. Application dependencies,
source, Caddyfile, schema and credentials are unchanged. Current official stable
same-major image was selected after inspecting the lack of a newer 2.8 patch
line; no mass dependency update or custom transport policy was introduced.

The unchanged Caddyfile adapted and validated with no networking. HTTP checks
used a fresh **internal Docker network with no host-published ports**, the real
qualified API/web images, a read-only root and explicitly disposable SQLite.
A Python guard rejected non-SQLite and paths outside the disposable container
directory. No production network, volume, env/config, account or history entered
qualification. A generated test-only signing key stayed private and was deleted;
it was absent from captured API console/file logs. No live key was touched.

- API health, homepage, Today, Week and reset page: 200.
- Protected API workout/plan routes without credentials: 403.
- Nonexistent-address recovery in the empty test environment: generic accepted,
  no reset credential. No real account was used or created.
- Ten early-final Expect/ordinary-request sequences: passed. Backend connection
  identity was not instrumented; this is compatibility, not exact CVE replay.
- Bare-LF chunk termination: rejected with 502 before a successful application
  response. This shows parser rejection, not a complete smuggling-chain proof.
- Homepage gzip: passed. Original production API/web/Caddy/Postgres container
  IDs were identical before/after; owned test containers/network were removed.

Initial harness failures were setup/input errors (internal-network host-port
assumption, client module-name shadowing and reserved test email domain), not
application regressions; corrected final harness passed. Exact artifact-version
comparison is the strongest focused substitute for the unperformed CVE timing
reproduction. Existing application images were already built and qualified in
PR #42; no new API/web source requires another application build or full suite.

No Caddy production activation, credential rotation, live DB write/wipe/reset/
reseed or destructive migration occurred during dependency remediation. The
production Caddy binary therefore remains affected until separately authorized
cutover. M1-C stays paused. SEC-S2 session revocation, atomic reset consumption,
PostgreSQL concurrency, auth-version migration/cutover and distributed abuse
controls remain incomplete; no whole release/ADR/milestone acceptance.
