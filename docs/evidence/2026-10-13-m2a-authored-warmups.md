# M2A-2 authored warm-up candidate qualification

Scope: [bounded plan](../plans/m2a-authored-warmup-guidance.md), LOAD-008 Authored slice. Base `0a5151988a3e4e639c336db2388b46c871c0450f`; branch `m2a/authored-warmup-guidance`. Owner requested implementation and a review PR, not merge or deployment. This record does not accept all M2A.

## Runtime authority and limits

`core_engine.authored_warmups.build_authored_warmup_guidance` is the sole Authored warm-up calculation owner. It recognizes the existing compiled Phase 1/2 exercise-specific source protocol by a digest covering both introductory instructions and recipe rows: one set at approximately 60%; two at 50/70%; three at 45/65/85%, preserving the corresponding source rep ranges. Raw source count/text remains visible. The compiled source files and authored prescriptions are unchanged.

The owner requires a qualified M2A-1 next-exposure working load, supported load basis and an explicit declared equipment increment. It reuses M2A-1 canonical kg and grid rounding anchored on the qualified working load. A declared increment is not proof of available plates, machine minimum/maximum or a complete inventory. Unknown load/context, unsupported source ladder, bodyweight/AMRAP/assistance, hard load instructions and performed substitutions abstain from numeric load suggestions. Confirmed substitutions still require separately qualified warm-up semantics; no original-exercise load is inherited.

Absent/zero source entries, including `0.0`, yield no invented warm-ups. Text/range counts preserve text with manual actual entry. A known count outside the recognized ladder retains that count without invented reps or loads. Manual entries and qualified suggestions remain editable. The previous core `compute_warmups` and browser `warmupsFromWorkingWeightLb` formulas remain in Generated/estimate flows and do not feed Authored.

API advice identities bind user, occurrence, source protocol and working evidence. Captured warm-up advice is separate from working recommendations. Unknown planned warm-up load/delta is null; actual canonical load and optional observed RPE remain distinct. Warm-up receipts use independent ordinals without a parent or technique. They do not complete required work sets or add completed exercise exposures. Correction/undo retains original advice provenance; exact retries return the immutable acknowledgment before new source validation.

## Qualification environment

All implementation and tests used `/tmp/hypertrophy-m2a-warmup`. The isolated PostgreSQL 16 container used a loopback-only port, a tmpfs data directory and no host persistence mounts. Database/user identity was checked before application imports. Existing migrations through `0022_authored_load_states` were applied only to this disposable database; this package adds no migration. SQLite tests used explicit disposable files and per-worker isolation under a private qualification directory. No production services, configuration or workout data were changed.

Browser accounts, prescriptions and historical receipts are explicitly synthetic fixtures, not claims of importer/generator fidelity. Unit/source tests separately verify both compiled source protocols. Private test artifacts remain outside Git; this record contains no account tokens or production records.

## Measured results

Local qualification checkpoint for implementation `cc5c36e7fb82b2c4107fcaeb4b35b251326d5f6d`. The broader local and exact-head GitHub results at `b3c42bf` finished with the same baseline failures: core 594 passed / 4 failed, API 750 passed / 8 failed / 25 skipped, web 160 passed / 1 failed. Final review-fix CI results are recorded in PR #81.

