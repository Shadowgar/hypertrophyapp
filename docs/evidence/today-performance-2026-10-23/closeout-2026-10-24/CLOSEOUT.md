# PR #112 — bounded Customized cold-start closeout

Date: 2026-10-24. Input PR head `f79a4382e92028ec20b452dd409da0c52a48d931`;
application source remains `912e7e928960069316e81f01a1df08001b0f2a53`.
**No application fix is justified by this investigation. A material source cause
was not established; absence of a regression is not established either.**
The Authored gains and account/occurrence/recovery safeguards are retained.
This closes the bounded investigation, not Issue #103 or production acceptance.

## Controlled comparison

The existing real Next production builds and real API used verified disposable
PostgreSQL `today_performance_1023` / `m2a_test`, loopback 55418. Docker inspection
again showed tmpfs storage, no volume mounts and a loopback-only port. The same
four ordinary synthetic accounts were reused: Customized small unstarted/resume,
Authored large unstarted/resume (100 prior synthetic occurrences). No plans were
regenerated and no calibration/history was seeded for this pass.

| Variant | Frontend | API | Purpose |
|---|---|---|---|
| Base | PR #111 `c656988`, original build `5gupZD75mVy5ZATfTF18I` | `c656988` | Full before case |
| Candidate | `912e7e9`, original build `U4LUcHUOpuJcqc3YzGs16` | `912e7e9` | Actual PR #112 application |
| Control | Scratch checkout of `f79a438`, **only Today page restored from `c656988`**; build `QfLM-LREb8vvitNYZHys8` | `912e7e9` | Isolate Today frontend changes while retaining optimized backend |

The control is an experiment, not a proposed rollback or integration artifact.
Its `api.ts` retains the candidate retired-token protection. No request received
a 401, so that guard's token-reading branch did not execute. The same pinned
Next 16.3.7/React 18.3.1 dependencies, webpack production mode, API rewrite,
viewport (390×844), native loopback network and manual actual-entry draft were
used. All three route manifests hash identically. Today JS is 96,281 / 99,848 /
96,285 uncompressed bytes respectively; size alone does not establish latency.

Four repetitions used pair-order-balanced sequences B–C–R, R–C–B, C–B–R,
R–B–C. Every case starts owned API/frontend processes and a fresh Chromium
process/context, then opens one warm page in that context after network idle.
Health/root readiness probes precede the clock. Each listener's process group,
working directory, unique API marker and live frontend build ID were checked.
The existing fixture's Friday calendar was explicitly fixed at October 23 in
browser and routing modules; JWT authentication kept its actual clock. This
prevents Saturday routing from changing the test occurrence. Same-day soreness
was explicitly skipped through the existing synthetic preference key.

No build or test suite ran during the measurement window. The shared ARM64 host
was not exclusive: one-minute load averages ranged 5.75–12.57. Filesystem and
PostgreSQL caches were not cleared. The study cannot uniquely identify host,
proxy, browser scheduling or build/cache effects. Process-cold is not OS-cache
cold, server-boot time or physical-iPhone acceptance.

## Results

Seconds to editable weight/repetition fields and an enabled Save action after
the same manual draft. **n=4 per cell**, 96 navigations total. Brackets are
observed min–max; these small samples do not support production p95 claims.

| Case | Phase | Base median [min–max] | Candidate median [min–max] | Today revert control median [min–max] |
|---|---|---:|---:|---:|
| customized-small-unstarted | cold | 2.436 [1.827–5.302] | 2.249 [2.050–4.429] | 2.097 [1.732–4.007] |
| customized-small-unstarted | warm | 0.895 [0.696–1.903] | 1.549 [1.429–1.868] | 1.265 [0.763–1.872] |
| customized-small-inprogress | cold | 1.960 [1.361–2.809] | 2.062 [1.477–6.538] | 3.771 [2.286–6.608] |
| customized-small-inprogress | warm | 0.825 [0.751–1.183] | 1.379 [0.842–1.854] | 1.496 [1.223–2.262] |
| authored-large-unstarted | cold | 5.968 [4.771–11.413] | 4.018 [3.236–8.728] | 3.910 [3.608–5.228] |
| authored-large-unstarted | warm | 3.887 [3.843–5.473] | 2.461 [2.360–3.679] | 2.737 [2.292–3.185] |
| authored-large-inprogress | cold | 5.944 [5.396–6.477] | 3.433 [3.028–3.804] | 3.953 [3.851–4.160] |
| authored-large-inprogress | warm | 4.062 [3.749–4.145] | 2.682 [2.339–2.968] | 2.758 [2.545–3.162] |

Customized warm results remain unfavorable versus base and are not omitted.
The frontend-revert control also has unfavorable warm results. For cold
Customized resume, candidate minus control per repetition is −70, −3,352, −65,
−809 ms; for unstarted it is −1,957, +2,212, +274, +514 ms. Reverting Today does
not produce a repeatable improvement across both paths. This tests that change
set; it does not isolate every backend/build/host interaction or prove that all
possible source effects are absent. No additional optimization cycle was run.

