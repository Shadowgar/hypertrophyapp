# Personal WorkoutApp product direction and supplemental requirements

**Owner direction approved:** 2026-10-21. **Status:** approved desired outcomes only; technical mechanisms, estimates, release qualification and implementation packages remain Proposed or pending. This is a supplemental requirements document under the [product contract](product-contract.md), not a new mode, roadmap, milestone, executable policy or deployed feature. This document must be read with the [requirements catalog](catalog.md), [existing traceability](traceability.md) and [M0–M6 roadmap](../roadmap/milestones.md).

## Purpose and success definition

Build **one first-party WorkoutApp for its owner**, not a general consumer fitness/social platform. The application should answer: given the owner's goals, real completed training, time, equipment, schedule and trustworthy context, what is the appropriate next training action, why, and did it help? Its primary outcomes are consistent, safe, measurable progress in muscle and strength, gradually improving conditioning and selected physical-performance benchmarks, and very low friction in the gym.

The product must work reliably without a wearable, Apple Health data, an external fitness app, a subscription to another product, or a cloud AI inference service. Prefer useful decisions and sustainable adherence over decorative scores, maximal data collection and continual novelty. Fitness-app competitors are **inspiration for capabilities only**, never runtime dependencies or providers of algorithms, records, exercise logs or APIs.

## Binding owner-level constraints

1. **Only WorkoutApp is used to plan, execute, record and evaluate training.** No Hevy, Motra, Athlytic, Training Today or other third-party fitness/health/coach application integration, exporter, API or synchronization intermediary. Do not implement, endorse or require any such bridge.
2. **Apple is the sole permitted external fitness-data/platform integration**: the owner's own Apple Health XML export imported directly into WorkoutApp, or a future first-party WorkoutApp iOS/watchOS app using Apple's HealthKit/Watch APIs with explicit permission. Apple data is optional. Existing generic hosting and code libraries are not a grant to introduce new fitness-data or inference-service integrations.
3. **No third-party runtime coaching API and no paid LLM dependency.** Interactive explanations/conversation may be implemented through locally controlled capabilities or deterministic evidence-linked responses as separately designed. No language model may author a workout prescription or bypass the deterministic, versioned decision engine (D-005 / GEN-009).
4. **Preserve user data, existing identities and authored program fidelity.** This approval does not authorize a reset, deletion, migration, merge, feature enablement, production deployment, unreviewed analytics or algorithm replacement. The [database safety lock](../../DB_SAFETY_LOCK.md) remains binding.
5. **Distinct permissions by mode:** Authored is source-faithful; working-load recommendations and lossless scheduling are allowed within their contracts. Time pressure, recovery context, equipment gaps, general fitness goals or a request for a shorter session do not authorize removing or silently rewriting authored sets, reps, intensity techniques or exercise slots. Customized can propose bounded redesign under explicit mode consent, preview, constraints and revision rules.
6. **Truth over false precision.** Missing measurements remain unknown; observed performance is not direct muscle-growth measurement; HRV does not reveal per-muscle recovery; calories and consumer scale estimates are uncertain; correlation does not prove a recommended change caused gains. Distinguish measured, self-reported, inferred and experimental fields.

## Supplemental requirement register

The stable IDs below supplement and cross-reference the original 80-ID catalog; no existing ID or original status is renumbered or silently reclassified. **All items are owner-approved desired outcomes, not implemented features or individually accepted release criteria.** Acceptance examples specify observable target behavior; detailed technical thresholds remain to be designed and qualified.

