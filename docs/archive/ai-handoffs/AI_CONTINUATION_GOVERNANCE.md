# AI Continuation Governance - Adaptive Coaching Rebuild

Archive status: historical AI-operational guidance only.
Current constitutional authority lives in `docs/architecture/GOVERNANCE_CONSTITUTION.md`.
Current runtime ownership authority lives in `docs/architecture/RUNTIME_AUTHORITY_MAP.md` and `docs/current_state_decision_runtime_map.md`.

Last updated: 2026-03-07

## Purpose

This document exists to keep any AI agent or human contributor from introducing architectural drift.

Read this before implementing new coaching behavior.

## Required Read Order

1. `docs/archive/ai-handoffs/AI_CONTINUATION_GOVERNANCE.md`
2. `docs/Master_Plan.md`
3. `docs/Architecture.md`
4. `docs/process/Working_Agreements.md`
5. `docs/archive/ai-handoffs/GPT5_MINI_EXECUTION_BACKLOG.md`
6. `docs/archive/reviews/EXHAUSTIVE_PROJECT_REVIEW_2026-03-07.md`

## Current Architectural Diagnosis

The repository is not in a failed state where canonical artifacts are decorative only.

Current state:
- canonical rules are partially operational in live runtime paths
- canonical rules are not yet sovereign
- meaningful coaching behavior still exists in routers and helper logic outside one interpreter path

Short version:

`rules are partially operational, but not yet sovereign`

## What Counts As A Meaningful Coaching Decision

The following are meaningful coaching decisions and must not be introduced outside the core decision runtime:
- program recommendation
- frequency adaptation
- workout generation changes driven by readiness/fatigue/adherence
- substitution selection
- progression changes
- deload triggers
- phase transitions
- weak-point volume adjustments

UI formatting, response serialization, and backward-compatible humanization of legacy reason codes are not meaningful coaching decisions.

## What Counts As Canonical Artifacts

A path is canonical only if it uses all required structured inputs for that feature:
- canonical template data
- canonical exercise knowledge
- canonical rules
- interpreter-compatible user state

If any of those are missing, the path is legacy by definition.

## Repository Law

1. No new coaching behavior outside the core-engine decision runtime.
2. Preview and apply must call the same interpreter for the same decision family.
3. Explanations must be emitted from interpreter output, not reconstructed independently in routers or clients.
4. Routers may orchestrate auth, IO, persistence, and response shaping only.
5. Legacy paths may continue temporarily, but they may not gain new coaching behavior.
6. A program is not first-class runtime unless it has canonical artifacts.
7. Every meaningful coaching decision must emit a structured decision trace.

## Decision Trace Minimum Contract

Every meaningful decision trace should contain:
- interpreter identifier and version
- normalized input snapshot relevant to the decision
- ordered rule checks or evaluation steps
- matched rule or fallback path
- final selected outcome
- machine-readable reason code
- human-readable rationale

## Legacy Containment Policy

Legacy runtime paths are technical debt, not valid long-term coexistence.

Legacy paths must be:
- explicitly identified in docs
- blocked from receiving new coaching features
- migrated or deprecated on a tracked schedule

## Current Priority Gap

The project is now constrained more by governance than by UI or API plumbing.

The highest-value remaining work is:
- make one authoritative decision runtime the only source of coaching behavior
- move router-owned heuristics behind interpreter functions in `packages/core-engine`
- require canonical artifacts for all active runtime programs

## Immediate Implementation Order

1. Centralize one decision family at a time in `packages/core-engine`.
2. Emit structured decision traces from that interpreter.
3. Reuse the same interpreter in preview and apply paths.
4. Remove duplicated router-side heuristics for that decision family.
5. Add focused regression tests.
6. Update docs with evidence and remaining legacy boundaries.

## Do Not Do This

Do not:
- add new coaching thresholds directly in API routers
- add explanation-only logic that is not tied to a real decision path
- extend legacy runtime programs with new coaching intelligence
- let canonical docs describe a future architecture that the runtime still bypasses

## Evidence Rule For Future AI Agents

A task is not complete unless the docs show:
- what interpreter now owns the decision
- which legacy path was reduced or removed
- which tests prove the interpreter behavior
- whether the decision now emits a trace
