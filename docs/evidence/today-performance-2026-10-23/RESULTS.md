# Matched measured results

All durations are milliseconds. Brackets show min–max; the right endpoint is the observed maximum. These small samples do not estimate production percentiles. Every retained ordinary readiness trial reached editable load/repetition inputs and an enabled Save action. Filling the same manual draft is part of the readiness measurement; no set was saved.

## Ordinary navigation

Five serial trials per case and revision; API process primed by the separate API batch. Each case uses one fresh browser context: trial 1 is its first page, trials 2–5 reuse that context with a new page and retained occurrence selection. Next production process remains running throughout the matrix. Browser work waits for network idle only after the readiness timestamp, to drain background work before the next trial.

| Scenario | Visible median before → after | Usable before median [range] | Usable after median [range] | Observed max change |
|---|---:|---:|---:|---:|
| authored-small-unstarted | 1555 → 826 | 1722 [1541–3289] | 1023 [906–2779] | -15.5% |
| authored-small-inprogress | 1535 → 1043 | 1692 [1610–1817] | 1264 [921–1522] | -16.2% |
| authored-large-unstarted | 3821 → 2504 | 3969 [3752–4693] | 2710 [2530–2966] | -36.8% |
| authored-large-inprogress | 3864 → 2610 | 4087 [3861–4219] | 2773 [2523–3773] | -10.6% |
| customized-small-unstarted | 695 → 672 | 885 [774–1825] | 803 [758–920] | -49.6% |
| customized-small-inprogress | 726 → 679 | 885 [821–1058] | 807 [785–855] | -19.2% |
| customized-large-unstarted | 833 → 877 | 987 [930–1265] | 1066 [1011–1245] | -1.6% |
| customized-large-inprogress | 998 → 1088 | 1171 [1116–1816] | 1253 [1057–1336] | -26.4% |

[Before raw](baseline-browser.json) · [After raw](after-browser.json)

## Verified process/browser cold

Three independent frontend/API process starts and fresh browser contexts per case and revision. Startup/readiness probes precede the navigation clock. Every run verifies unique API response marker, live frontend listening PID/worktree and BUILD_ID. PostgreSQL and filesystem caches were not cleared.

| Scenario | Before median [range] | After median [range] |
|---|---:|---:|
| authored-small-unstarted | 3072 [2744–3432] | 2955 [2251–2957] |
| authored-large-inprogress | 4970 [4693–5515] | 3182 [2877–3341] |
| customized-small-inprogress | 1586 [1360–2273] | 2541 [1970–7353] |
| customized-large-inprogress | 1986 [1974–2815] | 1738 [1663–1738] |

[Before raw](baseline-cold-browser.json) · [After raw](after-cold-browser.json)

The 7,353 ms Customized-small candidate cold sample is retained. Its visible-workout timestamp is 6,849 ms. Its Today-page JavaScript resource spans about 3,251 ms from resource initiation to response end, with other shared chunks around 1.9 s. API requests occupy a smaller later portion of this navigation. These observations locate a cold asset/client-bootstrap window; they do not establish its causal source.

## Direct API

Five serial HTTP requests per scenario and revision, using the real API and PostgreSQL.

| Scenario | Before median [range] | After median [range] |
|---|---:|---:|
| authored-small-unstarted | 786 [723–1000] | 166 [165–356] |
| authored-small-inprogress | 825 [720–863] | 176 [172–272] |
| authored-large-unstarted | 3060 [2925–3440] | 1616 [1421–1777] |
| authored-large-inprogress | 2919 [2847–2966] | 1416 [1292–1513] |
| customized-small-unstarted | 122 [110–215] | 114 [112–125] |
| customized-small-inprogress | 132 [131–136] | 134 [131–168] |
| customized-large-unstarted | 229 [213–407] | 269 [201–317] |
| customized-large-inprogress | 245 [228–356] | 327 [231–586] |

[Before raw](baseline-api.json) · [After raw](after-api.json)

## API work per request

The following measurements use the first five scenario-tagged Today requests in each instrumentation file: exactly the direct API batch above. Phases are inclusive and overlap; do not add them.

Authored large in-progress, n=5:

| Measure | Before median | After median |
|---|---:|---:|
| Total ms | 2914.7 | 1411.5 |
| SQL statements | 21.0 | 10.0 |
| SQL execution ms | 241.5 | 217.1 |
| Calibration SELECTs | 12.0 | 1.0 |
| History grouping: calls / ms | 1 / 1007.7 | 1 / 887.1 |
| Source scope, load-state binding: calls / ms | 7212 / 853.3 | 607 / 72.0 |
| Calibration lookup: calls / ms | 6 / 24.1 | 6 / 0.9 |
| Source warm-up protocol read: calls / ms | 6 / 719.7 | 1 / 87.8 |
| Per-slot warm-up calculation/assembly: calls / ms | 6 / 728.7 | 6 / 7.8 |
| Per-slot load feedback projection: calls / ms | 6 / 1653.1 | 6 / 119.8 |

[Before phase samples](baseline-api-phases.json) · [After phase samples](after-api-phases.json). Calibration report rows are **zero** in all eight ordinary cases; absence lookup is measured, rather than calibration-heavy version history. Dedicated runtime journeys cover saved calibration and qualified-history precedence. The standalone pre-change source-protocol probe is [recorded separately](baseline-source-warmup.json).

## Representative request waterfall

Authored large in-progress: select the median-usable trial within each five-trial batch. Start offsets are relative to the first resource in that navigation; duration is resource response end minus request start. Background endpoints may finish after usable controls.