- Core focused: 95 passed. Independent review caught missing-raw-count fallback and Decimal precision failure; both have red/green regressions and were approved on re-review.
- Core broader: 594 passed, 4 failures matching the existing baseline exactly.
- API focused SQLite: 54 passed, 9 PostgreSQL-only skips. PostgreSQL warm-up file: 22 passed; 41 existing M2A PostgreSQL cases passed. Persistence, same-command retries, concurrent ordinal collision, work/warm-up ordinal overlap, correction/undo and cache reconstruction were exercised.
- Broader API: subsequently completed locally and on GitHub with 750 passed, the same 8 baseline failures and 25 skips. An initial attempt was stopped after setup errors: the private runner omitted `HIST_TEST_ROOT`. It was corrected to the same explicit disposable root required by CI before the valid broader run. No repository or application change was made for this environment error.
- Web focused: 19 warm-up cases and 33 existing load-intelligence cases passed. The single broader run produced 154 passes and four failures: the known history-calendar failure, two timeouts and a following authored-prescription assertion failure. Targeted reruns of the two existing failing files produced 14 passes and only the known history-calendar failure; the new warm-up file passed after final fixes. This supports a timing/cascade explanation for the other initial failures, not a claim that the original broad run was green.
- Production web build and TypeScript passed. Full web lint passed with one existing Today effect-dependency warning. Documentation check: 28 retained active-link failures, zero new failures. Whitespace check passed.
- Independent core, API and web task reviews, followed by a whole-branch integration review, found no unresolved actionable correctness/security blocker in this implementation revision. These source reviews are separate from managed scan completion and CI.

## Playwright on the isolated production build

Desktop at 1440×900 and mobile at 390×844 used authenticated synthetic accounts and the real isolated API/PostgreSQL. No mocked browser responses or production records were used. Neither viewport had horizontal overflow; the inspected mobile logging button was 48 px high. No captured JavaScript page errors or console errors occurred in the final flows.

- Desktop: unknown context initially left warm-up loads blank. Declaring total external load, a synthetic equipment identity and a 0.5 kg increment returned source-preserving suggestions of 20.5 and 28.5 kg. Logging 20.5 kg retained the suggestion and actual value separately, kept required working completion at zero and retained the one prior completed exposure. Correction to 19.123 kg and undo both succeeded; the effective warm-up receipt disappeared and working completion stayed zero.
- Mobile: the textual source instruction remained visible with blank actual reps/load. Logging 7 reps at 12.345 kg with unknown actual RPE created a warm-up receipt with null planned load, zero completed work sets and zero completed exposures for that exercise. Logging the first working set then advanced working completion to one, with warm-up/work receipts still distinct. Reload retained the warm-up as 7 reps at the rounded 27.2 lb display while canonical persistence remained 12.345 kg. Numeric-zero `0.0` stayed visible and exposed no warm-up logger.

Screenshots and private synthetic receipts are retained only in the local qualification directory. Unit tests additionally exercise untouched/restored rounded lb canonical round-trip, pending/remounted retries, stale advice, context changes and substitutions; browser testing does not claim exhaustive device or concurrency coverage.

## GitHub review follow-up

The initial Codex claim that warm-up-only history suppresses the next qualified working recommendation did not reproduce in four isolated API cases. Historical warm-up-only groups retain unknown comparison context and cannot join a qualified working cohort; partial and voided actual working roots still affect that cohort. The evidence is recorded on PR #81.

Two subsequent findings were confirmed and fixed. Current Today/progress/summary reads now restore a declared context from effective independent warm-up receipts, preserving unit, basis, increment and qualified suggestions across reload. Historical grouping remains working-only. Working command capture disables this restoration, so an older client omitting a working declaration does not silently inherit warm-up context. Any retained working root, including voided or unknown-context work, keeps working-context authority. Voided warm-ups and technique children do not restore settings.

The warm-up logger now rejects zero external load before submission. It uses the existing authored/performed bodyweight classification for the zero-load exception; changing the declared load basis alone cannot permit zero.

Eight new API regressions passed on disposable SQLite, and the full warm-up API file passed all 30 cases on isolated PostgreSQL. The original four history-isolation probes also passed after the fix. Web warm-up tests passed all 24 cases, including declared-basis and confirmed-substitution negatives. Production build, TypeScript, scoped lint and an independent fix review passed; lint retains the existing Today warning.

Post-fix Playwright repeated real API logging and reload at 1440×900 and 390×844. Zero external load disabled submission in both viewports. After logging a 20.5 kg warm-up and reloading, both retained total-external basis, 0.5 kg increment and the remaining 28.5 kg source-qualified suggestion, with working completion still zero. Neither flow captured page/console errors or horizontal overflow. Synthetic accounts and disposable PostgreSQL only.

