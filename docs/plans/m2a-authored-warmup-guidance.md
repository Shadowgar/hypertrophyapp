# M2A-2 authored warm-up guidance

Status: implemented candidate 2026-10-13; local qualification checkpoint and independent source reviews recorded in [evidence](../evidence/2026-10-13-m2a-authored-warmups.md). Broader API/GitHub qualification and owner PR review remain separate. No deployment/merge. Base 0a5151988a3e4e639c336db2388b46c871c0450f. Branch m2a/authored-warmup-guidance.

## Scope and authority

LOAD-008; source/execution/load contracts govern. Preserve source exercise/count/reps/effort/rest/technique/order/relationships. No invented warm-ups for absent/zero (including 0.0), no numeric parsing of textual/range counts. Preserve visible raw text and source protocol. No new hypertrophy policy, source artifacts, migration, generated policy, issue #80 optimization or live operations.

Existing duplicate paths: core warmups.compute_warmups (60%; 50/70%; 45/65/85%, floor/minimum kg) and browser oneRepMax.warmupsFromWorkingWeightLb (45/65/82/90%, pound minimum, dedup). Authored decision_workout_session currently returns empty warmups; Today displays raw count. Source onboarding artifacts for both phases explicitly supply the core percentage ladders and rep ranges. New authored runtime authority belongs to core_engine.authored_warmups; legacy Generated calculations stay outside this slice and may not feed Authored.

## Shared interface

Pure function build_authored_warmup_guidance(*, exercise, working_decision, load_context, program_id, source_protocol) returns dict:
version=authored-warmup-v1; source_count (raw string or null); count (exact nonnegative integer or null); status (none/manual/suggested); source_instructions (string); sets (list of {set_index, suggested_weight: canonical kg or null, reps_min: int or null, reps_max: int or null, percent: number or null}); reason_codes; explanation; equipment_feasibility; decision_trace.

source_protocol is existing compiled onboarding warm_up_protocol. Rules must match the source protocol before numeric ladder interpretation; preserve source text and its digest/provenance. Suggested loads require M2A-1 prefill_available and positive recommended_weight, a declared increment with kg/lb unit and supported load basis. No compatibility-increment fallback for warm-ups. Reuse M2A-1 attainable-grid semantics anchored on the qualified working weight; do not invent zero-origin equipment or plate inventory. Loads must be positive and below working load; otherwise manual. Keep per-hand/total/machine basis distinct; machine requires equipment_key. AMRAP/bodyweight/assistance/hard load instruction or unknown variant evidence abstains. Never turn a source count > supported source ladder into fewer sets. Do not mutate inputs.

API returns this as load_intelligence.warmup_guidance, constructed inside existing project_authored_load_feedback (no extra history traversal; #80 stays untouched). Offer next_exposure-qualified baseline only (no source/planned or UI Epley fallback). Source protocol resolved by program_id from compiled onboarding artifact. Existing schemas/envelope dict support additive field. Keep advice identity/evidence invalidation traceable. Warm-up receipts use set_kind=warmup, positive independent ordinal, parent_set_index null and technique null. Zero/absent source rejects new warm-up commands; numeric known count enforces bounds; textual count allows manually recorded actual work without claiming prescribed count. Exact historical retries must return before new validation. Capture warm-up offered load/trace separately without claiming working-load override or using it as exposure evidence.

Today shows source instructions, rows or textual manual logger, qualified canonical load or empty manual input, editable actual reps/load and optional RPE. No working-control counter increment from warm-ups. Existing receipt correction/undo UI must identify warm-up separately. Canonical kg persists unchanged on untouched/restored rounded lb display. New logical receipt after ACK resets drafts; ambiguous retries preserve full immutable payload; refreshed guidance cannot overwrite edited/pending draft. Confirmed variants invalidate source advice. No extra screen/modal step. All zero/absent states preserve source text and offer no fabricated rows.

## Tasks

1. Core owner + red/green tests: authored_warmups.py and test_authored_warmups.py only. Source zero/text/numeric fidelity; approved ladder; unknown, AMRAP/bodyweight/assistance, per-hand/machine, increments, deterministic trace/no mutation, source-protocol mismatch. Commit task.
2. API adapter/receipt provenance + isolated tests: workout_load_state.py, workout_authored.py and tests. Add compiled source protocol adapter and envelope; validate warm-up kinds/counts; preserve replay/correction. PostgreSQL covers persistence, immutable retry/void, concurrent same warm-up, working overlap and reconstruction. No schema migration. Commit task.
3. Web presentation/logger + tests: Today, dedicated compact warm-up component, API types. Consume only server guidance; do not compute authored ladder in JS. Test exact canonical load, pending retry, count/work isolation, zero/text/manual, substitution, correction/undo and mobile. Commit task.
4. Integration: focused suites; isolated PG upgrade to existing0022 and synthetic browser fixtures; desktop/mobile real API logging. Broader applicable core/API/web/types/lint/build/docs once final stable source, baseline comparison. Final correctness/security review, PR push and GitHub CI/Codex loop. No auto-merge. Record evidence and stop for owner review.

## Verification environment

Only /tmp/hypertrophy-m2a-warmup and /tmp/hypertrophy-m2a2-qualification are writable task workspaces. Cleared test environment, explicit disposable SQLite files or isolated PostgreSQL loopback target; never inherit production env/compose defaults. Existing 4 core/8 API/1 web baseline is retained. Raw artifacts/tokens private outside Git; sanitized evidence in docs/evidence. Preserve production main, configuration, data/services and tracked log.
