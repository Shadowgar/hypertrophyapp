# M4-R — Evidence-informed six-service fitness preparation and adaptive training design (candidate v0.1)

**Date:** 2026-10-16. **Research/design only.** Extends [current six-service standard register](us-military-six-service-fitness-standards-2026.md) and [H2F cross-project appraisal](military-h2f-cross-project-appraisal.md). Not an implemented training plan, validated medical screening, injury predictor, official military score certification, or approved physiological prescription. Existing **hypertrophy-first C1 issue #85** is unaffected.

## 1. Design objective: what the system should actually optimize

The user seeks excellent hypertrophy and **measurable military fitness above the applicable qualification floor**. Those are overlapping but **nonidentical** outcomes. Proposed separate objective profiles, each explicit opt-in:

- **Hypertrophy-first:** largest sustainable individual muscle-development stimulus reasonably compatible with their chosen gym time; optional cardiopulmonary activity when it doesn't displace consented priorities.
- **Military Readiness:** pass **all** events on the selected and presently applicable service/occupation test, then improve the **weakest standard margin**, then pursue the next officially defined score class or user-defined reserve margin. Also improve selected physically relevant operational skills *beyond* that test where supported and qualified.
- **Hybrid:** user chooses an explicit relative priority and real time budget; aim for military pass-plus-margin without quietly stealing all available hypertrophy sets or demanding two simultaneous global maxima.

The optimizer is **multi-objective** and **constraint aware**, not a single fabricated “universal super soldier fitness score.” Military tests can measure minimum job-relevant capacities; they do *not* establish comprehensive combat readiness, ability to fight, aquatic safety certification, medical eligibility or skill competence.

**No promise of maximum results in the least possible time**: empirical science does not identify an individual global optimum. Offer testable progress, efficiency and transparent tradeoffs instead.

## 2. Assessment ontology — translate branch tests into trainable skills

| Physical capability | Tested events / example services | Programming ingredients (qualitative, not official exercise prescription) | Measurements and pitfalls |
| --- | --- | --- | --- |
| **Aerobic sustained running** | Army 2mi AFT; Navy 1.5mi PRT; USAF/USSF 2mi; Marine 3mi; Army CFT 1mi x2 | Individualized easy aerobic sessions where tolerated, gradual duration exposure, event-paced segments and appropriate faster-running work only after baseline conditioning | Run distance/time, course/terrain, pacing/symptoms, consistent event version; do not convert one runner's 1mi directly into a certified 3mi score |
| **Short intense efforts / maneuverability** | Army sprint-drag-carry/CFT sprint and movement drills; Marine CFT 880yd movement-to-contact and Maneuver Under Fire; USAF HAMR | Gradual running acceleration and repeated-effort conditioning, change-of-direction mechanics, relevant task-specific supervised practice where safe | Time and validated course, footwear, rest between bouts and technique; faster 100m does not independently pass whole course |
| **Maximal/repeatable loaded strength** | Army **3RM deadlift**, Marine ammo-can lifts, Army sandbag repetitions, loaded water-can carries; optional tactical/ruck tasks | Repeatable multi-joint strength (hinge, squat, push/pull), progressive carry and local muscular endurance where relevant; demonstrate proficiency before heavier implement handling | **Army 3RM ≠ 1RM**; official implement mass and task technique required; don't replace 3RM with estimated 1RM score |
| **Upper-body muscular endurance** | Army hand-release/dead-stop pushups; Navy/USAF/USSF and Coast Guard pushups; Marine pullups or pushups; Navy combat weighted pullups/pushups | Authentic event-form practice alongside progressively loaded pressing/pulling and sets of quality repetitions; build endurance without routinely taking every set to failure | Actual event style, timed window, approved ROM/repetition rules, body mass, assist/weighted semantics; generic machine chest press doesn't equal 2min pushup score |
| **Trunk endurance and bracing** | Army plank; Marine mandatory plank; Navy/USAF/USSF/USCG event-specific planks or alternatives | Specific timed position practice and general trunk strength/bracing integrated in other lifts | Different plank protocols and alternate exercise rules, no automatic conversion of situps to plank score |
| **Swimming and aquatic work** | Navy general alternate swim; combat 800m with fins; Coast Guard approved swim option; specialized accession | Water competency assessment, supervised technique, progressively timed swim intervals and endurance with suitable safety controls | Facilities, aquatic competency, lifeguard/supervision; **never assign unsupervised breath-hold/underwater hypoxic drills**; a land fitness test cannot imply water-skill qualification |
| **Loaded field movement** | Army combat carries/sandbags; Navy combat 20lb weighted tasks; Coast Guard specialty CFT; task-specific ruck | General resistance+aerobic base before carefully added load carriage; separate progress of load, distance, speed, terrain and total weekly exposure; boots/terrain conditions recorded | Specific test rig/vest/pack, terrain, temperature, musculoskeletal tolerance; **rucks are not a required event on every service-wide test** |
| **Body composition** | Navy BCA, USAF scored waist-height, USSF separate BCA, USMC WHtR, USCG BCS | Optional non-stigmatizing body composition tracking and evidence-based nutrition education where appropriate; clinical/pregnancy/waiver contexts must be professionally managed | Official age/sex and method/version rules; a strength workout cannot promise body-composition compliance by a particular date |

