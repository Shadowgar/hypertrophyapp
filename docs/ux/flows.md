# Product flow requirements

Owner-approved desired mode/date/load direction, detailed UI/API mechanisms Proposed. [Product](../requirements/product-contract.md), [profile](../contracts/onboarding-profile.md), [execution](../contracts/execution-plan.md), [dates](../contracts/selected-date-scheduling.md), [recommendations](../contracts/recommendations.md) and [UX catalog](../requirements/catalog.md#ux) govern outcomes. This is target behavior; [current state](../architecture/current-state.md) identifies incomplete implementation.

1. Select Authored Plan or explicitly consent to Customize My Workout. Manual/auto program recommendation is separate. Normalize applicable answers; display unsupported/defaulted controls honestly.
2. Select actual distinct dates in the user's current local week. Preview allocation, preserved source dose/relationships, duration uncertainty and conflicts; confirm a feasible revision without silent loss.
3. Open/resume the stable scheduled occurrence. Display source prescription, load reason/override, meaningful relationships and actual set input. Retry and correction preserve effective history.
4. A constrained source slot offers a source-approved alternative and waits for explicit confirmation. Declining keeps it unresolved; no unrelated dose changes. Load-only automatic prefill remains overridable.
5. Review history/advice with comparable exposure coverage, missing evidence and permission boundaries. Authored redesign advice never writes a changed prescription; switching modes requires explicit consent and preserves prior history.

Accessibility, account-scoped cache clearing and recovery are qualification needs from the first affected flow. These desired flows do not establish implemented layout/routes, selected-date behavior or qualified offline writes. Original research/flows remain [historical support](../flows/Onboarding_and_Flows.md) with retained [research registry](../archive/README.md).
