# High-risk contracts

Current contract map under [product](../requirements/product-contract.md), [constitution](../governance/constitution.md) and accepted decisions. Technical mechanisms remain Proposed unless explicitly accepted; the contract outcome does not imply implemented behavior. [Runtime authority](../architecture/runtime-authority.md), [requirements](../requirements/catalog.md) and [test strategy](../quality/test-strategy.md) qualify each affected change.

| Contract | Boundary and required negative protection |
|---|---|
| [Authored source](authored-source.md) | Preserve all slots/set-specific/non-numeric prescriptions, relationships and provenance; no generated writer/source mutation. |
| [Execution plan](execution-plan.md) | Preserve source intent, consent, occurrence/slot/variant and effective corrections; no cross-week progress/retry contamination. |
| [Onboarding profile](onboarding-profile.md) | Deterministic normalized inputs/origins; no raw answer or trace-only control silently affecting generation. |
| [Customized generation](customized-generation.md) | Explicit mode consent, original deterministic construction, hard constraints or visible infeasibility; no authored topology replay. |
| [Load progression](load-progression.md) | Completed comparable exposures/actual load-effort; load-only automatic authority, uncertainty, override and undo. |
| [Selected dates](selected-date-scheduling.md) | Actual local-week dates, timezone, stable occurrence and lossless relationship-aware allocation; no implicit count-only schedule. |
| [Recommendations](recommendations.md) | Evidence/version/permission and outcome record; no Authored design mutation by advice. |
| [Metadata accounting](metadata-accounting.md) | Dose accounting and variant identity; scoring freeze cannot be bypassed. |
| [Security architecture](../security/architecture.md) / [data model](../architecture/data-model.md) | User scope, recovery/session lifecycle, concurrency, schema ownership and disposable verification. |

Legacy [canonical schema](Canonical_Program_Schema.md), [high-risk payload/API contracts](High_Risk_Contracts.md) and [offline contract](Offline_Sync_Deterministic_Contract.md) retain compatibility details. Existing wire fields and error shapes are not changed by docs migration. No new ADR authorizes silently dropping fields. Resolving divergent proposed schema keys, preview/apply transitions or offline-write scope requires a bounded implementation plan and consumer verification; offline writes remain deferred.