### Exercise selection: “best for **this** user's tested goal”

Select from an **original** exercise-action ontology using equipment, actual technique, constraints, skill/comfort, comparable history, time and selected military events. Maintain separate **hypertrophy stimulus** and **tested movement-performance** classifications. A compound lift can develop general capacity for both, but success in a squat is not proof of CFT dragging speed or PFT run ability. Preserve one or more stable movement variants so progress is observable. Introduce event-specific movements for sufficient exposure to the *actual* official testing conditions without copying a proprietary field manual's weekly program.

## 3. The individual assessment → action → re-test loop

**Step A — classify:** branch, active vs reserve, in-service vs accession, duty specialty/combat status, age/scoring rules, exact test edition/date, selected event alternates and known restrictions. Distinguish authoritative scoring chart availability. A military candidate's training goal does not establish medical/entrance eligibility.

**Step B — establish a safe baseline:** history and confidence; voluntary submaximal calibration of current strength and quality; record available self-performed event attempts when appropriate. No forced novice all-out 3RM, loaded vest/ruck event or dangerous underwater assessment to obtain first score. Record actual trials as `practice_self_reported`, `supervised_practice`, or `official_result_provided_by_user`, and do not infer official certification.

**Step C — calculate *per-event deficit and margin*:** compare **only** with fully verified chart for the user's demographic/role/method/date. Store each event raw performance, grade, time/repetition/distance units and whether requirements were met. Prioritize any hard-fail event first, then the smallest passing margin, then higher performance tier. When chart inaccessible, show **component-only readiness** and `official_score_not_verified`, not a fabricated percent probability.

**Step D — tailor weekly microcycle:** place available resistance, runs/intervals, calisthenics, trunk/carry and, when relevant, swimming into actual user-selected dates and time constraints. Track both intended and completed minutes, volume, load, RIR/actual exertion, distance and event timing. Avoid back-to-back high-load running/plyometric/ruck stress when current condition cannot sustain it. Manage **interference risk**, not assume simultaneous maximization of all qualities.

**Step E — adapt quickly when evidence is strong, cautiously when it isn't:** next-set/next-exposure load calibration from **comparable completed work** (reusing independent M2A semantics), technique and user-rated effort. Longer-term changes to weekly run dose, ruck stress, weekly sets or target event should be deliberate, one or few changes with written rationale and user approval. More weight or mileage is not a substitute for demonstrated recovery and capability. An unexpectedly easy session can receive a **same-day bounded suggestion**; one poor day must not trigger a massive deload or conclude “overtrained.”

**Step F — periodic test-specific check:** use reproducible event performance or a tolerable progressive practice proxy; schedule formal mock multi-event days only when skill, recovery and event-specific readiness support it. Verify course, event order and allowed alternatives for accurate comparison. Under high uncertainty, abstain from inferring an official performance category. Compare running pace, push-up quality, event-specific handling, adherence and longer-term body composition separately rather than imputing direct muscle hypertrophy.

