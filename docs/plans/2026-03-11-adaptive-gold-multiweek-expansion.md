# Adaptive Gold Multi-Week Expansion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Preserve authored multi-week doctrine for the adaptive-gold runtime path and prove week-to-week generation plus weak-point preservation across that authored structure.

**Architecture:** Keep adaptive-gold as a loader-adapted runtime template, but preserve authored week variants in the canonical template payload instead of collapsing to the first week. Then use existing `prior_generated_weeks` runtime state in generation/scheduler to select the correct authored week before day compression, time-budget capping, and substitution logic run.

**Tech Stack:** FastAPI API tests, Python loader/generation/scheduler logic, Pydantic template contracts, pytest with SQLite temp DBs.

---

### Task 1: Write failing tests for adaptive-gold authored week preservation

**Files:**
- Modify: `apps/api/tests/test_program_loader.py`
- Modify: `apps/api/tests/test_program_catalog_and_selection.py`

**Steps:**
1. Add a loader test asserting adaptive-gold exposes authored week variants, not only the first week.
2. Add an API test asserting a second generated week selects authored week 2 instead of repeating week 1.
3. Add an API test asserting week 2 still preserves weak-point structure under constrained time/frequency.
4. Run the focused tests and confirm they fail for the expected reason.

### Task 2: Preserve authored weeks through loader/runtime and select them in generate-week

**Files:**
- Modify: `apps/api/app/template_schema.py`
- Modify: `apps/api/app/program_loader.py`
- Modify: `packages/core-engine/core_engine/generation.py`
- Modify: `packages/core-engine/core_engine/scheduler.py`

**Steps:**
1. Add canonical template support for authored week variants.
2. Adapt adaptive-gold loader output to preserve all authored weeks from the first phase.
3. Use `prior_generated_weeks` to select the authored week before session/day compression.
4. Keep existing weak-point preservation, substitution, and SFR logic operating on the selected week only.
5. Run focused tests until green.

### Task 3: Expand adaptive-gold authored doctrine to a second week

**Files:**
- Modify: `programs/gold/adaptive_full_body_gold_v0_1.json`

**Steps:**
1. Author a distinct week 2 in the same phase with deterministic but modest changes.
2. Keep ids, slot roles, and canonical exercise metadata stable so current runtime logic still applies.
3. Ensure week 2 is meaningfully different enough for loader/API assertions.

### Task 4: Update evidence docs and verify

**Files:**
- Modify: `docs/GPT5_MINI_HANDOFF.md`
- Modify: `docs/GPT5_MINI_EXECUTION_BACKLOG.md`
- Modify: `docs/Master_Plan_Checkmark_Audit.md`
- Modify: `docs/CODEX_5_3_PASSOFF_PROMPT.md`

**Steps:**
1. Record multi-week authored doctrine support and week-selection proof.
2. Record any constraint-preservation proof that now spans week 2 as well as week 1.
3. Run focused verification commands and remove temp SQLite files.
