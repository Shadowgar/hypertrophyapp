# M0 check qualification

This package scopes GitHub checks to the complete changed-file diff and propagates applicable failures. It changes no training, auth or application behavior. PR #35 remains a separate documentation baseline; publishing this package does not merge either PR or qualify a release.

| Changed scope | Applicable checks |
|---|---|
| Markdown / documentation JSON or YAML | Offline local links and anchors, changed JSON/YAML syntax, context-manifest paths, release-evidence schema boundaries; tooling tests and actionlint. |
| API | API tests with explicit disposable SQLite/log targets. Settings defaults run directly in Python, outside pytest/conftest, with the dev flag absent and dotenv disabled; the remaining suite runs with synthetic dev routes explicitly enabled. |
| Core engine | Core tests plus API tests for consumers. |
| Programs, compiled knowledge, importers, reference inputs, runtime `docs/rules`, generated guide/catalog assets | Core and API qualification; these are not classified as narrative documentation. |
| Web | Lockfile install, lint, unit/component tests, TypeScript and production build, reported separately. |
| Workflow / CI tooling | Selection/gate/checker tests, actionlint and documentation checks. |
| API/web Dockerfiles, Compose, `.dockerignore` | Compose validation and real builds of all buildable services, preserving applicable runtime checks. Documentation and ordinary API Python changes do not select container builds. |
| Unknown shared configuration | Conservative API, core, web and container coverage. |

Container builds use the root contexts and API/web Dockerfiles defined in `docker-compose.yml`, with automatic dotenv loading disabled. They build images without starting services, running migrations or connecting to application persistence. Build failures, cancellations and unexpected skips fail qualification when container coverage applies.

[CI](../../.github/workflows/ci.yml) always produces `CI qualification`, which fails if any applicable job fails, is cancelled or is skipped. Nonapplicable checks are visibly skipped, not described as validation passes. Full manual dispatch selects all categories. Push CI runs on main; PR CI runs on pull requests, avoiding duplicate branch-push suites. No branch protection or repository integration settings are changed here. Owners may separately choose the aggregate as a required check.

## Documentation scope and limitations

[Documentation checker](check_docs.py) reads Git snapshots, never imports the application or contacts external links. It checks active Markdown references across the snapshot so deleted targets and renamed headings can break referring documents. Existing link failures are compared by source/target/reason and reported as baseline exceptions; they do not become a full-documentation pass. A newly introduced failure still fails. A full manual check has no baseline exemption.

Historical notices explicitly beginning with Historical, Supporting, Generated or Tool-consumed keep their original dated bodies outside current qualification; their successor/navigation notices are checked. The headings in a historical target still resolve references into that historical document. This follows PR #35's original-body retention boundary, not an assertion that old historical links work.

Changed structured documentation must parse; active context-manifest paths must exist. When the release scorecard is present, schema probes require pending records to remain representable, forbid empty evidence on accepted records and permit an evidenced acceptance. They do not fetch/hash evidence artifacts or establish their truth. The P2 schema finding in PR #35 is deliberately detected, not silently fixed in this tooling PR.

## Removed and unqualified checks

The automatic Mini Validate workflow is removed: PR #35's wrapper returned success after two API runs each reported 9 failures, and the script exited before web tests/build. Its duplicated Compose startup and failure suppression are replaced by explicit CI jobs. The historical local `scripts/mini_validate.sh` is unchanged and is not a safe production procedure or current release authority.

[SonarQube](../../.github/workflows/sonarqube.yml) remains available through manual dispatch, with automatic checks suspended until its access is qualified. PR #35 reached Sonar Cloud but JRE metadata provisioning returned HTTP 403 before analysis. This package changes no credentials or secrets and makes no Sonar analysis-pass claim. CodeQL default setup and GitGuardian remain under their existing repository integrations; the manual advanced CodeQL workflow is not enabled alongside default setup.

CodeRabbit's green skipped status and Copilot's exhausted quota are review-not-performed outcomes. Bot comments/inline findings remain review evidence; these scripts cannot turn them into an approval. No reviewer request, integration setting or branch protection is altered.

