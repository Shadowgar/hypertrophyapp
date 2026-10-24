# Product contract

Date: 2026-09-28. Status: **Direction approved by owner on 2026-09-28, subject to this review’s corrections; technical mechanisms remain Proposed**. The deterministic-runtime requirement is explicitly owner-approved on 2026-09-28. Approval of desired behavior is separate from implementation, verification and owner acceptance of a release. Current-state observations use audited revision `df9965232ce731f8234d222acc526a90bc6be620` and the [audit](../evidence/README.md#audit-reference-and-migration-plan).

## Product purpose and mode authority

The app helps a person execute an authored training program faithfully or explicitly choose deterministic program customization. Both modes can provide load coaching, explain recommendations and respect declared safety constraints. Their permissions differ.

| Dimension | Authored Plan | Customize My Workout |
|---|---|---|
| Program-design authority | Authored source governs the prescription. | Explicit user selection grants design authority within declared constraints. |
| Exercises and dose | Preserve source exercise slots, working sets, reps, effort targets, intensity techniques and permitted choices. | May optimize exercises, volume, frequency, split and other programming variables. |
| Order and structure | Preserve meaningful sequencing, pairs/primers and program/block relationships. | May design relationships and progression within its own declared lifecycle. |
| Scheduling | Place workouts on the user's actual selected dates; allow lossless redistribution. | Allocate the chosen design to actual dates under its constraints. |
| Adaptive coaching | May automatically calculate and prefill the next working load; user override remains available. Source prescription stays fixed. | May recommend changes within customization permissions. |
| Effectiveness analysis | Advisory; no automatic program redesign. | Explainable recommendations, with user override and bounded authority. |

`manual` versus `auto` program selection concerns selection convenience. Neither grants customization consent. A generated program must never overwrite, replace, modify or reinterpret an authored template. Authored Full Body Phase 1 and Phase 2 remain distinct programs, separately governed by their sources.

## Authored execution invariants

Every admitted source slot must remain represented in execution unless a recorded source-defined choice selects an allowed alternative. Preserve AMRAP, set-specific targets and other nonnumeric prescriptions rather than coercing or dropping them. Preserve source program/version lineage so an importer update does not silently revise existing history.

Actual workout dates are user-selected distinct local dates, not merely a weekday count or consecutive offsets. Placement and redistribution may change grouping to fit those dates; they must preserve the complete source dose and meaningful relationships. A shorter schedule is not permission to prune sets, inflate minimum sets, add generic weak-point bonuses or promise equivalent results. Show workload and feasibility implications honestly.

Equipment, safety, pain or another constraint may make a source slot impossible. Identify the slot, offer a source-authored/source-approved substitute when available and explain the reason. Require explicit user confirmation before changing the performed exercise. Preserve the original source slot identity and record the confirmed performed variant and consent; never silently replace an exercise. Without a permitted alternative, retain an unresolved/infeasible slot. The conflict grants no authority over unrelated exercises, sets, reps, RPE/RIR or volume. Do not pressure unsafe execution to satisfy fidelity.

The eventual Authored load coach may automatically calculate and prefill an increased, held or decreased working load for the next comparable exposure, using qualified performed evidence. It exposes the reason/evidence and allows override; the user need not do session-by-session arithmetic. `monitor` explicitly describes insufficient or uncertain evidence and need not prefill a newly inferred load. This authority applies only to working load, never automatic exercise, working-set, rep-range, RPE/RIR, intensity-technique or progression/block changes. A calculated load, a performed set, a plan revision and a user override remain distinct. See the [load contract](../contracts/load-progression.md).

Concrete acceptance examples:

- Selecting Tuesday, Friday and Sunday produces those dates and preserves every required source slot and set. If relationship-preserving allocation cannot fit, the result explains infeasibility rather than silently dropping work.
- A restriction affecting an authored squat slot offers a source-approved alternative with a reason and awaits confirmation. Declining leaves the slot unresolved; it does not add shoulder volume or rewrite unrelated rep targets.
- A Phase 2 AMRAP push-up prescription is represented as AMRAP with its working sets. Its nonnumeric target is never a reason for importer omission.
- A qualified next-exposure load is calculated and prefilled automatically; the user may override it. Authored sets/reps/effort remain unchanged.

## Customized execution invariants

Customization begins with explicit selection of Customize My Workout and clear permissions. Raw onboarding answers must first map to deterministic `GenerationProfile`; generation consumes that normalized profile, not raw answers. Trace active controls, compatibility defaults, ignored or unsupported fields and their origins.

Given the same qualified inputs, versions and explicit context, planning decisions are reproducible and inspectable. Owner-approved requirement (2026-09-28): core workout and program decisions remain deterministic and auditable. AI/LLMs may explain, converse, research, summarize, analyze and assist development, but may not directly determine runtime training prescriptions. Explanation or analysis cannot bypass the deterministic decision layer. Detailed boundaries are proposed in [ADR-004](../adr/0004-deterministic-runtime-and-ai-boundary.md). Preserve useful existing decision modules and offline compiled knowledge boundaries.

A customized output must satisfy declared hard constraints or return visible infeasibility. Soft preferences cannot override safety or hard constraints. Any reduced plan or fallback must identify what changed and why; no hidden replay of an authored scaffold as supposedly original generation. The existing Full Body v1 boundary remains until an explicitly accepted change expands it. Metadata scoring remains frozen until separately qualified and activated; current accounting does not authorize that activation.

The proposed consent mechanism is a visible mode transition, permission summary and plan preview/change summary, with recorded consent and preserved prior history. Its storage schema and migration are future decisions. This draft does not authorize converting existing users to Customized or retroactively inferring consent.

## History, evidence and honest recommendations

Unknown effort stays unknown. Do not invent historical RPE, load, session dates or workout identity. Ambiguous legacy records may require an explicit unresolved mapping. Corrected and undone records must stop influencing future derived recommendations; identity, retries and reconstruction are proposed in [ADR-005](../adr/0005-training-history-identity-and-correction.md) and the [execution contract](../contracts/execution-plan.md).

Use actual performed data only where units, exercise comparability, load semantics and exposure completeness permit comparison. Assistance, unilateral and machine loads require explicit meanings. Missing or incomparable evidence produces monitor/abstention with a reason; a clearly labeled known baseline may remain without claiming new progression evidence. A qualified hold is distinct from insufficiency.

Set counts describe recorded or planned work; they do not measure muscle growth. Observational performance associations do not prove optimal programming or causal improvement. Separate deterministic software correctness from evidence that a recommendation improves outcomes. Disclose sample sufficiency, uncertainty, confounders and the scope of conclusions.

Recommendations remain explainable and overridable. Advice and its acceptance/decline/edit outcome should be traceable without rewriting performed history. Personal-response optimization, causal claims and broad split expansion require later qualification; they are not current capabilities established by this contract.

## Current deviations and acceptance boundary

The audit found Phase 1 source parity for tested fields, but Phase 2 lost five AMRAP rows; unrestricted redistribution matched prescription multisets without certifying order. Restriction handling, shared live rep guidance, count-based scheduling and cross-week history identity have documented deviations. These findings prioritize work; they do not redefine the owner's intended behavior.

The [roadmap](../roadmap/milestones.md) assigns fidelity and parallel M2A load/M2B actual-date tracks, followed by advice and customization gates. M2B initially selects current-week dates manually, without external calendar integration. The [catalog](catalog.md) preserves audit section 12 requests and section 23 proposals separately; [traceability](traceability.md) distinguishes existing checks from missing qualification. No historic checkmark, passing subset or draft statement qualifies the whole product.

The [constitution](../governance/constitution.md) proposes how this contract will govern implementation once integrated and accepted. Until then, existing repository guardrails remain active and any conflict must be recorded rather than silently resolved by changing runtime behavior.

## 2026-10-21 first-party personal product approval

**Owner-approved additional product direction**, not an implementation, algorithm/threshold approval or release acceptance: WorkoutApp is one first-party training application built around the owner's actual goals, completed work, limited training time, rotating schedule, equipment, recovery context and performance outcomes. The approved [personal requirement supplement](personal-workoutapp-2026-10-21.md) contains PERS-001–PERS-020 and the [existing roadmap crosswalk](../roadmap/personal-capability-crosswalk-2026-10-21.md) shows placement without creating new milestones.

The owner expressly **rejects third-party fitness/health app, exporter, logger and coaching API integrations** (including suggested Hevy, Motra, Athlytic, Training Today or intermediary Health sync). The only accepted fitness-data/platform path is direct Apple Health XML import in WorkoutApp and, later if separately designed/approved, first-party WorkoutApp iOS/watchOS capabilities using Apple's native HealthKit/Watch APIs. Imported data remains optional, scope-limited and secondary to effective performed WorkoutApp logs. Browser-based WorkoutApp has no direct native HealthKit access. An external AI coaching/inference SaaS is not an implied exception; deterministic runtime decision authority and D-005 remain in force. Standard existing infrastructure is not permission to add new external training-data or coaching dependencies.

Approved goals include low-friction and reliable exercise execution; actual shift/daytime-sleep-aware scheduling; realistic personal time estimates and interruptions; exercise/machine/increment/setup memory; comparable-evidence load progression with optional 1RM calibration, effort and pain/technique context; evidence-aware recovery; selected conditioning/occupational benchmarks; optional body/nutrition trends; transparent analytics; recommendation outcome tracking and cautious personal-response learning; and evidence-linked conversational explanation. **No per-muscle recovery measurement, biological age, precise growth score or causally proven optimality is implied.**

These priorities never waive source-preserving Authored dose, explicit Customized consent/preview, data sufficiency, unknown-data handling, corrections/undo fidelity, preserved history or separate qualification/owner deployment authorization. The pending final visual review of [PR #108](https://github.com/Shadowgar/hypertrophyapp/pull/108) is not superseded by the owner's approval of feature ideas. [Issue #103](https://github.com/Shadowgar/hypertrophyapp/issues/103) remains an immediate gym-use reliability priority while the broader personal capability work is phased through M0–M6.
