# Gold Path Tier 4A with Path-Scoped Sovereignty

Last assessed: 2026-03-16

## Purpose

This document defines the next concrete milestone for the repo:

**Gold Path Tier 4A with Path-Scoped Sovereignty**

This milestone is path-specific.

It does not imply repo-wide sovereignty.

## Milestone Definition

The gold path reaches Tier 4A with path-scoped sovereignty only when all requirements below are satisfied for the gold path specifically.

## Required Conditions

### 1. No Gold-Path Authority in `intelligence.py` — SUBSTANTIALLY MET

For gold-path flows:

- `intelligence.py` may not contain real coaching authority
- it may normalize, adapt, and forward
- it may not change coaching meaning

Status: `intelligence.py` retains only compatibility wrappers for workout, weekly-review, coach-preview, frequency-adaptation, and program-recommendation families. All real authority lives in dedicated `decision_*.py` modules. Remaining risk: compatibility-hub drift if wrappers accumulate unchecked.

### 2. Preview / Apply Unification — SUBSTANTIALLY MET

For the gold path:

- preview and apply must be unified enough that they do not create path-level split-brain
- they must share the same decision-family authority model
- they must share compatible trace semantics

Status: Coach-preview and coach-apply share `decision_coach_preview.py` authority. Frequency-adaptation preview/apply share `decision_frequency_adaptation.py`. Trace semantics are compatible.

### 3. Structural Fidelity Gap List Is Current — MET

The gold path must have a current, branch-accurate structural fidelity gap list that tracks:

- authored week structure
- day roles
- exercise lineup
- sequence state
- post-sequence behavior

Status: Gold sample covers 5-day authored source (Full Body #1-#4 + Arms & Weak Points), 10-week mesocycle, day roles, post-sequence `phase_transition_pending` behavior. Tracked in `Master_Plan_Checkmark_Audit.md`.

### 4. Doctrinal Fidelity Gap List Is Current — PARTIAL

The gold path must have a current, branch-accurate doctrinal fidelity gap list that tracks:

- effort model
- Early Set / Last Set semantics
- intensity-technique semantics
- weak-point doctrine
- progression meaning
- compression philosophy

Status: Weak-point doctrine, progression meaning, and compression philosophy are verified. Effort model (RPE/RIR), Early/Last Set semantics, and intensity-technique semantics have rule-set foundations but lack focused behavioral verification tests. See `docs/audits/2026-03-12-tier4a-doctrinal-fidelity-gaps.md`.

### 5. Explanation Classification Is Implemented — NOT MET

Gold-path surfaces must classify user-visible explanation-like text as:

- authoritative rationale
- descriptive summary
- generic fallback

No ambiguous explanation text is allowed on first-class gold-path surfaces.

Status: Decision traces carry structured rationale, but UI surfaces do not yet systematically classify explanation text into these three tiers.

### 6. Valid Decision Traces — SUBSTANTIALLY MET

Gold-path authoritative coaching decisions must emit valid and sufficiently complete traces.

Trace completeness must be strong enough to audit:

- which canonical inputs mattered
- which owner family acted
- which execution steps transformed the outcome
- why the outcome happened

Status: All gold-path decision families emit structured `decision_trace` with version, steps, and reason codes. Coverage is strong for generation, progression, weekly-review, and coach-preview. Workout log-set traces exist but depth varies.

### 7. No Semantically Insufficient Artifacts — PARTIAL

No semantically insufficient artifact may drive a first-class gold-path claim.

If an artifact is structurally valid but doctrinally insufficient for the visible behavior it drives, the gold path cannot reach Tier 4A.

Status: Gold program template and rule set are doctrinally grounded. Schema validation tests enforce structural correctness. Remaining gap: some rule-set entries lack provenance links to specific source sections.

### 8. Felt Behavior Audit — NOT YET VERIFIED

The gold path must pass a felt-behavior audit confirming that:

- it feels like a coach, not a planner
- explanations match visible behavior
- substitutions feel stimulus-preserving
- progression and deload behavior feel justified
- compression preserves intent rather than merely compressing volume

Status: API-level behavior is verified through focused tests. Real-use felt-behavior audit requires actual training cycles (Phase 3 dogfooding). Initial audit at `docs/audits/2026-03-12-tier4a-felt-behavior-audit.md`.

### 9. Correct Bounded-Trust Labeling — PARTIAL

The gold path must be described with bounded-trust language appropriate to Tier 4A.

That labeling must be reflected in:

- docs
- status reports
- test names where relevant
- product or feature descriptions

Status: Docs and roadmap use bounded-trust language. Test names use `gold` prefix convention. UI surfaces do not yet carry explicit trust-tier labels.

### 10. No Shadow Authority — SUBSTANTIALLY MET

The gold path may not contain any shadow-authority seam that changes outcomes or user understanding.

That includes:

- hidden authority in `intelligence.py`
- scheduler-local doctrine invention
- UI humanization that sounds causal without trace support
- summary text that implies rationale without rationale

Status: Decision-family decomposition has removed coaching authority from `intelligence.py`. Scheduler consumes canonical rules. UI humanization risk remains in descriptive text on workout/review surfaces but is bounded by trace-backed data.

## What This Milestone Allows

If all requirements above are met, the milestone allows:

- serious internal use of the gold path
- honest statement that the gold path is the strongest validated coaching path in the repo
- internal dogfood under bounded trust
- Tier 4A classification for the gold path

## What This Milestone Does Not Allow

This milestone does not allow:

- repo-wide sovereignty claims
- equal promotion of non-gold programs
- product-wide "serious hypertrophy coach" language
- global-trust claims for the repo
- hiding remaining doctrinal gaps behind structural fidelity or polished presentation

## Success Standard

The gold path is Tier 4A only when it is:

- path-scoped sovereign enough for serious internal use
- structurally strong
- doctrinally sufficient for bounded gold-path claims
- explanation-clean
- trace-auditable
- free of semantically insufficient first-class behavior