## First navigation, initialization and required reads

- **Assets:** the base itself produced a retained 5.302 s Customized unstarted
  navigation. Its Today JS response span was about 2.201 s, while aggregate
  script duration was 2.641 s. The candidate resume outlier was 6.538 s with
  only 278 ms aggregate script duration; the revert control reached 6.608 s.
  Slow first navigation is therefore not exclusive to the added Today code.
- **Initialization/hydration:** AppShell's existing hydration/token gate,
  AppearanceProvider, fonts and navigation prefetch implementation are unchanged.
  Browser navigation/resource timing, long tasks and CDP Script/Task/Layout
  durations were recorded. The first Today `/health` fetch is an effect-start
  proxy, **not a direct React hydration timer**. Cold resume median proxy times
  are 791 / 595 / 1,857 ms (B/C/R), and aggregate script duration 285 / 264 /
  377 ms. No consistent added initialization cost is established. These totals
  include other browser work and cannot attribute cost to individual hooks.
- **Required API gates:** no new cold-read endpoint was introduced. Date and
  weekly review remain required, starting together in the candidate. Profile
  starts alongside progress; it does not gate accepted controls. Each navigation
  fetched Today exactly once. The candidate 6.538 s sample spent about 3.4–3.5 s
  in the browser's date/review requests; corresponding API middleware elapsed
  times were 48 / 38 ms, with 9 / 14 ms SQL time. That gap is outside measured
  API handler work, but cannot be assigned uniquely to proxy, upstream queue,
  transport or browser scheduling.
- **Deterministic backend:** Customized SQL counts stay 19 unstarted / 22 resume
  in all variants and phases, with zero Authored snapshot calls. No Customized
  policy, source prescription, consent or load owner changed. Authored gains
  remain visible in the matched opening/resume data. The added same-occurrence
  variant comparison and retired-account guards do not add a cold-read await.

The evidence supports retaining the correctness protections, rather than
shipping an unproven rollback or speculative optimization. A possible smaller
source-related or build/host interaction remains unresolved.

## Original observations and targets stay intact

The [original report](../RESULTS.md) and every original artifact are unchanged:
Customized-small resume cold median **1.586 → 2.541 s**, retained candidate
**7.353 s** sample; additional ABBA base **1.325 / 1.517 s**, candidate
**2.474 / 1.614 s**. These are not pooled with this different measurement window
or reclassified as invalid. Every new performance sample is retained, including
base Authored 11.413 s and candidate Authored 8.728 s samples.

Original predeclared targets remain: usable controls ≤2 s warm / ≤5 s cold, and
≥25% lower observed maximum where a bottleneck was demonstrated. Large Authored
warm controls still exceed two seconds. Cold is not uniformly within five
seconds. The original unstarted maximum improvement was 37%, resume 11%, so
maximum-target achievement was partial. New samples do not overwrite that
qualification or authorize unrelated architecture changes. The owner's original
two-minute production symptom remains **not reproduced**.

## Preservation, checks and limits

All **96 complete Today payloads** match exactly by case across variants,
repetitions and cold/warm navigation, without field exclusions. The eight
ordinary accounts' ten training/presentation table hashes/counts still match the
original October 23 checkpoint; account rows match privately too. The new
pre-measurement fingerprint helper failed to save because the guarded wrapper
cleared its extra environment variable. Its corrected argument-based helper
compares the original retained checkpoints. No latency sample was excluded.
No account/auth values or JWTs are published.

Fresh focused PostgreSQL checks on separately verified `m2a_qualification`:
**172 passed, zero failed/skipped, 110.01 s** across history snapshot,
initial calibration, load intelligence and source warm-up suites. Final-head
web/API/CI results and exact documentation head are recorded in PR #112's
closeout qualification comment. Five inherited API failures and four inherited
core failures remain separate; no waiver, weakened assertion or fabricated
licensed workbook is introduced.

No application path changed, so earlier actual save/correction/undo/lost-response
captures retain their original `912e7e9` provenance; they are not relabeled as new
captures. Fresh web tests include late replies, account switches, edited drafts,
retired-account undo and immutable retry cases. This pass's new browser evidence
qualifies opening/resume only. It captured no unhandled page exceptions or
unexpected HTTP/request failures, but is not a full clean-console/hydration audit.
No duplicate screenshots were added.

GitGuardian on this PR is reported separately from PR #111's retained checksum
finding. [Canonical security qualification remains blocked](../../unified-ux-gym/correction-pass/SECURITY.md)
by the managed writer's non-sticky group-writable parent rejection; no supported
setup change or rerun, shared chmod, sealed report or final-head scan pass is
claimed. Physical iPhone Safari remains pending under the [existing isolated
procedure](../RELEASE-READINESS.md). Chromium does not qualify its keyboard or
background behavior. All owned measurement processes were stopped.

See [condensed measurements](measurements.json), [reproduction](REPRODUCE.md)
and [integration recommendation](INTEGRATION.md). No merge, deployment,
production migration/data operation or Home/onboarding implementation occurred.