**Step G — stop / revise:** pain, marked decline in movement competence, illness/heat symptoms, concerning cardio signs or lack of environmental safety prompt pausing relevant task and appropriate assessment, not “push until you break.” Program completion is never a substitute for military-authorized testing or health clearance.

## 4. Literature and doctrine synthesis; limits

- **Army H2F:** [Army current doctrine (Sept 3, 2026)](https://www.army.mil/article/295085); [H2F physical domain](https://h2f.army.mil/Domains/Physical-Domain/). Assess actual demands and support functional conditioning across relevant domains. Doctrine specifies *institutional approach*; it isn't evidence that an identical military PT routine maximizes hypertrophy in the general population.
- **Load carriage performance:** [Knapik et al. 2012 systematic review, PMID 22130400](https://pubmed.ncbi.nlm.nih.gov/22130400/): 10 primary studies; combined **progressive resistance, aerobic and task-specific load carriage** produced substantial performance changes. However, intervention details/populations vary, and the summary effect is not a validated dosage curve for beginners.
- **Load carriage safety:** [USMC recruit retrospective injury comparison, PMID 38552130](https://pubmed.ncbi.nlm.nih.gov/38552130/): 2,363 original vs 681 modified regimen recruits, overall injury proportions 58% vs 39%, but **observational, nonequivalent cohorts** with heterogeneous subtypes, including higher stress reactions and severe injury share in modified cohort. Do **not** quote 19-point difference as causally guaranteed injury prevention for our users.
- **Loaded marches risk modifiers:** [2025 narrative review PMID 40442982](https://pubmed.ncbi.nlm.nih.gov/40442982/): load, speed, terrain, heat/foot conditions and exposure affect tolerability/injury risk. **No clinical injury probability model follows from this.**
- **Concurrent endurance/strength:** [2026 umbrella review PMID 41762427](https://pubmed.ncbi.nlm.nih.gov/41762427/) included 17 meta-analyses; combined strength+endurance improved aerobic fitness without consistently reduced average growth in included samples, but evidence uncertain for high-performance/specific modalities. [2024 meta-analysis PMID 37847373](https://pubmed.ncbi.nlm.nih.gov/37847373/) found some male lower-body strength interference and inadequate sex-specific muscle-hypertrophy data. Overlapping study pools cannot be added as independent evidence.
- **Existing M4-R hypertrophy science:** retained as original strength/hypertrophy track. No need to redo Batches 01–07 or owner-provided multi-GB JN archives. Military training is a goal-specific **supplement**, not permission to erase or overrule the hypertrophy rationale.
- **Qualification:** these are targeted sources, not a completed military-performance systematic review; no direct proof our proposed combined policy is “maximum speed with zero injury risk.”

## 5. Training phases — flexible structure, *not* arbitrary calendar prescriptions

| Phase | Entry/goal | Allowed training emphasis | Gate to advance |
| --- | --- | --- | --- |
| **Physical foundation / competency** | Unknown, deconditioned, returning or skill-limited; stabilize tolerable exposure | Safe movement and load calibration, general resistance strength, easy appropriate aerobic activity, scaled calisthenics; establish event technique | Repeated completed sessions with usable comparable observations and ability to demonstrate relevant movements, not elapsed calendar days |
| **Event capacity development** | Skill and history sufficient for gradual increased challenge | Movement-specific run/row/swim and calisthenics, sustained strength + conditioning, selected harder sessions, extra weak-event practice | Trend toward each valid event floor without loss of adherence or unacceptable tolerance/recovery cost |
| **Integrated readiness / mock tests** | Credible individual capacity and event conditions available | Rehearse realistic approved event order and transitions, balance fatigue and strength work, monitor total time and technique | All required event minima and composite supported by *valid practice data*, or recorded weaknesses trigger more development |
| **Above-minimum / sustainable performance** | Multiple valid event passes or strong specific benchmarks | Build buffers, optional official high category or user-selected ambitious capability; maintain hypertrophy as preferred goal; minimize needless fatigue and wasted gym time | User controls which abilities to prioritize; guard against chasing scores at expense of appropriate health and recovery |

No fixed number of weeks, mile percentage progression, universal ruck starting weight or forced failure training emerges from this research; coach-reviewed quantitative guidance may be proposed **separately**. If a user's available time or relevant equipment cannot sustain both hypertrophy and all selected event goals, show **tradeoffs / infeasibility** rather than silently overtrain or fake a projection.

## 6. Original example acceptance scenarios for later isolated tests

| Case | Required program behavior; no code yet |
| --- | --- |
| **Army noncombat** | User selects verified 2026 AFT general; 3RM deadlift, pushups, SDC, plank, 2mi; 300 aggregate and every 60 required. A large composite cannot hide a pushup failure. |
| **Army CFT combat** | AFT 350 in 21 designated MOS and **additional** CFT where in 24 approved occupational set; continuous <=30min 7 tasks; future Apr 2027 record date; don't merge 1RM, 3RM or CFT times. |
| **Marine combat** | Adult Marine gets specific combat PMOS male-age-normed PFT ≥210 and separate Marine CFT. A noncombat Marine uses different chart; OCS induction is a separate standard. |
| **Navy general vs Navy combat** | PRT age/sex modality; Navy combat CFT 800m fins, weighted calisthenics/run, each pass; candidate PST not interchangeable. Swimming practice requires supervision when inexperienced. |
| **Air Force** | New July 2026 2mi/HAMR and 50/20/15/15 distribution; strength/core/cardio conditions plus scored WHtR; reserve annual differs from active biannual and Special Warfare charts differ. |
| **Space Force** | Two HPAs annually including at least one 2mi; body composition separate; *numeric score unavailable* until current official 2026 SPFMAN and charts verified; never score using Sept 2025 80/60 retrospectively as current. |
| **Coast Guard** | Run/row/swim options, pushups/plank, >=45 each; if full SharePoint scoring missing, indicate inability to calculate overall official 1–7 scale; AST CFT separate; current October BCS screening not substituted by boat-crew PFT. |
| **Hybrid time constraint** | Three-day hypertrophy preference plus two possible conditioning periods; if hard weekly cap can't fit sufficient strength/conditioning and progression, surface deficit and ask user to prioritize, don't use unsafe cumulative dose or fabricated promise of "both maximized". |
| **Low readiness / pain** | No first-session full loaded CFT/ruck or unsupervised swim test; no diagnostic injury probability; user can stop, select safer options and seek proper assessment. |
| **Real user privacy/source rights** | Self-reported results never displayed as official military qualification; neither public LMS nor app distributes distribution-restricted source manuals; production DB untouched. |

## 7. Scoped development pathway and open approvals

**Right now:** research outcomes added to **draft PR #84 only**. **M4-C1 Issue #85** continues independent hypertrophy Full Body planner and calibrated weight evidence; no scope expansion, deployment or full systematic research prerequisites inserted.

**Future bounded package M4-TAC-0:** verify remaining official score charts and occupational exceptions; define versioned `MilitaryStandard` registry, `FitnessAttempt` raw evidence, `ReadinessMargin` per-event, source-qualified score engine in *offline research fixtures*, no live user fitness program changes. Provide a review of rights and official scoring authority. Do not start until owner approves the package.

**Future M4-TAC-1:** user-consented Tactical / Hybrid profile, separate conditioning modalities and time/fatigue ledger, event-aware training policy with vetted ranges, realistic calendar integration, exercise/score reason trace and negative regression across Authored/Customized, isolated testing.

**Future RESP validation:** prospective outcomes at each test domain; time efficiency, adherence, objective scored event change, injuries/adverse events, and user priorities; do not declare optimality from aggregate benchmark wins, e1RM or invented physiology confidence.

**Scientific decisions for named expert review:** how to personalize graded run/swim training exposure and intensity; aerobic interval and multi-joint workload schedules; task-specific weighted practice safety; strength-endurance volume; combined-training priority/time tradeoffs; cutoffs for unfamiliar/supervised skills; meaning of high performance and expected injury risks. **Explicit owner authorization, acceptance and implementation PR required before activation.**

**Summary:** the app should help users work toward and exceed *applicable physical test minima* while retaining personalized muscle-development goals. It cannot guarantee passage, certify official status, bypass medical entrance rules or promise full military occupational performance from gym logs alone.
