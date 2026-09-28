# Current implementation at the audited revision

Descriptive baseline: `df9965232ce731f8234d222acc526a90bc6be620`, audited 2026-09-28. Reference [AUD-20260928](../evidence/README.md#audit-reference-and-migration-plan). Application source on this review branch remains at that baseline; documentation changes are not runtime implementation. No broad audit or production inspection was repeated. This document never overrides the [product contract](../requirements/product-contract.md).

## Existing system and paths

The Next.js browser calls FastAPI profile/plan/workout/history/auth routers. SQLAlchemy persists profiles, JSON plans, set logs and mutable state; Compose deploys PostgreSQL. Offline importers produce gold artifacts and compiled knowledge. Core `decision_*.py` families cover progression, review, recommendations, frequency, live guidance, execution and generated adaptation. API code still owns important policy. Preserve these seams.

Authored bindings `pure_bodybuilding_phase_1_full_body` and `pure_bodybuilding_phase_2_full_body` remain distinct. `_build_week_plan_runtime_for_user` loads an authored week and redistributes through `_prepare_authored_frequency_adapted_template` / `_build_authored_adapted_sessions`. An unrestricted path sets `__authoritative_authored_passthrough__`; any nonempty restriction removes eligibility and reopens generic scheduler filtering, weak-point bonuses and review overlays. No generated writer overwriting authored files was established.

`full_body_v1` is generated Full Body. Legacy `adaptive_full_body_gold_v0_1` resolves to generated, not authored. Normalization/assessment/blueprint/constructor/adapter are implemented in the API package and invoke compiled doctrine/policy. Generated output inherits Phase 1 scaffolding/timeline and fallback content. Execution uses shared workout infrastructure. Manual/auto program choice is not an explicit programming-consent grant.

## Material deviations

| Area | Source/probe established behavior | Contract consequence |
|---|---|---|
| Authored restrictions | Probe: 88 sets unrestricted; restriction variants 85/86, unmatched restriction 91. | Constraints affect unrelated dose; protection must be mode-based. Substitutions require explicit source-approved consent. |
| Source fidelity | Phase 1 315/315 matched tested fields; Phase 2 310 source/305 retained, AMRAP push-up weeks 6–10 omitted by numeric-only parser. | Import diagnostics do not authorize missing slots; complete source certification pending. |
| Execution shape | Loader sums work sets and reads first numeric rep target; limited adjacent name-based pairing, incomplete typed relationships/warm-up forwarding. | Full set-specific prescription/relationship fidelity absent. Eighty multiset passes do not certify ordering or missing data. |
| Load | `ExerciseState` advances on each submitted work set, uses prior/planned state rather than actual logged weight; normal logger RPE null; fatigue casts; shared live guidance can narrow reps. | Not a completed comparable exposure model; no calibrated progression confidence/monitor. Authored rep authority leaks. |
| Identity/correction | `{program_id}-{index}` repeats across weeks; logs/state lack occurrence FK; duplicate retries and read-modify-write races; undo rebuilds session state but not ExerciseState. | Cross-week progress, reliable retry, undo and longitudinal advice unqualified. Browser caches compound identity problems. |
| Scheduling | Day count, implicit server `date.today()`/Monday and mechanical offsets; authored adapted dates can be consecutive. Today selects next incomplete/resumable work. | Actual chosen dates, IANA timezone, spacing and cross-week allocation not implemented. |
| Generated controls | Six main active controls: days, time band, recovery, weak points, restrictions and mode. Others are partly trace-only; legacy equipment still feeds assessment. | Trace presence is not active-policy proof; empty-input clearing and goal mappings need a contract. |
| Generated ownership | Constructor, adapter, scheduler and router repair/floor/band policies overlap; reporting may require post-route recalculation. | Single ownership needed; no judgment here that a particular band is physiologically optimal. Metadata-v2 scoring remains disabled/no-op; accounting is active. |
| Analytics | Primary-ID grouping, weight/estimated strength calculations and activity-based calendar completion lack complete variant/effort/technique filters. | Partial charts are not reliable comparable PRs, full completion or personal-response proof. |

Source entry points: [plan router](../../apps/api/app/routers/plan.py), [loader](../../apps/api/app/program_loader.py), [models](../../apps/api/app/models.py), [core](../../packages/core-engine/core_engine), and [Today](../../apps/web/app/today/page.tsx). Links identify audited implementation areas, not proof that every line was reviewed in this pass.

## Security and operations

Recovery returns a credential when exposure is enabled or SMTP incomplete; the signing-key placeholder is accepted; old JWTs survive password reset; mail STARTTLS lacks a verified context; generic validation input can escape secret redaction. These are source findings with conditional production exposure, not proof of compromise. The development wipe defaults off. Reviewed personal-data queries derive current user and were user-scoped; no cross-account IDOR was established in inspected paths.

Destructive tests can inherit ordinary database targets. Compose runs Alembic and API startup also calls `create_all`; no isolated production role/grant evidence exists. A plaintext caller-relative dump script exists without complete restore/encryption/retention evidence. Image-input boundary, external TLS/origin/rate controls and live backups remain unknown. See [security architecture](../security/architecture.md) and [urgent plan](../plans/urgent-account-recovery.md).

## Historical verification baseline

| Run | Original result / interpretation |
|---|---|
| Core | 364 passed, 4 failed: changed completion/minimum-set expectations and muscle-list expectations. Individual contract disposition pending. |
| API full | 430 passed, 18 failed, 8 skipped; approximately 18m27s. Retain the full result. |
| API selected recheck | 12 passed: eleven prior failures plus one already passing. Nine flag assumptions and two copied-fixture failures cleared in isolation; one absolute-workbook-path artifact issue remains separately classified. |
| API behavior recheck | Six failed: two Today/progress totals, generated core-slot balance, legacy alias authored-deload assumption, authored review overlay assumption and hack-squat fixture expectation. Reproduction does not establish all six as defects; contract conflicts require replacement checks. |
| Web | 51 passed, 1 failed across 20 files: ambiguous Open Today Workout single-element query. |
| TypeScript | 102 diagnostics (90 TS2304, 12 TS2582) concerning undeclared test globals. Production build success not established. |

CI covers API pytest/web lint; standalone core/web suite/build coverage is incomplete and mini-validate suppresses failure with `|| true`. No production build, real-device/browser, PostgreSQL concurrency/migration or live smoke evidence was obtained. Managed security export remains failed due to its privacy check; no permissions repair or sealed certification. Initial audit snapshot fixture caveats remain in the [evidence registry](../evidence/README.md).

Historical failing cases must be classified individually using [test strategy](../quality/test-strategy.md). No new tests or runtime verification occurred in this documentation batch. Targets and acceptance gates are in the [roadmap](../roadmap/milestones.md).
