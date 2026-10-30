# Flexible training and authored workload evidence — 2026-10-30

Bounded owner-authorized implementation for [#105](https://github.com/Shadowgar/hypertrophyapp/issues/105), under [the registered plan](../plans/flexible-today-workload.md). Baseline main: `a1aa942`; verification here is isolated development evidence, not production deployment or release acceptance. #103/#105 remain open.

## Reproduction and scope of the finding

The owner reported that changing four training dates to three changed Today from five exercises to fourteen. No production account, saved workout history or production configuration was read to reconstruct that particular pair. Its exact original program/source week/date sets remain unverified. The same-program/date comparison below reproduces the underlying allocator defect independently, including a Friday session changing from 9 exercises/27 working sets on four dates to 14/37 on three dates in Phase 1, source week 1.

The API fixture is identical across compared placements except the selected dates and their count: new disposable account; manually selected `pure_bodybuilding_phase_1_full_body` or `pure_bodybuilding_phase_2_full_body`; source week 1; maintenance; five stored available days; equipment `dumbbell, barbell, bench, cable, machine`; saved session-time goal 60 minutes; no performed history; week beginning 2026-10-26; timezone UTC. Every selected date belongs to that same local week. Requests use `/plan/generate-week`, explicit selected dates, target count and expected placement revision 0. The generated plan and its allocation trace supply all per-session counts.

A separate paired replay passes **the same complete runtime source exercises, adapted days, selected dates and neighbor context** to the original allocator from baseline and the changed allocator. All ten paired cases assert exact ordered exercise/prescription equality across both outputs and the original source, unchanged input objects, and identical source digests. Independently generated API users have occurrence-dependent runtime digests, so their raw digests alone must not be treated as source mismatch or parity proof.

## Full per-session audit

Cells list **exercise slots / planned working sets** in selected-date order. Repeated source slots remain distinct. All Phase 1 rows retain 31 slots and 88 sets; all Phase 2 rows retain 31 slots and 67 sets.

| Authored phase | Selected visits, chronological | Before | After |
| --- | --- | --- | --- |
| 1 | Mon, Wed, Fri, Sun | 7/21, 7/21, 8/22, 9/24 | 7/21, 7/21, 8/22, 9/24 |
| 1 | Mon, Wed, Fri | 10/29, 10/30, 11/29 | 10/29, 10/30, 11/29 |
| 1 | Mon, Tue, Fri, Sun | 10/29, 1/3, 9/27, 11/29 | 7/21, 7/21, 8/22, 9/24 |
| 1 | Mon, Tue, Fri | 16/48, 1/3, 14/37 | 10/29, 10/30, 11/29 |
| 1 | Fri, Sat, Sun | 16/48, 1/3, 14/37 | 10/29, 10/30, 11/29 |
| 2 | Mon, Wed, Fri, Sun | 7/16, 8/16, 8/18, 8/17 | 7/16, 8/16, 8/18, 8/17 |
| 2 | Mon, Wed, Fri | 10/22, 10/22, 11/23 | 10/22, 10/22, 11/23 |
| 2 | Mon, Tue, Fri, Sun | 4/8, 3/8, 12/26, 12/25 | 7/16, 8/16, 8/18, 8/17 |
| 2 | Mon, Tue, Fri | 3/6, 5/12, 23/49 | 10/22, 10/22, 11/23 |
| 2 | Fri, Sat, Sun | 22/48, 1/2, 8/17 | 10/22, 10/22, 11/23 |

Three visits still have more work per visit than four. Balancing distributes the complete authored dose and cannot establish that it fits a 60-minute goal. No set pruning, arbitrary exercise/set cap or equivalent-results promise is introduced.

## Decision owner and correction

`packages/core-engine/core_engine/authored_redistribution.py::redistribute_authored_sessions` owns the changed decision. Its inputs are ordered complete source sessions/slots, adapted target days, selected local dates, optional previous/next workout context and the preserved-grouping flag. Its outputs are complete ordered sessions and an allocation trace. The selected-date scheduler/API remain the placement/revision/persistence owners.

The old `selected-date-lexical-v1` objective placed advisory consecutive-date primary-muscle overlap ahead of workload balance. Minimizing that overlap to zero could produce a one-exercise session beside a sixteen-exercise session. This is a deterministic objective-order defect, not evidence that the user needs fewer source sets or that grouped sessions are clinically unsafe.

New policy `selected-date-workload-first-v2` compares, in order: working-set range; squared deviation from deterministic per-day targets; advisory consecutive-date overlap; stable source cuts. The trace exposes the version, ordered objective, actual scores and rule digest. Existing hard relationships, mandatory source rest, source order, nonempty visits and full prescriptions stay mandatory; overlap remains advisory and missing neighbor/muscle evidence stays unknown. In the four-visit adjacent Phase 1 replay, range improves from 26 to 3 sets and squared deviation from 484 to 6, while advisory overlap rises from 0 to 20. That tradeoff is explicit; no recovery, safety or hypertrophy qualification is inferred from it.

The count-only path retains its old range/deviation/source-cut policy and 2–4 bound. Selected-date plans retain the existing 2–5 bound. The correction affects newly allocated or explicitly reviewed replacement placements. Existing activated plans are not automatically rewritten, and `preserve_grouping=True` retains saved groups on date-only amendments.

## Workload presentation and alternatives

`WorkoutWorkload` derives exercise-slot and planned working-set counts directly from the reviewed session. It shows the saved session-time goal when present, says duration is unknown and warns that workload may exceed available time. It does not convert counts into estimated minutes or claim the goal is met. Week shows this information for every active or previewed session before activation. An unread or unavailable profile keeps the time goal unavailable; a verified null goal is shown as absent. The shared component also supports Home/Today previews through the same factual presentation.

For Authored work, the review link leads to Week's existing 2–5 selected visits. Before any workout starts, the user can preview more visits and explicitly confirm a feasible, source-preserving allocation. No link silently executes a redistribution. Started-work freezing, source constraints and existing placement/revision checks still apply. This package adds no splitting of started workouts, cross-week carry-forward or invented continuation policy. Customized retains its separate planning/explicit-consent path and is never described as governed by an authored source.

## Verification and limits

- TDD: synthetic consecutive-date, mixed-gap and known-neighbor regression assertions failed against the original objective. The equal-workload tie fixture also failed, protecting overlap's tie-break role without allowing it to override balance. Compiled Phase 1/source-dose fixtures augmented with existing foundation muscle metadata independently fail against the baseline allocator for both three and four adjacent dates, and pass with the correction.
- Focused core: allocator and selected-date scheduler tests passed, **62 tests**. They include hard source pairs/primers, rest infeasibility, internal source-set links, five-date support, deterministic replay, no source mutation and preserved groups.
- Complete pure core suite: `env -i PATH=/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/core-engine <isolated-venv>/bin/python -m pytest packages/core-engine/tests -q` passed, **885 tests**. This suite requires no application/database environment.
- Web red/green: the real workload component first failed its three presentation assertions; active-Week and unactivated-preview tests failed before integration. Component + Week workload + existing selected-date and preview-feedback tests passed, **45 tests / 4 files**, using `--maxWorkers=1`. A prior concurrent run had one 5-second timeout in the existing “an acknowledged activation stays saved when its refresh fails” test (44 passed); the serial rerun passed all 45 without raising timeouts. Focused ESLint passed for the workload component/tests and Week page.
- Isolated API audit: ten generation cases and ten paired old/new allocator replays passed. The sole warning was the existing FastAPI TestClient/HTTPX deprecation. Targets were an explicitly verified disposable SQLite file under the workload evidence directory, with `configure_test_database` called before application imports/DDL. No production DB/service was contacted.

Local supporting artifacts are under `hypertrophyapp-worktrees/flexible-today-evidence/workload-correction/`: `allocation-after.json`, `same-input-replay.json`, isolated probe scripts and output. They contain synthetic fixtures only. The before matrix comes from the root task's independent baseline probe and is reconfirmed by same-input replay. Core fixtures and checked-in web tests are the reviewable regression evidence.

This workload subsection does not claim browser/device qualification, PostgreSQL transaction serialization, the next-workout API boundaries, final-head CI or physical iPhone acceptance. Those belong to the integrated package's separate recorded checks. Balancing does not calibrate duration, change source dose or resolve started-week/cross-week feasibility.
