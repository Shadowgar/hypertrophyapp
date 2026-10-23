# Existing stack: release-readiness boundaries

This bounded Wave A / Issue #103 package is implementation and isolated
qualification. The approved personal requirements/crosswalk were read directly
from unmerged PR #109 at `4ac9c49b8c9f274dd70784f4ec9027e65592f657`.
PR #111 base is `c656988c2133e5a655c83a9ba87c5f6c47c9308e`;
PR #110 and PR #111 remain independent review items in the unmerged stack.

| Item | Required disposition |
|---|---|
| Measured Today/resume behavior | Larger-history Authored warm target and uniform cold target remain unmet; the additional Customized cold trials leave a possible regression unresolved. Read this package's matched before/after results, sample sizes and limits; local synthetic measurements are not production latency acceptance. |
| Correctness | Fresh query/sequence/late-response/invalidation regressions and real save/retry/correction/undo/resume journeys must be reported for the final application tree. |
| Stack integration | Owner review and separate merge authorization remain required. Stacking a focused PR does not merge the design assets or earlier application PRs. |
| Inherited API failures | Five unresolved: two Authored planned-set total expectations, Authored weekly-review expectation, two missing licensed Phase 1 companion-workbook checks. Preserve assertions and licensing; no fabricated fixtures or accepted waivers. |
| Inherited core failures | Four unresolved: two set/completion-count expectations, two scheduler muscle-coverage expectations. Report final-head results separately from new regressions. |
| GitGuardian | PR #111 flags before/after empty-content SHA-256 checksums under the empty `password_reset_tokens` table-name key in migration evidence. Supporting hashes remain in the stack. No blanket suppression or history rewrite; provider disposition requires appropriate authorization. |
| Canonical security qualification | Remains incomplete: the managed writer rejects group-writable shared parent directories without sticky bit. No supported setup change has been established; do not repeat the blocked export or modify shared permissions. An older scan does not cover this head. |
| Physical iPhone Safari | Pending actual-device execution. Chromium viewport tests cannot qualify keyboard, Safari focus/scroll or background suspension. Use the procedure below on an isolated endpoint. |
| Inherited navigation/resource errors | Desktop shell points to `/programs`, but only `/programs/[id]` exists; its prefetch and `/favicon.ico` return 404. This source predates this slice. Runtime evidence classifies these separately from injected aborts, API/chunk failures and page exceptions; no console-clean claim. |
| Production activation | Separate deployment authorization, target/backup/migration/recovery review and operator acceptance are required. This package does not operate on production data or services. |

## Recorded isolated build

Application source: `912e7e928960069316e81f01a1df08001b0f2a53`.
The production frontend build in `/tmp/hypertrophy-today-perf/apps/web/.next`
has build ID `U4LUcHUOpuJcqc3YzGs16`, with `/api` rewritten to
`http://127.0.0.1:8020`; the isolated browser origin is
`http://127.0.0.1:3020`. Its PostgreSQL database is the verified disposable
`today_performance_1023` on loopback 55418, not production. These addresses
are recorded qualification endpoints; temporary processes can be stopped after
capture. Follow the reproduction instructions to restart the isolated build.
The API marker and listener PID/build checks in the harness distinguish it
from an already running server. They are external test instrumentation, not
production observability or application features.

## Physical iPhone procedure — pending execution

No physical device is available to the automated qualification harness. Use the
final PR head and the package's recorded isolated production frontend build/API
pair. Loopback addresses in the measurements are not reachable from a phone;
create a separately verified, access-controlled HTTPS development endpoint
pointing only to that isolated pair and its disposable PostgreSQL database.
Do not point the endpoint to production or expose test-only cleanup routes.

1. Record exact commit/build, proxy destination, disposable database identity,
   iPhone model, iOS/Safari version, orientation and keyboard settings. Use only
   synthetic accounts from the isolated fixture manifest; never publish tokens.
2. Test both Authored and explicitly consented Customized accounts. Open an
   already scheduled unstarted workout, then a partially completed occurrence.
   Measure navigation to visible workout and usable first-set controls; record
   slow/loading, rest-day/no-schedule and genuine failure states separately.
3. On Cross-Body Lat Pull-Around, verify source targets and warm-up, saved lb/kg
   preference, provisional versus qualified-history guidance, and editable actual
   values. Save with weight/repetition keyboard visible; record control bounds,
   scroll and one confirmed receipt/rest timer. Continue the next set.
4. Edit actuals while a guidance refresh is delayed. They must remain edited.
   Inject test-only failure before commit and response loss after commit; reload
   and retry the frozen command. Verify one effective set in the isolated DB.
5. Correct a prior receipt with response loss, close/reopen, try another receipt,
   background/lock the phone beyond the rest deadline, then reload and retry.
   Confirm the original receipt/command/payload, one correction and preserved
   superseded record. Undo and resume; check History in both units.
6. Switch synthetic accounts and test delayed responses. Old workout/advice must
   never appear as the new account's current session. Test date/revision conflicts
   without silently regenerating or activating a different workout.
7. Capture sanitized recordings, timings, console errors and VoiceOver/control
   focus observations. Remove the temporary endpoint afterward. Record failures
   as failures; do not infer acceptance from desktop or Chromium results.