| Request | Before start / duration | After start / duration |
|---|---:|---:|
| /api/profile/preferences | 260 / 318 | 250 / 80 |
| /api/health | 573 / 255 | 328 / 39 |
| /api/plan/scheduling-context | 597 / 165 | 381 / 189 |
| /api/weekly-review/status | 765 / 33 | 384 / 99 |
| /api/workout/today | 798 / 3029 | 573 / 1908 |
| /api/profile | 3832 / 21 | 2483 / 30 |
| /api/workout/<occurrence>/progress | 3902 / 3428 | 2484 / 1812 |

## Explicit first-use construction

Three unique fresh accounts per mode and revision. Construction uses the existing injected Monday planning clock, with a coherent Mon/Wed/Fri week; ordinary loads use actual Friday. Authored preview then `/plan/generate-week` activation and Customized proposal/challenge/accept/activation invoke the real application and PostgreSQL through TestClient. Their timing excludes HTTP transport and browser rendering; it must not be compared directly to the ordinary HTTP/API table. All phase calls returned 200.

| Mode / phase | Before median [range] | After median [range] |
|---|---:|---:|
| authored / /plan/selected-dates/preview | 4197 [4036–4464] | 4185 [4110–4263] |
| authored / /plan/generate-week | 4521 [4223–4660] | 4196 [4040–4395] |
| customized / proposals | 349 [319–497] | 323 [317–611] |
| customized / challenge | 402 [276–414] | 390 [282–524] |
| customized / accept | 370 [333–431] | 432 [331–434] |
| customized / activate | 383 [379–517] | 387 [384–553] |

First navigation to the newly activated Authored plan through the real production frontend, n=3 unique accounts each: usable 3355 [3018–3559] before, 1750 [1685–1979] after. The browser opens the actual Friday response, independent of the Monday construction clock.

A separate three-account no-plan Today probe returned 404 in both revisions. That is an empty state, not first-plan construction or a slow-workout success. See [before](baseline-first-use.json) / [after](after-first-use.json).

## Customized counterbalanced follow-up

The initial unfavorable Customized-large API samples remain in the direct API table. Four quiet API-only ABBA process blocks use the same two ordinary accounts; each block excludes one startup warm-up request per path and retains five measured requests per path.

| Scenario | Base block 1 | Candidate block 2 | Candidate block 3 | Base block 4 |
|---|---:|---:|---:|---:|
| customized-large-unstarted | 245 [205–302] | 292 [206–356] | 207 [205–353] | 259 [209–345] |
| customized-large-inprogress | 275 [229–362] | 258 [225–372] | 249 [227–413] | 239 [226–350] |

The initial slowdown does not reproduce consistently by source across these blocks. Both sources vary with block/order. This supports a variability limitation; it does not prove its exact cause or establish absence of every regression. SQL counts remain 19/22 for unstarted/in-progress and no Authored snapshot/protocol/calibration work enters these Customized paths. [All ABBA samples, including warm-ups](customized-abba-api.json).

Additional four cold-browser ABBA trials retain the original cold outlier and add two independent trials per source:

| Block | Source | Visible | Usable |
|---|---|---:|---:|
| 1 | base | 1111 | 1325 |
| 2 | candidate | 2146 | 2474 |
| 3 | candidate | 1334 | 1614 |
| 4 | base | 1186 | 1517 |

[Additional cold ABBA raw](customized-cold-abba.json). These samples supplement the original n=3 matrix; they do not replace it. Both additional candidate observations are slower than both base observations. A possible cold-startup regression remains unresolved; the initial 7,353 ms sample is retained. The production Today page chunk grew from 96,281 to 99,848 bytes (+3,567 / 3.7%); file size is observed, not a proven cause.

## Targets and preservation

The predeclared local targets were usable controls within 2 s warm / 5 s process-browser cold, and at least 25% lower observed maximum where a bottleneck was demonstrated. The 2 s target is unmet for large-history Authored navigation. The 5 s cold target is not uniformly met, including the retained 7,353 ms Customized sample. Ordinary large-Authored unstarted observed maximum improves 37%; in-progress improves 11%, below the 25% maximum target despite a lower median. These are partial performance gains, not uniform target acceptance.

All 24 complete Today/progress/summary JSON payloads compare exactly across the same eight ordinary accounts before intentional runtime-journey writes. All ten scoped training/presentation table hashes and counts match, and the eight ordinary account rows also compare unchanged privately. [Preservation proof](preservation.json). Fresh first-use and dedicated runtime accounts append legitimate synthetic rows outside that scope.

An earlier cold attempt accepted an existing owned warm listener after port-bind failure. Those invalid samples were removed from the public results and rerun with fatal occupied-port/process checks, a unique API response marker and live frontend PID/worktree/BUILD_ID verification. No invalid cold sample contributes to these tables.

## Preconditions and limits

The browser harness stores the synthetic token and the existing same-day soreness-skip key before navigation. Thus readiness is measured after that optional check-in was explicitly skipped; soreness interaction latency is outside these numbers. No two-minute Today delay was reproduced. All accounts/data are synthetic, the network is native loopback, and server/browser processes share this ARM64 production host with uncontrolled background load and warm filesystem/PostgreSQL caches. Chromium viewport results do not qualify physical iPhone Safari, keyboard, focus or background suspension.

Runtime resource qualification retains inherited `/favicon.ico` and `/programs?_rsc` 404s. The baseline already links to `/programs` in `components/app-shell.tsx:15` while lacking an index route; resource/console paths remain in the journey evidence. These are remaining navigation/resource defects; console output is not described as clean. Intentional response-loss injections also produce expected `net::ERR_FAILED` messages.
