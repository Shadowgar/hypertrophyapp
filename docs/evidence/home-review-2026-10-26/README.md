# PR #119 independent Home review

Scope: owner-authorized Workstream A, 2026-10-26. Candidate source is this PR; no merge, production deployment, account inspection or persistence operation is included. All test identities and responses are synthetic.

Reviewed baseline: PR #119 `0926c8f9807f638ae76158078ac61570988bb02e`, against main `ad789ff983a51c2445fde34c849d3738fcb0311a`. Approved visual reference: PR #108 `33598c3fb35328cc2d2b6310865f716380b6c81e`, `docs/ux/astra-2026-10-20/unified-2026-10-21`, Home screens 10/11. The complete three-file PR diff, reviews, inline threads and current checks were inspected. Initial PR was draft, merge state CLEAN, with no submitted reviews or inline threads. Its latest web checks and CI qualification passed; API/core/container jobs were skipped, not passed. CodeRabbit explicitly skipped draft review.

## Decision and findings

Retain and repair the existing PR. Its guest/authenticated split and explicit unknown/loading states are useful, but the original implementation was not ready for acceptance.

| Finding in reviewed head | Repair and boundary |
|---|---|
| `Promise.allSettled` withholds the available workout until profile, analytics and weekly-review requests all settle. | Each resource settles independently. Today can become actionable while optional reads remain pending or fail. |
| Only a successful null Today response is understood as no workout. The API actually returns 404 with three named domain details. | Recognize only `No plan generated`, `No workout scheduled today`, and `No workouts available`. Unknown 404s, 409 conflicts and other failures remain retryable. A week-empty statement additionally requires an acknowledged current scheduling context with `plan: null`; a Today 404 alone never proves a rest day or empty week. |
| Home ignores auth-token/storage changes and accepts results using a mount flag only. An expired token or changed account can leave private data visible. | Reset all page resources on auth/storage/focus identity changes. Require matching token, request generation and mounted page before publishing success or failure. Existing API token-matched 401 clearing remains authoritative. No shared auth implementation is changed. |
| Retry replaces its button while loading, losing keyboard focus. Optional failures have no recovery control. | Keep retry mounted and focusable across its pending attempt, with `aria-disabled` preventing duplicate activation; expose readable status. |
| “Next session” is only a Today result, and the many coaching/radar modules obscure the approved next action. | Use existing current/next-week scheduling context to preview actual future selected dates. Future previews link to Week; Today alone owns opening/resume. Preserve current-week program identity when the future program differs. Move factual mass/load/history summaries into optional disclosure; remove inferred coaching, weak-area and deload directions. |

The Home page does not select/activate programs, generate a plan, submit reviews, change preferences or modify prescriptions/history. It uses the existing `workout_today` and selected-date `scheduling_context` owners. Profile effective program/day fields remain read-only. Authored Phase 1/2 and Customized consent are unchanged.

## Controlled latency comparison

A temporary Vitest comparison rendered both the exact reviewed Home and the repaired Home with identical responses. Workout/profile/review settled at simulated 100 ms; analytics settled at simulated 4,000 ms. Both assertions passed:

| Client | Action visible at 100 ms | Action visible at 4,000 ms |
|---|---|---|
| Original `0926c8f` | No | Yes |
| Repaired Home | Yes | Yes |

This demonstrates 3,900 ms of avoidable client coordination delay for that controlled case, not API, production or physical-device latency. A never-settling analytics regression also proves that the workout no longer waits for analytics. The temporary original component/comparison fixture is outside the candidate; no second application route was introduced.

## Qualification

Final local checks:

