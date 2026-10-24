# Personal WorkoutApp integration rehearsal — 2026-10-24

**Recommendation: BLOCKED for main integration under the existing release gate.**
Two unchanged source-fidelity tests require the missing licensed Phase 1 companion
workbook. Provider security findings remain open. The canonical security qualification is
incomplete and physical iPhone
Safari acceptance is pending. Failed CI is not accepted or waived. No production
service/database/private record was contacted; no main merge or deployment occurred.

This is the owner's bounded integration-and-qualification request, after PR #112
closeout. It does not repeat the performance investigation, reopen design/science,
implement Home/onboarding or introduce another roadmap. WorkoutApp remains one
first-party application; Apple is the only future external fitness-data platform.

## Candidate and ancestry

Branch `integration/personal-workoutapp-2026-10-24`, worktree
`/tmp/hypertrophy-integration-1024`, starts at freshly verified remote main
`fc3bd0c7b93c9d3232e6aec758e16efcca6ac583`. The production checkout remained
unchanged at `1327ddd9b52497327965c365c03bdbb07992ae60`; its state was not used
as a proxy for remote main or the deployed application.

| Order | Pinned input, verified on GitHub before changes | Local merge |
| --- | --- | --- |
| 1 | #109 `4ac9c49b8c9f274dd70784f4ec9027e65592f657` | `2064461` |
| 2 | #110 `b3844398b50a64311f99ccf74411801bbd88225c` | `b62e103` |
| 3 | #111 `c656988c2133e5a655c83a9ba87c5f6c47c9308e` | `687722a` |
| 4 | #112 `ab2b7e9fd7d58a67af89ef379176aa05b4427429` | `d802e4e` |

All original commits remain ancestors once; no cherry-pick duplicates. The
[manifest](manifest.json) lists complete original ancestry and application tree IDs.
Test-only correction commit: `188a45d68eb06b66b655ffeac251cb2453cd02a5`.
The final evidence commit is identified by this directory's GitHub revision and
head-linked PR qualification comment, avoiding a self-referential commit hash.
Runtime trees are unchanged from #112 (application source `912e7e9`); the new
repairs are tests/documentation only. This is fresh qualification of the combined
checkout, not reuse of #112 results.

