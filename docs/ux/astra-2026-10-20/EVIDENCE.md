# Browser evidence — Astra UX audit, 20 October 2026

This index records the existing frontend observations behind [AUDIT.md](AUDIT.md). **LIVE** means deployed guest behavior; **SYNTHETIC** means the deployed frontend rendered against invented, intercepted API responses. Neither establishes authenticated backend correctness. The owner explicitly chose clearly labeled synthetic journeys instead of a disposable authenticated backend. Design sketches are separate **PROPOSED** artifacts and are not application evidence.

## Environment and provenance

- Deployed frontend: `https://hypertrophy.theroccos.us`; Chromium at **390 × 844** mobile and **1440 × 900** desktop viewports.
- Source revision: `fc3bd0c7b93c9d3232e6aec758e16efcca6ac583`; deployed login footer: `d60d9ed413329f575947568c05888546f8d3e6d5`. The browser auditor confirmed an empty `apps/web` diff between them. Production backend revision was not independently verified.
- Guest pages used live responses. All signed-in data, receipts, prescriptions and session state were synthetic. No real credentials, account records, private logs or database were inspected; no production data were modified. Developer wipe/reset controls were not clicked. Customized Accept/Activate and real scheduling activation were not performed.
- Full-page screenshots can be taller than the viewport. The [asset manifest](evidence/manifest.json) records each image's dimensions and evidence class. It currently lists **35 captures: 4 LIVE guest and 31 SYNTHETIC frontend**. Image dimensions describe captures, not viewport size or responsive qualification.
- This is an observation/capture record, not a self-contained automated replay harness. Exact browser version, full fixture payloads, network archive and timing distributions are not bundled. Repeating the synthetic scenarios requires recreating their responses and confirming the relevant frontend revision.

## Exact measurements

| Class / state | Recorded result | Interpretation / limit |
|---|---|---|
| LIVE guest Home, 390 px wide | Document **1861 px** high; six similarly weighted action controls; no dock | A long undifferentiated entry screen; not a measured completion-time study |
| LIVE Login | Show Password **32 px** high; Login **40 px** high | Measured visible controls; not a full touch-target/accessibility audit |
| LIVE public Home navigation, one sample | TTFB **274.2 ms**; DOMContentLoaded **861.1 ms**; load **866.8 ms** | Single observation from this host; not mobile-network percentiles or workout-backend latency |
| SYNTHETIC Authored initial mobile runner | Working-weight input top **1526.75 px** against **844 px** viewport | Core working entry below the initial view |
| SYNTHETIC work set before acknowledgement | Input top **274.75 px**; inner scrollTop **1236 px**, clientHeight **783 px**, scrollHeight **2019 px** | Baseline after scrolling to the form |
| SYNTHETIC same work set after acknowledgement | Input top **364.75 px**; scrollTop **1236 px**, scrollHeight **2165 px** | **90 px downward content displacement** at unchanged scroll offset; total inner content grew **146 px**. This was not a 90 px browser scroll |
| SYNTHETIC same acknowledgement | Active element **INPUT → BODY**; header Set 2/3; **one** effective receipt above form | Focus loss and fragmented controls observed; duplicate receipt values not reproduced |
| SYNTHETIC desktop, 1440 px viewport | Main and exercise dialog **448 px** wide at **x=496 px**; working input top **1536.75 px** | Phone-width cap persists. Home/Week/Settings/Check-In/History/Customize also measured 448 px main |
| SYNTHETIC Customized setup, 390 px width | Full-page height **2040 px** | Form and explanatory copy length; not the height of every consent/preview state |
| SYNTHETIC Today delayed response | Injected **4000 ms** delay; “Load today's workout” / “No workout loaded” at elapsed **1298 ms**; session visible at **5261 ms** | Establishes misleading initial presentation under this controlled delay; does not diagnose the owner's two-minute wait |
| SYNTHETIC Home profile | Canonical **80 kg** rendered as **80 lb** | Unit-label defect for the fixture, corroborated by source |
| SYNTHETIC rolling History calendar | **23 September–20 October**; Wednesday **23 September** rendered below **MON** | Weekday misalignment; source explains missing leading grid slots |
| SYNTHETIC three-set/correction sequence | Acknowledgements showed **1 → 2 → 3** Edit-set buttons and All Sets Complete; corrected set 1 to **11 reps**; Undo removed set 3; reload showed **2 receipts**, set 1 at **11 reps**, counter **Set 3/3** | Frontend reconciliation/hydration from in-memory fixture responses only; not durable backend persistence or idempotency qualification |

## Reproduction paths and representative captures

### LIVE guest entry

Open Home at the mobile viewport, then inspect Login, onboarding welcome and recovery. Unauthenticated Today redirected to `login?next=%2Ftoday`. Login fields had placeholders without persistent labels/IDs, and email used `type=text`. Recovery showed request and confirmation together. Onboarding displayed developer wipe/reset affordances; their backend permission gates were not tested.

