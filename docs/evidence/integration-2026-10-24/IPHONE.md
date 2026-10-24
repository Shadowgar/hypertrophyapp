# Physical iPhone Safari acceptance — pending

No physical device was available. Chromium mobile viewport evidence is supplementary
and **does not qualify iPhone keyboard, Safari scroll/focus or suspension**.

## Exact isolated candidate pair

Use this integration branch's final head (record the full SHA from the PR), runtime
trees listed in [manifest](manifest.json), web build **`ZLEpb6JBscpHyieWEipdp`**
at `/tmp/hypertrophy-integration-1024/apps/web/.next`, API from the same worktree,
web `127.0.0.1:3020` rewriting only `/api` to `127.0.0.1:8020`, disposable
PostgreSQL `integration_1024` / `m2a_test`, loopback 55418 in verified tmpfs container
`workoutapp-ux-qualification-1022`. The owned temporary servers are stopped after
qualification. Reverify container mounts/ports and SQL database/user/schema before
any restart/import. Isolated server must keep dev cleanup **false**. Credentials
and synthetic account manifests stay private; never use a live account.

Loopback is unreachable from a phone. A separately verified, access-controlled
HTTPS development endpoint must point exclusively at this pair. Record its exact
URL and proxy destination before testing; none is provisioned/claimed here. Never
reuse the public production endpoint. Bind/account/date/session recovery keys are
origin-specific, so use the same test HTTPS origin throughout an interrupted flow.
If the in-memory DB/build is gone, reproduce using the retained helpers and a new
explicit verified disposable target; record new account/build identities rather
than borrowing old acceptance evidence. Do not bypass hardcoded safety guards.

1. Record full commit, build ID, runtime tree IDs, HTTPS origin/proxy, SQL identity,
   iPhone model, iOS/Safari version, keyboard settings/orientation and UTC/local date.
   Create fresh synthetic scheduled Authored and explicitly accepted Customized
   plans. Align selected dates with that account's actual local test date; never
   regenerate a started occurrence or move recorded history to make the test fit.
2. Test unstarted opening and in-progress resume in both modes. Record navigation
   to visible workout and usable first-set controls; distinguish rest-day/no-plan,
   pending reads and genuine failure. This is device qualification, not a rerun of
   the closed broad performance investigation.
3. Select Cross-Body Lat Pull-Around. Verify source prescription, units, known-1RM/
   recent-set/manual options, provisional label and qualified-history precedence.
   Execute source-defined warm-up separately from work. With keyboard visible,
   enter working weight/reps and actual optional effort, save, then record control
   rectangles/scroll/focus, one confirmation, deadline rest timer and next set.
4. Through test-only transport interception at this isolated endpoint, abort one
   save before commit and drop one response after confirmed commit. Reload: absent
   receipt retains exact retry; matching command receipt reconciles without another
   POST. Verify original command/frozen payload and exactly one effective set in
   the disposable database. No production service-worker/network modification.
5. Lose a correction response; try another receipt (must remain blocked), close/
   reopen, lock/background beyond the rest deadline, then reload and reconcile the
   exact original correction. Verify one correction chain and retained original.
   Undo, reload, continue next logical set and review History in kg and lb.
6. Delay reads, edit actuals during refresh, switch synthetic accounts and deliver
   old responses. Check account/token, selected-date, occurrence/revision and source
   variant isolation. No stale guidance/late 401 may replace the current account's
   state. Test interrupted undo/rest-day recovery. Use VoiceOver to verify labels,
   focus visibility and saved/warning/error distinction.
7. Retain sanitized recordings, bounds, timings, request-command counts and test
   outcomes under the exact build. Never export credentials/private training data.
   Report failures honestly; remove the temporary HTTPS endpoint afterward.

## Separate future production safeguards

This procedure authorizes no production access. Main merge and deployment each
require explicit owner authorization. Before cutover an authorized operator must
verify actual images/schema/DB/user, create a private protected backup, restore that
exact snapshot into a verified separate isolated target, review the additive
0025/0026 chain and lock window, coordinate immutable API/web images, test readiness
and retain a forward-safe rollback pair. Never restore an old dump over newer
training records, downgrade, reset, stamp or replay initial-activation toggles.
Synthetic backup/restore here does not replace those safeguards.