[PR #108 at `33598c3`](https://github.com/Shadowgar/hypertrophyapp/tree/33598c3fb35328cc2d2b6310865f716380b6c81e/docs/ux/astra-2026-10-20/unified-2026-10-21)
remains the approved design reference. Its static collection is not merged here.
Original PR branches are unchanged. Do not subsequently replay all overlapping
stack commits over this candidate.

## Documentation and schema reconciliation

The plan registry, traceability and single M0–M6 roadmap retain all original
80 catalog IDs and all PERS-001–020 requirements. The roadmap conflict retained
both the personal crosswalk and Today slice. The dated handoff now has an explicit
subsequent-authorization notice: its original planning-only/pending-visual wording
cannot override the later design, implementation and numerical-amendment approvals.
Original requirements, crosswalk and decision history remain intact; no ADR or
whole milestone is silently accepted. Historical implementation evidence remains
revision-scoped. [Plan/checklist](PLAN.md).

Only new schema files relative to main are `0025_interface_preferences` and
`0026_initial_calibration`: `0024_merge_authored_customized → 0025 → 0026` is a
single additive chain. No runtime rules, program/source assets, production config
or deployment workflow changed. Both migrations create separate owned tables,
with no account/history rewrite, cascade or backfill. Their forward-only provenance
protection is unchanged.

Fresh PostgreSQL rehearsal used `workoutapp-ux-qualification-1022`, PostgreSQL 16,
no mounts, tmpfs data, loopback `127.0.0.1:55418`, role `m2a_test`.
New database `integration_1024` was verified empty before imports/DDL. A synthetic
existing account/history record was seeded at real Alembic `0024`, retained through
`0025`; a preference was added at `0025`, retained through `0026`. All preexisting
table digests matched across both upgrades; new preferences/calibrations were empty.
After browser use, the original three seeded account/preference/history rows still
matched their earlier digests. The exact synthetic dump was restored without
`--clean` into independently verified empty `integration_1024_restore`:
**23 table digests / 63 rows matched exactly**, including consent, plans, receipt
amendments and calibration. [Preservation proof](preservation.json).
Dump/credentials/raw records stay in ignored private qualification storage.
This is synthetic restore evidence, not a production backup or production RPO/RTO.

## Fresh combined-checkout qualification

| Check | Observed result / scope |
| --- | --- |
| Full core | **873 passed**, 28.80 s. Four inherited failures repaired, no new failure. |
| Full web | **313 passed / 49 files**, 264.57 s. Covers late replies, account/token/epoch changes, edits during refresh, stale dates/occurrences, frozen saves/corrections/undo, themes and History units. |
| Production frontend build | Pass, isolated build `ZLEpb6JBscpHyieWEipdp`; API rewrite to loopback 8020. |
| TypeScript | Pass (`tsc --noEmit --incremental false`). |
| Lint | 0 errors, 7 retained hook-dependency warnings; no clean-warning claim. |
| Focused PostgreSQL | **172 passed**, 112.18 s; Authored history snapshot, initial calibration, load intelligence and source warm-ups, including concurrency and retry/isolation boundaries. |
| Fresh API CI | First combined head `4e0fef6`: **958 passed, 2 failed, 120 skipped**, 510.53 s, run `40067157844`. Only the unchanged workbook checks failed; all corrected weekly cases passed. Final helper-correction head is reported separately in the head-linked PR comment; no all-API-pass claim. |
| Independent review | No actionable finding in bounded test repairs/ancestry; reviewer reran 216 affected pure core cases successfully. Final release limits remain explicit. |

The focused PG suite's unchanged safety guard requires the preexisting disposable
`m2a_qualification` database. Container/DB/user/schema were reverified before
imports; it uses additive unique synthetic fixtures. An initial attempt against the
new integration DB correctly stopped at guard assertions before app imports.
An overbroad PG selection was stopped after 166 additive passes, before legacy
profile reset helpers; only the four additive files were rerun to completion.
Profile/preferences preservation was instead checked through actual browser/API use
on `integration_1024` and by the existing isolated CI workflow.

Local full API setup lacked xdist; that collection attempt executed no tests. A
serial full attempt was stopped (**35 passed, 2 skipped**, incomplete) after
inspection identified inherited `drop_all` helpers, contrary to the local safety
lock. Earlier narrow count/weekly reproduction runs had already executed those
helpers only on newly created explicit disposable SQLite files. This is a local
procedure deviation, not a full-suite pass or permission to repeat them. No PG or
production reset was executed. Full API qualification uses the unchanged repository
CI workflow's ephemeral target; assertions/skips/test selection are not weakened.
The corrected weekly persistence comparison passed in full combined CI at
`4e0fef6`; its interrupted local retry did not qualify it. The final head-linked
PR comment records the subsequent helper-correction head's completed CI result. [Nine-case disposition](INHERITED-CI.md).

### Actual browser behavior, not screenshot-only evidence

The isolated production build/API pair used new synthetic accounts and the real
PostgreSQL backend. Dev cleanup remained disabled in that server. Requests were
committed using real `route.fetch()` then their responses deliberately discarded;
fail-before-commit cases abort before reaching the server. No fabricated API replies.

- Authored Cross-Body Lat Pull-Around: known 100 lb benchmark → qualified provisional
  65 lb estimate → source-guided 37.5 lb warm-up → optional actual RPE → save → one
  receipt/rest/next-set entry. Mobile 390×844 and desktop 1440×900 composer bounds
  and scroll match exactly before/after save, including uncertain desktop save.
- Lost benchmark/set/correction responses retain exact original command/payload.
  Another receipt stays locked; closing/reloading then retrying applies one
  correction. Undo/reload returns to one effective corrected receipt; original,
  superseded and voided rows remain. History opens on the saved workout.
- Qualified 40 kg prior exposure supersedes the reported 100 lb benchmark and
  renders 88.2 lb; unsupported targets abstain and permit manual entry.
- Real consented Customized proposal/challenge/accept/activate → fail-before-commit
  save → reload/exact retry → committed-but-lost second save → receipt-bound
  reconciliation without another POST → correction/lost reply/close/reload/exact
  retry → undo/reload. Accepted dose/consent/source identity stay intact.
- Existing-account onboarding sign-in emits only authentication write and preserves
  profile. Equipment PATCH changes only its two intended fields. Six appearance
  saves, kg/lb switching, Follow Device Settings and independent desktop persistence
  preserve unrelated profile settings. Existing missing-preference user starts
  Classic Dark/lb revision zero. The harness waits for the loaded profile before
  editing Settings; its initial premature-edit attempt is retained privately as a
  failed readiness attempt, not passing evidence for edits during initial loading.

[Fresh journey assertions and representative captures](JOURNEYS.md) retain console
exceptions accurately: injected transport failures are expected; inherited favicon
and `/programs` prefetch 404s are classified separately. No broad console-clean claim.
Earlier galleries/performance samples retain their original revisions; they are not
relabeled as this candidate. The original two-minute production symptom remains
**not reproduced**; the closed performance uncertainty/targets remain unchanged in
[#112 closeout](../today-performance-2026-10-23/closeout-2026-10-24/CLOSEOUT.md).

## Security, review and readiness

[Security/provider disposition](SECURITY.md) preserves PR #111's two empty-input
SHA-256 occurrences and the incomplete canonical scan. GitGuardian dashboard/API
incident disposition requires authenticated provider access not available here;
no broad ignore, synthetic success status, credential search or history rewrite.
[Review findings](REVIEWS.md) distinguish existing thread resolution from fresh
combined regression evidence and from actual security/release approval.

**Smallest next actions:** provide the lawful original licensed Phase 1 fixture in
an approved private CI channel and rerun the unchanged tests; complete the supported
canonical security setup and incident-specific provider review; execute the
[synthetic physical-iPhone procedure](IPHONE.md). No new training-policy decision
was required for the seven obsolete assertions. No inherited failure is a waiver.
Main integration remains owner-controlled and blocked by the failing applicable
source-fixture gate; security/device qualifications remain additional open release
gates. The PR check/comment records the exact final aggregate result.

Before any future deployment, obtain separate authorization for production target
verification, a protected private backup and restore of that exact snapshot into a
separately verified isolated target, actual-schema migration review, coordinated
immutable API/web images, health checks and forward-safe rollback. Do not replay
old initial-activation toggles: activation is already complete. Never downgrade,
stamp away or reset training history. This rehearsal grants no production access.

After readiness and owner integration review, the next development stream remains
the approved guided Home/onboarding and program/equipment selection, then remaining
layouts. It is deferred here, not a new prerequisite or roadmap. **Stop.**
