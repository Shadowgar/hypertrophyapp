# 2026-03-11 Pass 4 Reality Verdict

## Scope note

Requested inputs:

- `docs/audits/2026-03-11-pass1-authority-audit.md`
- `docs/audits/2026-03-11-pass2-trace-explanation-audit.md`
- `docs/audits/2026-03-11-pass3-gold-trust-audit.md`

What actually existed on disk during this pass:

- `docs/audits/2026-03-11-pass1-authority-audit.md`

`pass2` and `pass3` were not present in the repo at audit time, so this pass is grounded in:

- Pass 1 authority findings
- `docs/architecture/GOVERNANCE_CONSTITUTION.md`
- `docs/architecture/RUNTIME_AUTHORITY_MAP.md`
- `docs/architecture/TRUST_AND_MATURITY_MODEL.md`
- direct runtime and UI inspection

This means the verdict below is not blocked, but it is missing any prior written Pass 2 / Pass 3 conclusions that may exist outside this checkout.

## Hallucination / Fake-Intelligence Risk Map

### 1. Generated Week

- What the user sees:
  A polished weekly plan with a command-deck feel: selected program, mesocycle posture, deload framing, coverage radar, session blueprint, candidate stack, and adaptation carryover.
- Why it feels intelligent:
  It looks like a single coherent coaching brain selected the right template, interpreted recovery state, decided deload posture, preserved weak-point intent, and balanced weekly coverage.
- What compiled doctrine/state is genuinely behind it:
  Real canonical state is present: days available, split preference, equipment, soreness/adherence inputs, prior plans, review overlay, progression state per exercise, and SFR-derived state. There is also real deterministic template loading and some real rule-set-backed substitution/progression support.
- What is still partial / fallback / approximate:
  The top-level generated week still has no constitutionally complete authoritative `decision_trace`. Template choice still lives in `intelligence.py` and `generation.py`. `scheduler.py` still invents mesocycle, deload, weak-point continuity, and missed-day doctrine. `rules_runtime.py` still falls back to default doctrine when canonical rule sets are absent.
- What risk that creates:
  This is the highest gold-path hallucination seam. The user experiences one authoritative coach, but the runtime is still a composite of real owner logic plus hidden execution heuristics and doctrine fallback.

### 2. Today Workout

- What the user sees:
  A specific daily workout with session intent, authored block context, deload status, warmups, between-set coaching, live weight/rep recommendations, and a clean resume flow.
- Why it feels intelligent:
  It appears to understand what today is for, where the user is in the block, what to do next set, and when to steer load or substitutions.
- What compiled doctrine/state is genuinely behind it:
  This surface is more real than fake. `decision_workout_session.py` owns much of the selection, state hydration, log-set handling, and response shaping. It uses real session logs, persisted exercise state, current plan state, and rule-runtime support for starting load and repeat-failure substitution.
- What is still partial / fallback / approximate:
  It inherits generated-week meaning from the upstream week payload, so any week-level authority drift contaminates today. Starting-load and substitution logic still allow doctrine fallback when no rule set is present. The UI also wraps everything in strong coaching language whether or not the underlying rationale is fully authoritative.
- What risk that creates:
  The live lane is directionally real, but it can borrow confidence from a week spine that is not yet sovereign. The user may trust today’s context more than the upstream planning authority actually deserves.

### 3. Substitutions

- What the user sees:
  Compatible swap options, automatic equipment substitutions, and repeat-failure substitution suggestions that look aware of recovery and practical constraints.
- Why it feels intelligent:
  It looks like the engine knows exercise equivalence, equipment compatibility, and when an exercise should be changed for stimulus-preservation reasons.
- What compiled doctrine/state is genuinely behind it:
  There is real deterministic machinery here: equipment tags, substitution candidate lists, exercise metadata, persisted under-target exposure counts, and explicit substitution traces from `rules_runtime.py`.
- What is still partial / fallback / approximate:
  When a canonical rule set is missing, substitution strategy and repeat-failure threshold come from hardcoded defaults. Auto-substitution is mostly "first compatible candidate," not true coaching-grade equivalence. `scheduler.py` also adds `substitution_pressure` and `substitution_guidance` using local heuristics rather than doctrine-owner output.
- What risk that creates:
  This can feel smarter than it is. The engine is really doing bounded deterministic filtering, but the user may infer deeper exercise-intelligence and stimulus-equivalence than the runtime can currently justify.

### 4. Progression

- What the user sees:
  Hold/progress/deload outcomes, readiness-aware rationales, and load-scale behavior in preview, log-set follow-up, and review flows.
- Why it feels intelligent:
  The app sounds like it is interpreting performance, fatigue, readiness, soreness, and underperformance in a coaching-like way.