## Baseline disposition and safety

PR #35 API CI reported 450 passed, 9 failed, 7 skipped. Six behavioral failures reproduce the September 28 audit: two Today/progress totals, generated core-slot balance, generated alias/deload behavior, weekly-review overlay and substitution-guidance selection. Reconcile those against the approved product contract in separately scoped work; never reintroduce authored mutation to satisfy obsolete assertions.

Two failures require a licensed Phase 1 workbook absent from Git and nonportable embedded paths. Fixture provision/licensing and provenance portability remain later M0 work. The workflow does not publish proprietary files, skip those tests or label missing fixtures successful. The default-settings assertion runs in a standalone Python process, outside pytest/conftest setup, with the dev flag absent and `Settings(_env_file=None)`. Its mandatory assertion preserves the false runtime default; the remaining suite explicitly enables synthetic dev routes.

Core/web/type failures established by the audit remain failures when their category applies. SQLite does not qualify PostgreSQL concurrency, migrations, live configuration, deployed security, browser/device behavior or scientific outcomes.

All API CI persistence and logs use newly created runner-temporary targets. No Compose service or migration command is invoked. Local verification for this package is limited to its pure checker tests, static workflow lint and Git snapshot probes in disposable worktrees; application suites are not run from the production checkout. Production DB/configuration/services/deployment and existing logs remain outside this authorization.

## PR #35 failure identities

[PR API run](https://github.com/Shadowgar/hypertrophyapp/actions/runs/36389369258/job/108821561185) and both [Mini Validate attempts](https://github.com/Shadowgar/hypertrophyapp/actions/runs/36389369540/job/108821561970) reported these same nine failures at `bd19cb2ba271876344f942404a30f05e7efac58b`. The first six match the audit's persistent recheck at `df9965232ce731f8234d222acc526a90bc6be620`:

```text
tests/test_authored_generated_path_regression.py::test_today_total_sets_matches_progress_planned_total[pure_bodybuilding_phase_1_full_body-30]
tests/test_authored_generated_path_regression.py::test_today_total_sets_matches_progress_planned_total[pure_bodybuilding_phase_2_full_body-23]
tests/test_program_catalog_and_selection.py::test_adaptive_gold_generate_week_includes_core_slot_when_equipment_available
tests/test_program_catalog_and_selection.py::test_adaptive_gold_generate_week_uses_authored_deload_week_six
tests/test_weekly_review.py::test_generate_week_uses_saved_weekly_review_adjustments
tests/test_workout_session_state.py::test_adaptive_gold_fourth_exercise_today_and_log_set_preserve_substitution_guidance
```

Existing CI fixture/environment failures, not new application regressions:

```text
tests/test_config_defaults.py::test_allow_dev_wipe_endpoints_default_false
tests/test_phase1_full_body_source_fidelity.py::test_phase1_full_body_source_paths_point_to_real_companion_workbook
tests/test_phase1_full_body_source_fidelity.py::test_phase1_full_body_onboarding_matches_companion_workbook_table_exactly
```

The audited main CI [already failed](https://github.com/Shadowgar/hypertrophyapp/actions/runs/26394662070); its old detailed logs have expired. Exact six-case attribution comes from the September 28 audit, while the three CI-specific causes are supported by unchanged tests/test harness/configuration, absent tracked workbook and current job logs. The audit had the licensed workbook and an isolated environment, so its failure count is not interchangeable with GitHub's.

[Sonar failure](https://github.com/Shadowgar/hypertrophyapp/actions/runs/36389369425/job/108821561764) is external/configuration failure before analysis. [Codex P2 finding](https://github.com/Shadowgar/hypertrophyapp/pull/35#discussion_r4119430524) is an actionable new documentation-schema gap: accepted records permit empty evidence. It remains for a separately authorized correction to PR #35. CodeQL and GitGuardian completed successfully; CodeRabbit and Copilot performed no substantive review. No transient/flaky failure is established by these runs.
