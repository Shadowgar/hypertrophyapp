# Flexible Today and Authored workload correction

Status: Owner-authorized bounded implementation, 2026-10-30, related to Issue #105.
No merge, production operation, migration, reset or release-control change.

## Design and authority

Reuse existing selected-date placement and account lock rather than introduce a
second scheduler. A read-only next-unstarted-session preview shows original date,
program/source identity, exercise slots and working sets on Home and Today.
An explicit confirmation sends the reviewed plan/occurrence/date/revision/digest;
the server reselects and revalidates under the history User lock. Only a same-week
Authored date-only amendment admitted by the existing unstarted-week policy may
move. Started/consent snapshots, collisions, stale previews, cross-week work,
source minimum-rest conflicts and Customized consent remain blocking. No read
creates execution snapshots, completion or history. Keep original date is read-only.
Existing recovery guards must hide this mutation whenever recovery is pending.

The current selected-date allocator prioritizes advisory consecutive-day muscle
overlap before workload balance, allowing very small edge sessions and very large
other sessions. Correct that objective to balance working sets before minimizing
advisory overlap; hard source relationships/rest and complete source-order dose
remain mandatory. Existing activated plans are never automatically rewritten.
Counts are workload information, not calibrated minutes. Show the user's saved
session-time goal without claiming it is met, and offer review of more selected
visits before any work starts. Splitting started workouts or carrying source work
across weeks needs a separate occurrence/carry-forward contract and is excluded.

Alternatives rejected: silently loading a future workout through Today (changes
execution-date semantics); bypassing the whole-week freeze (breaks consent/history);
pruning prescriptions or adding a duration-based set cap (unapproved dose change).

## Implementation and verification plan

- [x] Reproduce empty Today and compare all three/four-day session counts using
  identical isolated profiles, source week and equipment; retain before/after evidence.
- [x] Add failing core/API tests for balanced allocation, read-only preview,
  confirmation, stable occurrence/source dose and stale/started/foreign-account/
  duplicate-date/cross-week/Customized boundaries; implement through existing owners.
- [x] Add one reusable preview/confirmation card and workload warnings to
  Home/Today/Week with account-generation and recovery guards; focused web tests.
- [ ] Qualify real isolated API/browser behavior at mobile/desktop; PostgreSQL
  write serialization tests for move-versus-start/move. No production accounts.
- [ ] Publish one PR, link #105 without closing #103/#105, require normal final-head
  CI/CodeQL/security checks, document limitations and physical-iPhone retest steps.
