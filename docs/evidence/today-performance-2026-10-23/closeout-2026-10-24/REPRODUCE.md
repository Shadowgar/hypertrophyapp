# Reproduce the bounded closeout

Use the [original explicit disposable setup](../REPRODUCE.md), pinned dependencies
and private synthetic account manifest; do not print JWTs or inherit production
DB/Compose defaults. Verify the tmpfs/no-mount container and actual SQL database/
user before application imports. All scripts retain the exact disposable target
allowlist. A fresh replay needs a deliberately verified new target and its own
before-checkpoints/fixtures; do not overwrite the original evidence or blindly
seed the Friday fixtures on a different day.

1. Verify #112 `f79a438`, application `912e7e9`, base `c656988`, original build IDs
   and runtime hashes against [original metadata](../environment.json). Existing
   original builds remain unchanged. No server may own loopback 3020/8020.
2. Create a detached scratch worktree from `f79a438`, restore **only**
   `apps/web/app/today/page.tsx` from `c656988`, and build its web app with the same
   pinned node_modules, webpack production mode, `SERVER_API_BASE_URL` pointing
   to loopback 8020 and `NEXT_PUBLIC_API_BASE_URL=/api`. Run from `apps/web`.
   This control is never merged or used for training writes.
3. Copy [reproduce files](reproduce/) into ignored `.qualification/closeout/`.
   Reuse the guarded private `run-python pg` wrapper from the original setup (or
   its credential-free example). Run `refresh.py` through it to mint four private
   synthetic tokens from the verified test users without changing database rows.
   Run `snapshot.py before` through the wrapper; it now uses an argument, because
   the wrapper intentionally clears unlisted environment variables. The recorded
   initial before-output failed to save; its comparisons use retained original
   table/private-account checkpoints instead, explicitly noted in measurements.
4. `python3 .qualification/closeout/run.py` executes the fixed four-repetition,
   three-variant/four-case comparison. Ports occupied by another process are fatal.
   It verifies owned listeners/builds/API markers and stops only owned processes.
   Do not run builds or test suites concurrently. Routing/browser calendar is
   fixed to October 23; JWT time stays real. Each cold page is followed by one
   warm-context page. Manual weight/repetitions are filled but Save is not clicked.
5. Run `snapshot.py after` through the guarded wrapper. `analyze.py` checks all
   96 complete payloads privately, compares retained checkpoints and emits the
   concise [measurements](measurements.json). For a new replay, point comparison
   inputs to that replay's own before-checkpoints, not the original hashes. Raw
   traces, payloads, auth/account fingerprints and tokens stay private/ignored.

Browser metrics include resource timing, long tasks, CDP script/task/layout
work and the first Today effect as an initialization proxy. They are not direct
React hydration profiling. The recorded 96 runs had no latency exclusions. No
screenshots are required for this timing-only closeout. The shared host remains
uncontrolled outside this study; samples do not prove a particular source effect
or its absence. See [findings and limitations](CLOSEOUT.md).

Fresh focused backend command, after the measurement window and separate
`m2a_qualification` identity/schema verification:

```text
python -m pytest apps/api/tests/test_authored_history_snapshot.py \
  apps/api/tests/test_authored_initial_calibration.py \
  apps/api/tests/test_authored_load_intelligence.py \
  apps/api/tests/test_authored_warmup_guidance.py -q
```

Use the guarded qualification interpreter/environment, never an inherited URL.
The recorded result is 172 passed, no skips/failures. Final web/API CI is reported
for the exact published documentation head in PR #112's closeout comment.