| ID | Owner-approved capability | Observable acceptance direction | Mode / existing track |
| --- | --- | --- | --- |
| PERS-001 | First-party-only product and Apple-only fitness integration | App can plan, log and analyze with no external fitness application/API; code/configuration dependency audit shows no prohibited intermediary; permissions remain opt-in | Both; governance / all tracks |
| PERS-002 | Dependable low-friction gym runner | Measured mobile Today load; weight and rep fields do not jump on save; one authoritative receipt; pending/failure/retry/correction/undo/resume cannot double-log or lose accepted sets | Both; #103, #105, M0-HIST, M6 |
| PERS-003 | Personal calendar, shift and sleep-aware scheduling | User can indicate rotating work, daytime or split sleep, available dates/windows; date-aware preview does not equate calendar midnight with recovery; missed sessions continue without invented completion | Both; M2B, M4 |
| PERS-004 | Time-accurate workout options | Estimates include source warm-ups, work, rest, transition and personal observed timing with uncertainty; a hard time limit produces feasible options, and reports remaining or reduced dose rather than claiming equivalent work | Authored lossless / Customized consent; M2B, M4 |
| PERS-005 | Change-of-available-time during a session | On time change, show continue/reschedule/preserve remaining options; never erase performed sets or silently change authored source dose or completed occurrence | Both; M2B, M4, M6 |
| PERS-006 | Equipment, exercise-variant and setup memory | Location, machine/implement, per-hand/stack/assistance semantics, increments, attachments, seat/grip/setup, cues and comparability boundary persist without cross-variant PR or load contamination | Both; M2A, M3 |
| PERS-007 | Personal demonstrations and concise exercise help | Relevant guides or user-authored cues are reachable in one interaction without obstructing set entry; licensing/provenance preserved; optional videos are advisory, not reliable injury diagnosis | Both; M1, M6 |
| PERS-008 | Starting loads and individualized next-load advice | Optional known 1RM/recent-set/manual calibration; effective qualified comparable logs outrank estimates; recommend increase/hold/decrease/monitor with reason, attainable increment and editable actual; unknowns never fabricated | Both; #103, M2A |
| PERS-009 | Minimal optional effort and technique feedback | Missing RIR/RPE, pain, technique and fatigue stay missing; request context only when helpful; safety flags never silently mutate authored slots, and qualified comparable performance remains central | Both; M2A, M3 |
| PERS-010 | Contextual recovery rather than magic score | Differentiate systemic state, local exercise performance/soreness and time feasibility; subjective feedback and biometrics show sources, trends, data freshness and uncertainty; no per-muscle physiological recovery percentage claimed | Both; M3, M5 |
| PERS-011 | Direct Apple Health XML import | User manually exports using Apple Health, uploads directly, previews limited chosen fields, confirms import; idempotent re-import, timezone/source fidelity, partial coverage and delete/error handling; no intermediary app/API | Optional; M0-SAFE, M3, M6 |
| PERS-012 | Future first-party HealthKit sync | Separately approved native WorkoutApp iOS companion reads explicitly allowed types through HealthKit; sync reconciles additions/deletions and stale/offline data without giving Apple measurements authority to rewrite workouts | Optional; M6, after import qualifications |
| PERS-013 | Future first-party Watch experience | When justified, WorkoutApp watchOS companion displays current exercise, next-set context, rest and confirmed receipts; on-device HealthKit/workout sync only; automatic rep/exercise recognition is an investigational, unproven later capability | Optional; M6, later |
| PERS-014 | Coordinated hypertrophy, strength, conditioning and personal physical benchmarks | User chooses goal priority and relevant tests; plan exposes tradeoffs and periods, monitors comparable measurements without asserting a generic military/occupational certification score | Customized planning / Authored advisory; M3–M5 |
| PERS-015 | Body-composition and light nutrition context | Trend body weight/waist/optional photos/nutrition from directly entered or Apple-permitted records; show missingness and uncertainty; do not mistake scale-estimated lean mass for measured hypertrophy or require a massive food logger | Optional; M3/M5 |
| PERS-016 | Individual-response learning with reversal | Predeclare question, comparison metric/window/confounders and evidence sufficiency; log accepted/declined changes and subsequent outcomes; require bounded change/rollback, abstain on noisy data and no causal-optimality assertion | Authored advisory / Customized gated; M5 |
| PERS-017 | First-party explanatory coach | Explain evidence, reason, limits, next action, unchanged recommendation and time-limit options; conversation must not create unreviewed training rules or use external fitness/AI coaching APIs | Both; M3/M5/M6 |
| PERS-018 | Transparent analytics and outcomes | Show actual completed sets, adherence, comparable load/reps, trends, benchmark results and confidence/sufficiency with corrected/void history handled; no fictional growth or recovery measurements | Both; M3/M5 |
| PERS-019 | Personal privacy and data ownership | Import scopes are explicit, records trace source/device/date/timezone, access is account-bound, private uploads are limited/encrypted/protected, deletion/export policy is reviewed, and no sensitive events leak into telemetry or Git | Both; M0-SAFE/M6 |
| PERS-020 | Research-backed rule maintenance | Version evidence and assumptions, separate established findings from conjecture, test numeric changes against existing contracts, do not silently activate frozen metadata scoring or source mutations | Both; M3–M5, governance |

## End-to-end expected experience

1. **Before training:** Home shows next scheduled session, estimated duration/constraint mismatch, selected goals and optional freshness-qualified recovery context. No mandatory wellness questionnaire or blocked workout due to absent wearable data.
2. **Set preparation:** Surface exercise/variant, exact prescribed work, source warm-up, one suggested load with basis/confidence when qualified, and the most relevant comparable last performance. Known-1RM is optional and distinguished from an estimated value or actual exposure.
3. **Execution:** Weight/reps/Save stay spatially stable. Single confirmed receipt list, reliable idempotent save, rest timer, next-set continuation, easy correction/undo, and durable resume even across reload or network errors. Actual effort is never guessed from a target.
4. **Limited time / interruption:** State what is complete and what can be rescheduled. For Authored preserve remaining source units; for Customized show explicit alternative and effect on dose before applying.
5. **After training:** Report actual completed training, honest comparison, next scheduled action, and which recommendation (if any) is supported. Never automatically declare muscle growth, full recovery or causal optimization.
6. **Over weeks/months:** Track adherence, comparable progression, conditioning and optional body-context trends; run cautious outcome reviews of clearly bounded suggestions rather than forcing weekly algorithmic novelty.

