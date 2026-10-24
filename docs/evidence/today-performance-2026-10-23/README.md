# Today loading and resume — bounded Wave A qualification

Draft PR #112 is stacked on PR #111 at
`c656988c2133e5a655c83a9ba87c5f6c47c9308e`. The measured application revision is
`912e7e928960069316e81f01a1df08001b0f2a53`; later evidence commits do not alter
that application tree. PR #110 and PR #111 are unchanged. This implements the
owner-authorized Today/resume performance slice, without changing training
policy, plan activation, source prescriptions, schema or the broader Home flow.

The matched local measurements show a substantial Authored improvement. With
100 prior synthetic exposure sessions, median time to usable first-set controls
fell from about 3.97 to 2.71 seconds for an unstarted workout and from 4.09 to
2.77 seconds for resume. The two-second warm target is **not met** in those
cases. Cold measurements include a 7.35-second Customized outlier; the
five-second cold target is **not uniformly met**. These are shared-host,
loopback synthetic measurements, not production percentiles or physical-device
acceptance. The owner's original two-minute symptom was not reproduced.

- [Results, sample sizes, spreads, phases and request waterfalls](RESULTS.md)
- [Reproduction, disposable fixtures and external measurement scripts](REPRODUCE.md)
- [Environment, source hashes, builds and dataset sizes](environment.json)
- [Exact response and scoped database preservation comparisons](preservation.json)
- [Rendered mobile and desktop recovery gallery](GALLERY.md)
- [Recorded correctness and application CI results](qualification.json)
- [Release readiness and physical-iPhone procedure](RELEASE-READINESS.md)

## Observed bottlenecks and bounded source changes

The Authored response reconstructed effective history once already, but repeated
calibration queries, source/setup history normalization and warm-up artifact
loading across exercises. The small request-budget regression reproduces six
calibration queries becoming one for three exercises; a larger history case
reduces source normalizations from 288 to 30; three warm-up protocol reads become
one. Real larger-history instrumentation identifies repeated source hashing and
warm-up projection as material costs. See the phase tables for inclusive timing
boundaries; nested phases must not be added as independent elapsed time.

`AuthoredHistorySnapshot` remains scoped to a single account, database session
and response. It batches account-filtered calibration revisions, indexes history
presence by source/setup with the existing inclusive performed-date cutoff, and
lazily retains the source protocol for each projected program. Existing history,
initial-calibration, load and core warm-up owners still make the decisions.
Protocol/provenance copies prevent one projection mutating another. Commands
construct fresh snapshots, so amendments and new calibration are not hidden by
cross-request caching. No global or cross-account cache was introduced.

On the frontend, independent date-context and weekly-review checks start
together, but both remain required before Today. Display profile loading starts
alongside progress instead of delaying it. The accepted Today payload can expose
usable controls while nonblocking profile/progress reads finish. Required
refreshes hide the prior runner until occurrence authority is established;
failures remain visible and retryable. Page/account/request generations reject
retired responses. Same-occurrence guidance refresh preserves edited actuals and
frozen pending commands while updating live advice; a confirmed performed-variant
change invalidates the changed slot's authority caches. A late 401 from a retired
account cannot clear the current account's token. No server authorization rule
changed.

Customized requests do not enter the Authored projection path. The initial
matrix contains slower larger-history Customized API samples, which are
retained. A separate counterbalanced base/candidate/candidate/base series did
not show a consistent candidate slowdown; this does not prove host variation is
the cause or establish a general Customized speed gain. A further four-block cold-browser check recorded base 1,325 ms, candidate
2,474 ms, candidate 1,614 ms and base 1,517 ms. Both candidate samples are
slower than both base samples. With two samples per revision this does not
establish causality, but it leaves a possible cold-start regression unresolved;
it is not dismissed as noise. The original 7,353 ms sample remains included.

## Correctness and review disposition

The completed application-revision CI is
[run 40010366351](https://github.com/Shadowgar/hypertrophyapp/actions/runs/40010366351):
web **313 passed** across 49 files, with lint/typecheck/build passing; API
**952 passed, 5 failed, 120 skipped**. The five failure names match the verified
base run. Overall CI remains failed. Core was not selected for this change;
PR #111's earlier 859 passed / 4 failed result is historical, not final-head core
coverage. The release-readiness document retains each inherited category.

The focused backend run against verified disposable PostgreSQL passed **172
cases without skips**, including existing initial-load, load-intelligence and
warm-up tests. It covers exact response equality against a test-only frozen
pre-optimization oracle, account/session/setup/occurrence isolation, inclusive
history cutoff, calibration freshness, correction/undo/retry and response-copy
isolation. The ordinary measurement accounts additionally have **24 exactly
equal complete Today/progress/summary responses**, unchanged hashes/counts for
10 scoped training/presentation tables, and unchanged account rows in a private
comparison. No auth/reset-token hashes are republished in this package.

The following are bounded implementation-review findings, not invented GitHub
review threads. GitHub PR #112 had no review threads at the recorded review;
recheck the live PR for later comments.

| Finding | Disposition / fixing commit | Relevant verification |
|---|---|---|
| Repeated Authored calibration, source/history and protocol work | `8d92077`; request-local batching/index/protocol reuse | `test_authored_history_snapshot.py`: query/normalization/read budgets, baseline response oracle, cutoff, ownership and copy-isolation cases |
| Sequential independent reads and profile blocking progress | `8d92077` | `today.loading.test.tsx`: concurrent gates, slow profile, usable controls before auxiliary reads |
| Late reads and unresolved refresh expose stale authority | `8d92077` | Loading/load-intelligence regressions: retired responses, unmount, required review, failure/retry, late progress after save and draft retention |
| Same-occurrence Customized advice retained after accepted refresh | `912e7e9` | `today.customized-calibration.test.tsx`: accepted refresh replaces advice/receipts while retaining edited or uncertain draft |
| Remote confirmed variant retained old slot advice/context | `912e7e9` | `today.load-intelligence.test.tsx`: external confirmed-variant reload preserves original frozen command while retiring source advice |
| Retired account undo state leaked into current account | `912e7e9` | `today.undo-recovery.test.tsx`: account-switch/late undo regressions |
| Retired account 401 could clear new account's token | `912e7e9` | `api.auth-token.test.ts`: retired-token rejection preserves current token; current-token 401 still clears |
| Initial Today visual snapshot lacked intentional busy/disabled state | `912e7e9`; reviewed snapshot and readiness wait | `visual.routes.snapshot.test.tsx`; all 313 final application web tests pass |

Runtime recovery screenshots and assertions are linked from the results and
reproduction documents. They use separate synthetic accounts so mutation
journeys do not change the ordinary before/after dataset. An attempted journey
with an incoherent timezone/week fixture was discarded and rerun after fixing
the fixture, not counted as an application pass.

## Acceptance boundaries

Issue #103 remains partial. This package does not qualify physical iPhone Safari,
production latency or every starting-load eligibility case, and does not close
inherited test failures or incomplete security qualification. The blocked
canonical security export was not repeated without a supported setup change.
GitGuardian checksum evidence in PR #111 remains intact, without suppression or
history rewriting. There was no Home/onboarding expansion, merge, deployment,
production migration or live-data change.