- What compiled doctrine/state is genuinely behind it:
  This is one of the stronger surfaces. `decision_progression.py` is a real owner. It uses deterministic readiness scoring, SFR evaluation, deload-signal evaluation, progression rules, and rule-runtime-backed thresholds. The logic is not fake.
- What is still partial / fallback / approximate:
  If no rule set is linked, progression still uses default percentages, thresholds, and deload cadence. Some reason text is still humanized from codes. Generated-week uses progression-derived state but then reinterprets it inside `scheduler.py`.
- What risk that creates:
  Medium risk, not catastrophic risk. The core progression family is real, but surrounding fallback doctrine and downstream reinterpretation can make it feel more complete than it is.

### 5. Deload

- What the user sees:
  A confident deload posture with reasons, specific set/load reductions, and week-level messaging that suggests the engine knows when recovery demands a pivot.
- Why it feels intelligent:
  The UI presents deload as a coaching judgment, not just a template flag. The reasons look synthesized from adherence, soreness, and mesocycle context.
- What compiled doctrine/state is genuinely behind it:
  There is some real basis: authored deload weeks, progression-family deload logic, weekly-review SFR adjustment logic, and optionally compiled deload rules.
- What is still partial / fallback / approximate:
  The generated-week deload decision is still heavily shaped by `scheduler.py` heuristics: cut-phase trigger shortening, early soreness/adherence triggers, and early SFR recovery trigger logic. The user does not get a constitutionally complete week-level deload trace.
- What risk that creates:
  High risk. Deload currently looks more sovereign than it is. The app can sound like it made a principled coaching call when the active runtime is still partly execution-layer doctrine invention.

### 6. Recommendation

- What the user sees:
  Program recommendation and switch advice with reasons like compatibility, adaptation upgrade, coverage gap, or mesocycle completion.
- Why it feels intelligent:
  It reads like a strategic program-level coach that understands when to stay, rotate, or upgrade the template.
- What compiled doctrine/state is genuinely behind it:
  This surface is meaningfully real. `decision_program_recommendation.py` is the owner, it resolves compatible candidates deterministically, consumes canonical training state, and emits real decision traces and human rationales.
- What is still partial / fallback / approximate:
  Recommendation quality depends on plan-context inputs like mesocycle and coverage, and those are partly sourced from the generated-week path that is still mixed in authority. Some route input defaults also remain fairly permissive.
- What risk that creates:
  Moderate risk. The recommendation family itself is not fake, but it stands on top of some generated-week context that is not yet fully trustworthy.

### 7. Weekly Review

- What the user sees:
  A Sunday review that audits the previous week, assigns readiness, gives global guidance, adjusts next week’s set/load bias, and tags weak-point targets.
- Why it feels intelligent:
  It feels like a coach reviewed the user’s week and translated it into next-week prescriptions.
- What compiled doctrine/state is genuinely behind it:
  This is another strong real surface. `decision_weekly_review.py` summarizes actual planned-versus-performed work, computes exercise faults, interprets nutrition/adherence/readiness state, derives SFR-aware adjustments, and persists a trace-backed adaptive overlay.
- What is still partial / fallback / approximate:
  It is still bounded, not full-spectrum recovery intelligence. Soreness is not richly integrated in the weekly-review decision itself. The doctrine lives in code-owner logic more than in rich external artifacts. The UI still presents this with fairly global-sounding confidence.
- What risk that creates:
  Low-to-moderate risk. This is real deterministic coaching logic in progress, but users could still over-read its breadth if the claims are not qualified.

### 8. History / Analytics

- What the user sees:
  A history dashboard with progression brief, strength lead, bodyweight drift, coach queue, calendar views, recommendation timeline, and a raw analytics snapshot.
- Why it feels intelligent:
  Headlines and summaries imply the system understands training trends, queue pressure, and progression status rather than simply reporting raw logs.
- What compiled doctrine/state is genuinely behind it:
  The underlying data is real: logs, check-ins, measurements, PR detection, calendar aggregation, and persisted recommendation history. `history.py` is doing deterministic summarization over actual user history.
- What is still partial / fallback / approximate:
  Most of this is descriptive analytics, not authoritative coaching explanation. The progression brief and bodyweight/queue summaries are UI-derived synthesis, not trace-backed rationale. This surface has little explicit explanation-law enforcement.
- What risk that creates:
  Moderate risk of faux-intelligence by summary tone. It is not lying about the data, but it can imply causal coaching understanding where the runtime is really doing dashboard summarization.

### 9. Explanation Text

- What the user sees:
  Human-readable reasons across week, today, recommendation, weekly review, coach preview, and history surfaces.
- Why it feels intelligent:
  The prose closes the gap between deterministic rules and "coach-like" experience. It makes the system feel like it understands why outcomes happened.
