# Product contract

Date: 2026-09-28. Status: **Draft for review**. Mode requirements below carry forward the owner's instructions; their inclusion does not manufacture acceptance of this document or its proposed technical mechanisms. Current-state observations use audited revision `df9965232ce731f8234d222acc526a90bc6be620` and the [audit](../../../Hypertrophy-Audit-2026-09-28.md).

## Product purpose and mode authority

The app helps a person execute an authored training program faithfully or explicitly choose deterministic program customization. Both modes can provide load coaching, explain recommendations and respect declared safety constraints. Their permissions differ.

| Dimension | Authored Plan | Customize My Workout |
|---|---|---|
| Program-design authority | Authored source governs the prescription. | Explicit user selection grants design authority within declared constraints. |
| Exercises and dose | Preserve source exercise slots, working sets, reps, effort targets, intensity techniques and permitted choices. | May optimize exercises, volume, frequency, split and other programming variables. |
| Order and structure | Preserve meaningful sequencing, pairs/primers and program/block relationships. | May design relationships and progression within its own declared lifecycle. |
| Scheduling | Place workouts on the user's actual selected dates; allow lossless redistribution. | Allocate the chosen design to actual dates under its constraints. |
| Adaptive coaching | May recommend working-load changes without rewriting the source prescription. | May recommend changes within customization permissions. |
| Effectiveness analysis | Advisory; no automatic program redesign. | Explainable recommendations, with user override and bounded authority. |

`manual` versus `auto` program selection concerns selection convenience. Neither grants customization consent. A generated program must never overwrite, replace, modify or reinterpret an authored template. Authored Full Body Phase 1 and Phase 2 remain distinct programs, separately governed by their sources.

## Authored execution invariants

Every admitted source slot must remain represented in execution unless a recorded source-defined choice selects an allowed alternative. Preserve AMRAP, set-specific targets and other nonnumeric prescriptions rather than coercing or dropping them. Preserve source program/version lineage so an importer update does not silently revise existing history.

Actual workout dates are user-selected distinct local dates, not merely a weekday count or consecutive offsets. Placement and redistribution may change grouping to fit those dates; they must preserve the complete source dose and meaningful relationships. A shorter schedule is not permission to prune sets, inflate minimum sets, add generic weak-point bonuses or promise equivalent results. Show workload and feasibility implications honestly.

Safety and equipment constraints may make a source slot impossible. Return an explicit unresolved slot, a source-permitted alternative, or infeasibility. Identify the affected slot and constraint. The conflict never grants authority to change unrelated exercises, dose or progression. Do not pressure a user to perform an unsafe prescription to satisfy a fidelity check.

Adaptive coaching may advise working-load changes using qualified performed evidence. It must preserve authored reps, effort targets and intensity techniques. A recommendation is distinguishable from a completed set, a plan revision and a user override.

Concrete acceptance examples:

- Selecting Tuesday, Friday and Sunday produces those dates and preserves every required source slot and set. If relationship-preserving allocation cannot fit, the result explains infeasibility rather than silently dropping work.
- A restriction affecting one authored squat slot produces a scoped conflict or source-permitted alternative; it does not add shoulder volume or rewrite unrelated rep targets.
- A Phase 2 AMRAP push-up prescription is represented as AMRAP with its working sets. Its nonnumeric target is never a reason for importer omission.
- Accepting load advice changes the recommended working load; it does not transform the authored exercise into a generated prescription.

## Customized execution invariants

Customization begins with explicit selection of Customize My Workout and clear permissions. Raw onboarding answers must first map to deterministic `GenerationProfile`; generation consumes that normalized profile, not raw answers. Trace active controls, compatibility defaults, ignored or unsupported fields and their origins.

Given the same qualified inputs, versions and explicit context, planning decisions are reproducible and inspectable. No runtime LLM inference may decide core planning outcomes. Preserve useful existing decision modules and offline compiled knowledge boundaries.

A customized output must satisfy declared hard constraints or return visible infeasibility. Soft preferences cannot override safety or hard constraints. Any reduced plan or fallback must identify what changed and why; no hidden replay of an authored scaffold as supposedly original generation. The existing Full Body v1 boundary remains until an explicitly accepted change expands it. Metadata scoring remains frozen until separately qualified and activated; current accounting does not authorize that activation.

The proposed consent mechanism is a visible mode transition, permission summary and plan preview/change summary, with recorded consent and preserved prior history. Its storage schema and migration are future decisions. This draft does not authorize converting existing users to Customized or retroactively inferring consent.

## History, evidence and honest recommendations

Unknown effort stays unknown. Do not invent historical RPE, load, session dates or workout identity. Ambiguous legacy records may require an explicit unresolved mapping. Corrected and undone records must stop influencing future derived recommendations; implementation of identities, retries and reconstruction belongs to the planned history contract.

Use actual performed data only where units, exercise comparability, load semantics and exposure completeness permit comparison. Assistance, unilateral and machine loads require explicit meanings. Missing or incomparable evidence produces hold/monitor/abstention with a reason, rather than unwarranted confidence.

Set counts describe recorded or planned work; they do not measure muscle growth. Observational performance associations do not prove optimal programming or causal improvement. Separate deterministic software correctness from evidence that a recommendation improves outcomes. Disclose sample sufficiency, uncertainty, confounders and the scope of conclusions.

Recommendations remain explainable and overridable. Advice and its acceptance/decline/edit outcome should be traceable without rewriting performed history. Personal-response optimization, causal claims and broad split expansion require later qualification; they are not current capabilities established by this contract.

## Current deviations and acceptance boundary

The audit found Phase 1 source parity for tested fields, but Phase 2 lost five AMRAP rows; unrestricted redistribution matched prescription multisets without certifying order. Restriction handling, shared live rep guidance, count-based scheduling and cross-week history identity have documented deviations. These findings prioritize work; they do not redefine the owner's intended behavior.

The [roadmap](../roadmap/milestones.md) assigns fidelity, load, actual-date scheduling, advice and customization gates. The future requirements catalog will preserve audit section 12 requests and section 23 proposals separately. No historic checkmark, passing subset or draft statement qualifies the whole product.

The [constitution](../governance/constitution.md) proposes how this contract will govern implementation once integrated and accepted. Until then, existing repository guardrails remain active and any conflict must be recorded rather than silently resolved by changing runtime behavior.