A further Codex pass identified two training-flow edges. A reported conflict after warm-ups still pauses execution; the existing started-receipt substitution guard remains intact. Today now explains the warm-up-only prerequisite and exposes the existing audited undo action directly before alternative confirmation/decline, without automatically changing receipts or consent. Server conflicts carry the same explanation. Tests preserve the existing safety pause for started confirmed working variants.

Effective receipt projections now expose their exact persisted command ID. The warm-up UI retires a saved pending command only when the observed effective receipt matches its occurrence-scoped key, exercise, ordinal, kind and command ID. Missing or mismatched receipt identity leaves the immutable retry intact. The lost-commit-response/reload/undo/new-attempt regression proves the next attempt receives a fresh command ID.

At this follow-up checkpoint, the warm-up PostgreSQL file passed 34 cases; targeted API tests also retained the existing started-work pain pause. The warm-up UI file passed 27 cases, constraint UI passed 6, and TypeScript/scoped lint passed. Independent follow-up source review found no blocker. The preceding exact-head CI at `8373eed` had 594 core passes / 4 baseline failures, 758 API passes / 8 baseline failures / 25 skips and 165 web passes / 1 baseline failure. Final browser checks and CI for the follow-up commit are recorded in PR #81; they are not presumed passed here.

Final browser follow-up found that the real substitution acknowledgment omitted the refreshed projection expected by the UI test fixture. The API now includes fresh load intelligence on the projected response copy before saving the immutable acknowledgment; the frozen occurrence remains prescription-only. Report and confirm retries return that exact original response. A confirmed variant immediately displays source instructions and manual warm-up rows without inherited numeric load. The API regression and full 28-case warm-up UI file passed. The warm-up PostgreSQL suite remained 34 passed.

Desktop Playwright against the real isolated API deliberately dropped a successful log response, then verified reload/observed acknowledgment, audited undo, and a fresh command recording 7 reps at 21.5 kg. Mobile Playwright reported pain after a source warm-up, used the 48 px explicit undo action, confirmed the permitted synthetic alternative, and immediately logged a manual 15 kg variant warm-up with null planned load. Working completion stayed zero; mobile had no console/page errors or overflow. The desktop's injected network failure was intentional; no page exception occurred.

Codex also identified that qualification initially omitted the exercise-specific introduction. Six red/green tests across both phases now require abstention for changed, missing or nontext introductory instructions while retaining visible source text. The complete unchanged intro/recipe digest was independently recomputed for both compiled artifacts. All 101 core warm-up cases passed; no source artifact or percentage/rep prescription changed. Independent review approved these bounded response/protocol fixes. Final-head CI/review results remain recorded in PR #81.

## Managed security qualification limitation

The Codex Security diff workflow passed capability preflight and started scan `9540ab78-44e1-4a93-b7ca-59e77d14658d` for the implementation range through `3227f9b`. Its first semantic checkpoint was rejected because the managed scan-output parent was group/world writable without a sticky bit. Global storage permissions were not changed, and no sealed scan or findings report is claimed. The later render-state lint fix `cc5c36e` was covered by the independent final source review. GitHub CodeQL/GitGuardian and the Codex PR review remain separately reported checks, not substitutes mislabeled as this managed scan.

## Baseline and acceptance boundary

The retained core failures concern two legacy Today set-count/state assumptions and two scheduler tracked-muscle contract expectations. The retained API baseline comprises the two Generated adaptive-plan cases, two Authored progress/Today total cases, one Generated substitution-guidance case, one weekly-review adjustment case and two missing licensed Phase 1 companion-workbook cases. The retained web baseline is the history-calendar test finding duplicate Open Today links. These remain failures, not synthetic passes or scope expansion.

Full plate inventory, multiple gyms, personal-response modeling, M2B recurrence/carryover, M3 dashboards and issue #80 history-query optimization are outside this package. Source fidelity tests and software qualification do not establish training outcomes. Owner PR review remains required; no auto-merge or deployment is authorized.