- What compiled doctrine/state is genuinely behind it:
  Some explanation text is real owner-produced rationale. Some is safely derived from reason codes that do map to real deterministic rules.
- What is still partial / fallback / approximate:
  This is still the biggest fake-intelligence multiplier. `resolveReasonText`, `humanizeCode`, UI copy maps, and panel labels routinely humanize codes or fill semantic gaps without strong authoritative/fallback labeling. The product still does not rigorously separate authoritative rationale from descriptive summary from generic fallback.
- What risk that creates:
  Very high risk. Even when the engine is behaving deterministically, the explanation layer can counterfeit a depth and coherence the runtime has not fully earned.

### 10. Gold Path Overall

- What the user sees:
  A full loop that looks like a deterministic hypertrophy coach: generate week, run today, adjust within session, review the week, carry adaptations forward, and recommend program changes when needed.
- Why it feels intelligent:
  The pieces line up well enough in UI and flow that the user experiences one integrated coaching system rather than separate bounded modules.
- What compiled doctrine/state is genuinely behind it:
  There is a real engine here: compiled program structure, canonical user state, persisted exercise state, weekly review overlays, progression and recommendation owners, deterministic routing, and usable traces in several families.
- What is still partial / fallback / approximate:
  The gold path still rides through a non-sovereign generated-week spine. The week path is missing full authoritative trace completeness, still contains shadow authority, and still permits doctrine fallback where the constitution says first-class paths should not bluff.
- What risk that creates:
  The overall gold path currently feels one tier more mature than it is. The repo can internally look like Tier 4A behavior while still being constitutionally closer to a strong Tier 3 / early Tier 4A candidate.

## Overall Reality Verdict

### Final verdict

Architecturally fragmented despite good docs.

The architecture documents are directionally right, and several families really have moved into proper owners. But the gold-path spine is still fragmented in the exact places that matter most for trust:

- generated week still lacks complete authoritative trace
- template selection still leaks through `intelligence.py` and `generation.py`
- `scheduler.py` still invents coaching meaning
- `rules_runtime.py` still becomes fallback doctrine when canonical rule sets are missing
- explanation text still overstates coherence

So the docs are not fake. The repo-wide runtime still does not fully live up to them.

### Authority estimate

Rough estimate across the audited user-facing surfaces:

- Authority inside correct owners: `60%`
- Authority outside correct owners: `40%`

Why this split:

- Inside correct owners: progression, weekly review, recommendation, and much of today/log-set logic are now genuinely deterministic and owner-backed.
- Outside correct owners: the generated-week path, deload posture, substitution framing, template selection, and explanation layer still carry too much hidden or weakly-justified authority.

### What this is, honestly

This is a real deterministic coaching engine in progress.

It is not just a polished workout app with zero engine under it.

But the gold path still overstates its intelligence in the user experience because the generated-week authority chain and explanation law are not yet clean enough to support the level of confidence the UI projects.

## Top Fixes Before Internal Dogfood

### 1. Make generated week fully trace-complete and authoritative

- Add one top-level authoritative `decision_trace` for generated week.
- It must answer owner family, canonical inputs, policy basis, execution steps, outcome, reason summary, alternative resolution, and trust scope.
- Stop treating `template_selection_trace` plus `generation_runtime_trace` as if they are an equivalent substitute.

### 2. Move generated-week template selection into a named owner

- Remove live selection authority from `intelligence.py` and `generation.py`.
- Create or assign one explicit decision family for generation template choice.
- Make `generation.py` routing-only and `intelligence.py` harmless forwarding-only on this path.

### 3. Strip doctrine invention out of `scheduler.py`

- Mesocycle and deload meaning must come from doctrine or an owner.
- Weak-point continuity and missed-day policy must come from doctrine or an owner.
- Exercise-level recovery pressure and substitution-pressure framing must not be invented locally by the execution engine.

### 4. Kill silent doctrine fallback on the gold path

- Do not allow gold-path first-class behavior to rely on hardcoded rule defaults when no canonical rule set is present.
- Either require a linked rule set for the gold path or explicitly downgrade trust/claims on any fallback path.
- `rules_runtime.py` should execute doctrine, not become doctrine.

### 5. Enforce explanation law in the product layer

- Label explanation text as authoritative rationale, descriptive summary, or generic fallback.
- Stop UI helpers from manufacturing coach-like rationale when only a code or partial trace exists.
- Downgrade labels like "Coaching Intelligence" and other high-confidence copy until the trace and authority chain actually support them.

## Bottom line

I would not personally dogfood the gold path yet as if it were already Tier 4A-clean.

I would keep pushing it as a serious deterministic coaching engine in progress, but only after the week spine, doctrine ownership, and explanation law are made honest enough that the felt intelligence matches the real authority underneath it.
