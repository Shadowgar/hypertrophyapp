# Test and qualification strategy

Status: **Proposed policy under production-safety requirements**. This documentation batch runs only static Markdown/link/scope checks. No application test, build, installation, migration or service startup. [Evidence policy](../evidence/README.md) owns manifests/results; [traceability](../requirements/traceability.md) links existing partial protections and missing qualification.

## Isolation before execution

Future authorized tests run in a disposable checkout/container and persistence target with an explicit identity contract. Use synthetic users/history, temporary logs/artifacts, cleared inherited settings and fake mail/network denied by default. Set both test and ordinary database URLs explicitly; guard target identity/path before connection or DDL. A fresh container, a database-name suffix or inherited Compose environment alone is insufficient. Test destructive helper rejection of production-like/inherited targets without contacting those targets.

Never run drop/create/truncate/reset fixtures, migrations or service-startup helpers against production. Do not read/copy private logs, live environment files, credentials or personal records to construct fixtures. Approved isolated PostgreSQL requires its own unmistakable target, credentials/access boundaries and reset lifecycle. This policy is not authorization to provision or run it.

SQLite qualifies supported sequential software cases only. PostgreSQL independently qualifies row locking, uniqueness races, transactions, migration/backfill/grants and recovery. A SQLite pass or create_all does not prove a PostgreSQL schema upgrade or multi-worker reset/logging behavior.

## Categories and acceptance

| Category | What it establishes / required limits |
|---|---|
| Deterministic unit | Decision families, explicit clock/context, normalization, action/permission and abstention cases. Does not prove persistence/UI/production. |
| Contract | Authored all-field/source relationship invariants, mode/consent, load/date/recommendation schemas and failures; negative unintended-mutation cases. |
| Integration | API ownership, occurrences, idempotency/correction/rebuild, mail fakes and migration compatibility on explicit disposable persistence. |
| PostgreSQL concurrency/migration | Competing same/different commands, one-winner reset, atomic state, legacy upgrade/backfill/recovery and grant boundaries. |
| Browser | Date/consent/substitution confirmation, load prefill/override/effort capture, focus/accessibility, rest/resume/account cache and interruption flows. |
| Manual/device | Actual target browser/device, keyboard/screen reader, background/network behavior, faithful source walkthrough and explanation uncertainty. |
| Security | No recovery credential, secret-free output, bad-TLS/config negatives, revocation/limit boundaries; effective live controls separately scoped. |
| Recovery/operations | Synthetic compatible upgrade/restore manifests, integrity/timing versus owner-approved RPO/RTO; no personal-data probe. |
| Outcome research | Predeclared qualified observations/confounders; deterministic correctness does not scientifically prove training benefit. |

Tie each test to a real catalog criterion. Add behavior protections for sensitive changes and deterministic traces where appropriate; avoid tests merely mirroring code. Deferred proposals are not all release blockers. Gates apply to violated controlling invariants and enabled/changed capabilities; affected security/recovery prerequisites are mandatory for their release. Exact numerical thresholds/service targets need their own accepted basis.

## Source fidelity and representative data

Independently parse approved licensed fixtures, including AMRAP/set-specific targets, and compare every admitted source slot/field/relationship/order through compiler/runtime/execution. Reconcile diagnostics/source hashes. Do not distribute copyrighted workbooks or turn an unavailable fixture into a success. Phase 2’s five known omissions require explicit repair evidence; unrestricted multiset parity does not certify them.

Synthetic data covers repeated same exercise, two weeks/users, confirmed substitutions, assistance/per-hand/machine loads, effort unknowns, technique children, retries/concurrency, corrections, partial/resumed sessions, pain/readiness, dates/DST/cross-week context and changed equipment. Choose scale/device targets from real deployment needs, not another project’s event-count/hardware assumptions.

## Failure disposition and honest CI

Preserve the original [audit result](../evidence/README.md#recorded-audit-baseline). Every failing case gets one explicit disposition: confirmed implementation defect, obsolete/conflicting expectation, fixture/environment issue or unresolved. Keep original result/test identity, contract rationale, replacement protection if applicable and later revision evidence. Never restore authored mutation/minimum-set inflation or outdated alias behavior just to pass.

Initial core: four failures around completion/minimum-set and muscle-list expectations, pending individual contract disposition. Initial API: eighteen; nine flag assumptions/two copied fixtures clear in isolated recheck, one absolute-workbook-path issue is environmental, six behavioral failures persist and need contract-specific review. Alias authored-deload and authored-review-overlay expectations may conflict with intended mode authority; do not label all six defects. Web single-query ambiguity preserves navigation protection after replacement. TypeScript’s 102 test-global diagnostics remain a failed check, not 102 independent product defects.

Required checks propagate failure; advisory output is explicitly advisory. CI must state coverage gaps and baseline dispositions, not hide them behind `|| true`. Choose API/core/browser/type/build categories appropriate to the changed capability; broaden only for unresolved regressions. Record full runs and selective rechecks separately.

## Evidence and owner acceptance

Every qualifying run records revision, dirty state, explicit environment/dataset/versions, safe procedure, expected/observed result, artifact hash/access/retention, limitations and reviewer. Keep failed evidence and independent original hashes. Security export remains failed; no permissions bypass or sealed-scan claim. Release owner acceptance explicitly names criteria/revision/evidence and accepted deviations. Documentation publication itself supplies only documentation consistency/scope evidence.