## Authority, interfaces and data provenance

- **WorkoutApp set/event/effective-history records:** authoritative for performed reps, load, exercise identity, correction/void, consent, occurrence and completion. Never backfill performed sets from a Watch workout or HR spike.
- **Authored compiler and source versions:** authoritative for Authored work prescription; adaptation cannot replace it, regardless of schedule/fitness/wearable data.
- **Customized normalized profile + deterministic engine:** authoritative for proposed prescription under explicit user consent and valid hard constraints. The AI explanation layer is read-only to prescription decision authority.
- **User-declared context:** work/time availability, shift pattern, sleep context, subjective recovery, equipment setup, pain/technique and benchmarks. Ask permission before storing sensitive details; unknown stays unknown.
- **Apple Health imports/native reads:** optional measurements with source, units, timestamp, timezone, coverage, uncertainty, sync freshness, access scope and deletion provenance. No claim of live HealthKit access in Safari. Do not confuse a ChatGPT-connected health source with permission or a data pipe to WorkoutApp.
- **Derived observations:** trace input versions and formulas, show confidence/absence, recompute after corrected/void data; advice and actual user action are separate events.

## Apple implementation boundaries

**Stage A — manual export/import:** Apple's Health app provides Export All Health Data (XML). WorkoutApp handles the user-selected upload without a third-party exporter. Design bounded preview/filter, import provenance, size limits, secure streaming parsing, rejection of path traversal/zip bombs/XML external entities, safe storage and deletion. Never dump raw full exports, health metrics or private notes into application logs, repository fixtures or telemetry. A full Apple export is substantially broader than training data: import only approved categories.

**Stage B — native first-party synchronization:** after a separately approved iOS design, the same WorkoutApp account/backend can use native HealthKit with per-type read permissions and scoped server sync. Handle revoked permissions, duplicate/retracted samples, timezone and device/source identity, partial coverage, eventual delivery and disclosure of last successful synchronization. Native iOS capability is required; browser code does not itself have HealthKit authorization. Watch support is a further independently qualified stage, not required for A or the main web app.

Apple documentation: [Health XML export](https://support.apple.com/guide/iphone/iph5ede58c3d/ios), [HealthKit authorization](https://developer.apple.com/documentation/healthkit/authorizing-access-to-health-data), [observer queries and delivery](https://developer.apple.com/documentation/healthkit/executing-observer-queries).

## Science and evaluation guardrails

- Translate established literature into **versioned candidate rules**, with explicit population/assumptions and study quality. A literature citation alone never authorizes changing numerical workout policy.
- The 2026 ACSM resistance-training position stand (PMID [41843416](https://pubmed.ncbi.nlm.nih.gov/41843416/)) supports progressive training and broadly appropriate dose; it does not certify a unique optimal program for this user.
- Split vs full-body when volume-matched (PMID [38595233](https://pubmed.ncbi.nlm.nih.gov/38595233/)) supports flexible planning without arbitrary split superiority.
- Estimated proximity-to-failure dose-response (PMID [38970765](https://pubmed.ncbi.nlm.nih.gov/38970765/)) is exploratory; don't enforce a universally precise RIR setting.
- Combined aerobic and strength training (PMID [34757594](https://pubmed.ncbi.nlm.nih.gov/34757594/)) supports coordination rather than an automatic ban on conditioning; explosive-performance tradeoffs merit attention.
- HRV-guided outcomes (PMID [34639599](https://pubmed.ncbi.nlm.nih.gov/34639599/)) and subjective well-being monitoring (PMID [26423706](https://pubmed.ncbi.nlm.nih.gov/26423706/)) caution against universal readiness scores and support measured plus self-reported context.
- Evaluate recommendations prospectively, distinguishing developer correctness, adherence, strength changes and independently measured body outcomes. Do not present algorithm-selected workouts as proven best for all people or for the individual.

## Scope, status and next step

**Current delivery truth:** the M0–M6 roadmap remains the one roadmap. M4 Customized functionality was integrated into GitHub main via [PR #107](https://github.com/Shadowgar/hypertrophyapp/pull/107), with release and live-environment qualification distinct. [Issue #103](https://github.com/Shadowgar/hypertrophyapp/issues/103) remains the gym-blocking reliability/units/starting-load work; [Issue #105](https://github.com/Shadowgar/hypertrophyapp/issues/105) and draft [PR #108](https://github.com/Shadowgar/hypertrophyapp/pull/108) cover end-to-end visual sketches, **not deployed fixes**. Do not infer final PR #108 visual acceptance from approval of these product ideas.

See the [personal capability crosswalk](../roadmap/personal-capability-crosswalk-2026-10-21.md) for sequencing and [next coder handoff](../operations/next-coder-handoff-2026-10-21.md) for a bounded, read-only planning request. No application implementation, migration or deployment is authorized by this document alone.
