# First implementation slice: audit coverage

Status refers to development code and the bounded qualification in [README](README.md), never production activation. The [approved 28-finding trace](https://github.com/Shadowgar/hypertrophyapp/blob/33598c3fb35328cc2d2b6310865f716380b6c81e/docs/ux/astra-2026-10-20/unified-2026-10-21/TRACEABILITY.md) remains the design reference; the audit was not repeated.

| Finding | This PR | Remaining approved work / limit |
|---|---|---|
| F01 Sign-in writes setup | Authentication separated from setup; negative login test. | Full guided onboarding layout. |
| F02 Equipment clears constraints | Narrow PATCH; full unrelated-profile/history preservation tests. | Full equipment-page composition. |
| F03 Logger buried | Main entry above disclosures; visible on mobile/desktop. | Physical gym trials and cold schedule construction performance. |
| F04 Input shift | Fixed composer/status geometry; measured no movement on confirmed save. | Physical mobile keyboard qualification. |
| F05 Hidden save/undo errors | In-runner pending, uncertain, rejected and undo feedback. | None declared fixed in production. |
| F06 Retry differs from draft | Frozen payload/command, reload reconciliation, late-response tests. | Production durability acceptance separate. |
| F07 Mixed units | Shared preference, exact canonical actuals, warm-up/correction/history/summary conversion. | Check-In/body-measurement redesign is later. |
| F08 Partial vs complete | Working-set completion remains server-owned; calendar legend says logged activity. | Full History/completion state redesign. |
| F09 Calendar weekdays | No new calendar placement policy. | Week/History calendar redesign and DST qualification. |
| F10 Settings save feedback | Explicit preview/save/confirmed/uncertain/conflict; revision checking. | Remaining Settings forms. |
| F11 Ambiguous states | Today loading, rest day, unavailable and set outcome states separated. | Full Home/Week/History state layouts. |
| F12 Developer wipe affordances | No new destructive affordance or authority. | Full onboarding/account presentation pass. |
| F13 Mode labels | Authored/Customized explicit in runner; separate contracts retained. | Program selection and consent presentation. |
| F14 Activation before review | Accepted plan/prescription policy unchanged. | Workload/revision preview composition. |
| F15 Equipment effects | Equipment-only update preserves accepted data. | Unified setup/inventory effect explanations. |
| F16 Check-In scope | No review or future-plan authority changed. | Full Check-In redesign. |
| F17 Account labels/pending | Login labels, duplicate guard and signing-in feedback. | Full recovery and onboarding form layouts. |
| F18 Navigation/return | Shared responsive shell, More and safe return path. | Guided Home/library content. |
| F19 Narrow desktop | Native desktop navigation/execution/receipt columns. | Other full desktop page compositions. |
| F20 Missing history context | Units, actual effort, receipt kind, correction and original identity included. | Full History layout and analytics split. |
| F21 Analytics races/labels | No new metrics or scoring activated. | Dedicated Analytics redesign/identity guards. |
| F22 Rest timer | Reserved confirmation area; deadline retained across refresh. | Physical background/suspension qualification. |
| F23 Starting strength | Manual/recent/known-1RM reference choices; unsupported calculation disclosed. | Authored 1RM evidence admission is not invented or activated. |
| F24 Excess setup questions | Login does not run setup. | Approved guided onboarding sequence. |
| F25 Modal/focus | Named native dialogs; working-input focus preserved on save. | Physical keyboard and screen-reader tests. |
| F26 Accessible selection | Equipment selected state and independent native appearance controls. | Full inventory selector redesign. |
| F27 Raw warm-up count | Numeric display normalized; source count and warm-up identities preserved. | None declared fixed in production. |
| F28 Internal vocabulary | Plain main task; advanced owner-provided context behind disclosure. | Week/Analytics/Check-In copy and structure. |

**Issue #103 remains partial. Known-1RM is reference-only; qualified starting-working-load calibration, cold Today performance qualification and physical iPhone keyboard/background acceptance remain open.** See [smallest next load package and safe physical-device instructions](correction-pass/REMAINING.md).

Issue #103's Cross-Body journey is exercised against the real API, including warm-up, actual weight/reps/effort, confirmed save, rest, next set, correction, undo, reload and History. The synthetic schedule retains the source's combined Full Body #1 + #2, 10 exercises and 29 working sets; this PR does not silently change that source grouping or claim it was a production diagnosis. No runtime LLM, shadow load formula or altered Authored prescription was added.