- `node node_modules/vitest/vitest.mjs run --maxWorkers=1 --no-file-parallelism --pool=threads --cache=false --reporter=dot`: **344 passed, 50 files**, 223.46 s. Final focused Home/state/unit regressions: **41 passed**. Existing Today/Link React `act` warnings remain; no test was skipped. The preceding full run had two Home summary-unit selector failures (335 passed); the final run preserves converted trend/working/bodyweight values, live unit changes without refetch, profile fallback and unchanged canonical fixtures.
- `node node_modules/typescript/bin/tsc --noEmit --incremental false`: passed. The final `npm run build` also passed TypeScript and the optimized route build on Next 16.3.7.
- `node node_modules/eslint/bin/eslint.js .`: 0 errors, seven inherited hook dependency/ref warnings in appearance-provider, technique-entry and use-atlas-set. Focused changed-file lint passed.
- `git diff --check`: passed.
- Initial red run against the original Home: ten new behavior failures and two existing error-boundary passes. Follow-up red/green cases distinguish pending/unavailable program details and prevent an active workout from inheriting a different program label from profile preferences or an unrelated calendar snapshot. One cold forks-worker attempt failed to start; the single-thread retry executed the intended tests. A baseline Week snapshot timed out under host load, then passed in focused and full runs. One build attempt failed TS6053 after temporary comparison files were removed during its file scan; the stable candidate was rebuilt successfully after those fixtures were removed. These environment/procedure failures are not reported as passes.

Playwright used a fresh browser context, local production build at `127.0.0.1:3127`, intercepted synthetic `/api/**` responses and an otherwise unreachable server API origin `127.0.0.1:9`. No database was started or accessed. Verified:

- Guest Home made zero account API calls. Synthetic returning sign-in returned to Home; the sole POST was synthetic `/auth/login`, with no profile, review, plan or preference write.
- Classic, Graphite and Charcoal, each light/dark, at **1440×900** and **390×844**: correct saved palette and kg display, 48 px workout action, no horizontal overflow, no onboarding action for the returning account and no JavaScript runtime errors.
- Analytics held for 4,000 ms: the workout action was already visible **651 ms after the mocked workout response** and remained available throughout the hold. This wall-clock browser observation is synthetic and host-load dependent, separate from the controlled timing comparison above.
- Keyboard retry after a 503 recovered to Resume and retained retry focus. Acknowledged empty week offered Choose dates; future selected-date workout offered Review Week, never Today. A 401, account switch with delayed old analytics, and cross-tab logout cleared prior private content. All state-probe requests were GETs; no JavaScript runtime errors occurred.
- Final program-identity browser negatives also passed: both workout-owned ID fields, explicit Customized mode and missing identity ignored a conflicting Phase 1 preference/calendar, while the workout action remained available. The final stable source was rebuilt successfully and representative screenshots were refreshed.
- Browser harness setup initially used the wrong existing Login button name and a network-idle wait that timed out on unrelated prefetch under host load. Corrected control locators and actual rendered-readiness waits passed; no application fix is claimed for those setup errors.

Representative synthetic screenshots: [Home mobile](screenshots/home-mobile.png), [empty week mobile](screenshots/empty-mobile.png), [Graphite light desktop](screenshots/home-desktop-light.png). All twelve palette/viewport combinations were exercised; these three keep review evidence compact.

An independent narrow static review of the page's auth synchronization and request guards found no concrete surviving account-response leak. A subsequent wider source review found a program-identity mismatch: profile preferences could label an active workout whose program differed. The final page uses workout-owned `program_template_id` / `selected_program_id`, an explicit Customized marker, or a calendar entry with the exact same occurrence ID. Missing identity stays checking/unavailable. Four mismatch fixtures exercise the two response fields, Customized and unknown against a conflicting profile/calendar. The reviewer rechecked the fix and reported no further concrete source finding. Reviewed SHA-256: page `3005c48b4d0b4327c393dba576c47e867846bad5fb6452045c8ff0559d58a4da`, state tests `b368e732341f94ad03208afceccb9bee66ed392479af201b38dcd35e74fa9059`. This is not a repository-wide security certification or a canonical Codex Security export. Physical iPhone gym acceptance remains pending. Browser fixtures cannot qualify database routing, real account behavior or production latency. This branch retains its existing dependency baseline; the independent security candidate must be considered separately before release.