[Home](evidence/astra-live-home-mobile.png) · [Login](evidence/astra-live-login-mobile.png) · [Onboarding](evidence/astra-live-onboarding-mobile.png) · [Password recovery](evidence/astra-live-reset-password-mobile.png)

### SYNTHETIC Authored execution, acknowledgement and error

Provide an Authored Cross-Body Lat Pull-Around fixture with three working sets and kg load context. Open the exercise: warm-up copy showed both “1.0 sets” and “1.0 warm-up sets,” kg warm-up input and technical controls before working entry. Acknowledge a synthetic warm-up, then enter **12 reps, 40 lb, actual RPE 8** for working entry. Hold the inner scroll offset and compare input position/focus before and after the work acknowledgement. A controlled **503** left “Set was not confirmed. Retry the same set before continuing.” outside the dialog while its button returned to Complete Set; no error appeared inside the dialog. This is a frontend visibility result.

[Initial mobile runner](evidence/astra-fixture-exercise-top-mobile.png) · [Before save](evidence/astra-fixture-set-before-mobile.png) · [After acknowledgement](evidence/astra-fixture-set-after-mobile.png) · [503 state](evidence/astra-fixture-set-error-mobile.png) · [Desktop runner](evidence/astra-fixture-exercise-desktop.png)

A later synthetic journey acknowledged three working sets, corrected set 1, undid set 3, and reloaded/reopened using in-memory fixture state. The displayed receipt/count result is recorded above. This expands frontend interaction coverage without establishing server storage, concurrency, correction-chain rebuilding or retry deduplication.

[Three acknowledged sets](evidence/astra-fixture-three-sets-mobile.png) · [Correction/undo then fixture reload](evidence/astra-fixture-correction-reload-mobile.png)

Keyboard observation: focus the runner's last Check-In link, then press Tab; focus moved to the background Workout link outside `aria-modal`. No screen-reader, OS keyboard or full keyboard traversal pass is claimed.

### SYNTHETIC loading, settings and planning

Delay Today by 4000 ms to inspect the initial empty-looking prompt. Send **500** for Settings POST `/profile`; no normal success/failure text was visible. Inspect Home with weight 80 in canonical kg; it displayed 80 lb and token presence produced Synced. Auth links remained visible while signed in. Week showed `custom` for a manual Authored program, plus IANA timezone, Mesocycle Posture and Coverage Radar. No plan was activated.

[Today loading](evidence/astra-fixture-today-loading-mobile.png) · [Home](evidence/astra-fixture-home-mobile.png) · [Settings failure](evidence/astra-fixture-settings-save-error-mobile.png) · [Week mobile](evidence/astra-fixture-week-mobile.png) · [Week desktop](evidence/astra-fixture-week-desktop.png)

### SYNTHETIC review, Customized and guides

Empty History showed Completion 0%, Best weekday Mon and the Missed legend; no personal working history was inspected. Check-In was headed Sunday Review and its bodyweight field had no unit. Customized setup and a valid proposal were rendered; Accept was disabled before its acknowledgement checkbox and enabled after checking it. Neither Accept nor Activate was clicked. The Customized runner retained separate kg, RIR, technique and pain controls. All seven guide-related route patterns rendered using synthetic content; the exercise guide exposed full JSON. Real source-licensed content was not copied.

[History mobile](evidence/astra-fixture-history-mobile.png) · [History desktop](evidence/astra-fixture-history-desktop.png) · [Check-In](evidence/astra-fixture-checkin-mobile.png) · [Customized setup](evidence/astra-fixture-customize-mobile.png) · [Customized consent](evidence/astra-fixture-customized-consent-mobile.png) · [Customized runner](evidence/astra-fixture-customized-exercise-mobile.png)

## Exclusions and unresolved claims

An initial malformed proposal fixture caused a caught error boundary; a corrected fixture succeeded. A legacy preference fixture caused a `missing_fields.join` error. Missing mock basis presentation fields also produced blank detail. These fixture-shape problems are **excluded from product findings**; the legacy route's forms were still inspected. These are not proof of production errors.

Literal duplicate receipt values were **not reproduced**. The real **roughly two-minute Today wait**, and the owner's **29-set/doubled-title scenario** remain unresolved; no matching real record or 29-set fixture was examined. The public Home timing does not answer those questions.

No physical iPhone/Safari or Android-device test, OS keyboard coverage, screen reader, complete WCAG audit, timer suspension/expiry test, real authenticated backend timing, email delivery, durable storage/reload, concurrent command/correction qualification, migration check or Phase 2-specific rendered workout was completed. Those are limits, not passing results. Source-only causal findings are documented separately in [SOURCE-APPENDIX.md](SOURCE-APPENDIX.md).
