"""Pure source-bound Authored warmup guidance; no new training prescription.

The numeric recipes below interpret the existing compiled Phase 1/2 source
instructions only when their instruction digest matches. Working-load evidence
and attainable-grid rounding remain owned by M2A-1 load intelligence. This
owner neither falls back to a planned load nor invents equipment inventory.
"""
from copy import deepcopy
from decimal import Decimal, DecimalException
from datetime import date
import re

from .load_intelligence import decide_initial_working_load, _initial_attainable_weight, _attainable_weight, _context_reasons, _digest, _finite, _numeric_target, _safe_json

VERSION = "authored-warmup-v1"
_AUTHORED_PROGRAMS = {"pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"}
# SHA-256 of the canonical JSON exercise-specific intro and recipe rows in
# both compiled programs/gold/*.onboarding.json artifacts. Every instruction
# rendered for this protocol must be requalified after a source edit.
_SOURCE_EXERCISE_PROTOCOL_DIGEST = "509169b9bc01c78c48d6485e7e7b71389e28538b5861266cc7afd0699efcb358"
_SOURCE_RECIPES = {1: ((60, 6, 10),), 2: ((50, 6, 10), (70, 4, 6)),
    3: ((45, 6, 10), (65, 4, 6), (85, 3, 4))}
_HARD_LOAD_KEYS = ("hard_load_instruction", "hard_load", "source_hard_load", "load_target")
_EXTERNAL_SEMANTICS = {None, "external_load", "external", "total_external", "per_hand", "machine_stack"}


def _source_count(exercise):
    raw = (exercise.get("authored_prescription") or {}).get("raw") or {}
    # A missing raw source cell stays absent; flat compatibility fields cannot
    # establish an authored warmup prescription.
    value = raw.get("warm_up_sets")
    text = None if value is None else str(value)
    if text is None or not text.strip():
        return text, None
    if not isinstance(value, bool) and re.fullmatch(r"[0-9]+(?:\.0+)?", text.strip()):
        try:
            return text, int(text.strip().split(".")[0])
        except ValueError:
            pass  # An unrepresentable count remains unresolved, never truncated.
    return text, None


def _source_instructions(protocol, count, qualified):
    parts = []
    intro = protocol.get("exercise_specific_warm_up_intro")
    if isinstance(intro, str):
        parts.append(intro)
    rows = protocol.get("exercise_specific_warm_up") or []
    if not isinstance(rows, list):
        return "\n".join(parts)
    if qualified and count in _SOURCE_RECIPES:
        rows = [rows[count - 1]]
    for row in rows:
        if isinstance(row, dict):
            parts.extend(row[key] for key in ("label", "instruction") if isinstance(row.get(key), str))
    return "\n".join(parts)


def _exercise_reasons(exercise):
    reasons = []
    prescription = exercise.get("authored_prescription") or {}
    raw = prescription.get("raw") or {}
    sets = prescription.get("sets") or []
    if not sets or any(not isinstance(row, dict)
            or _numeric_target(row.get("rep_target") or {}, "reps") is None for row in sets):
        reasons.append("rep_target_unresolved_or_amrap")
    if not exercise.get("id"):
        reasons.append("performed_variant_identity_unknown")
    if exercise.get("performed_variant"):
        # A confirmed alternative invalidates source advice. A later comparable
        # working-load decision alone does not qualify this warmup source recipe.
        reasons.append("performed_variant_warmup_unqualified")
    if any(exercise.get(key) not in _EXTERNAL_SEMANTICS for key in ("load_semantics", "semantics")):
        reasons.append("load_semantics_unsupported_or_contradictory")
    containers = (exercise, exercise.get("source_lineage") or {}, prescription, raw, *sets)
    if any(isinstance(item, dict) and any(item.get(key) for key in _HARD_LOAD_KEYS) for item in containers):
        reasons.append("source_hard_load_instruction")
    if prescription.get("load_semantics") not in _EXTERNAL_SEMANTICS:
        reasons.append("load_semantics_unsupported_or_contradictory")
    return reasons


def build_authored_warmup_guidance(*, exercise, working_decision, load_context, program_id, source_protocol,
        provisional_decision=None):
    """Return lossless source count/text plus qualified canonical kg suggestions.

    Numeric but unsupported counts and textual counts have no synthetic rows.
    A recognized source recipe retains its rows/reps/percentages when load
    evidence abstains; every suggested_weight is then null for manual entry.
    """
    exercise, working, context, protocol = (deepcopy(value or {}) for value in
        (exercise, working_decision, load_context, source_protocol))
    provisional = deepcopy(provisional_decision or {})
    provisional_used = False
    source_count, count = _source_count(exercise)
    exercise_protocol_digest = _digest({key: protocol.get(key) for key in
        ("exercise_specific_warm_up_intro", "exercise_specific_warm_up")})
    protocol_qualified = exercise_protocol_digest == _SOURCE_EXERCISE_PROTOCOL_DIGEST
    reasons, rows = [], []
    feasibility = {"status": "unknown", "increment": context.get("increment"),
        "increment_unit": context.get("increment_unit"), "limitations": ["No qualified warmup load proposal."]}
    if source_count is None or not source_count.strip() or count == 0:
        status, explanation = "none", "The source lists no exercise-specific warmup sets."
        reasons.append("source_warmup_absent_or_zero")
    elif program_id not in _AUTHORED_PROGRAMS:
        status, explanation = "manual", "No qualified Authored source protocol is available for this program."
        reasons.append("authored_program_unqualified")
    elif count is None:
        status, explanation = "manual", "Follow the source warmup text and record actual work manually."
        reasons.append("source_count_unresolved")
    elif not protocol_qualified:
        status, explanation = "manual", "Follow the supplied source protocol; its numeric recipe is unqualified."
        reasons.append("source_protocol_unqualified")
    elif count not in _SOURCE_RECIPES:
        status, explanation = "manual", "The source count has no qualified numeric warmup ladder."
        reasons.append("source_ladder_unavailable")
    else:
        rows = [{"set_index": index, "suggested_weight": None, "reps_min": reps_min,
            "reps_max": reps_max, "percent": percent}
            for index, (percent, reps_min, reps_max) in enumerate(_SOURCE_RECIPES[count], 1)]
        reasons.extend(_exercise_reasons(exercise))
        reasons.extend(_context_reasons(context))
        for container in (exercise, exercise.get("authored_prescription") or {}, context):
            for key in ("load_semantics", "semantics"):
                semantics = container.get(key)
                if semantics in {"total_external", "per_hand", "machine_stack"} and semantics != context.get("basis"):
                    reasons.append("load_semantics_unsupported_or_contradictory")
        weight = working.get("recommended_weight")
        qualified = (working.get("scope") == "next_exposure" and working.get("prefill_available") is True
            and _finite(weight) and weight > 0)
        if not qualified and provisional.get("status") == "provisional":
            # Re-evaluate the supplied owner result against this exact source
            # and setup. A copied/stale/tampered weight is not authority.
            initial_trace = provisional.get("decision_trace") or {}
            try:
                evaluated_date = date.fromisoformat(initial_trace.get("evaluated_date"))
                expected = decide_initial_working_load(exercise=exercise, program_id=program_id,
                    calibration=initial_trace.get("calibration"), load_context=context,
                    has_current_work=initial_trace.get("has_current_work", True),
                    has_effective_history=initial_trace.get("has_effective_history", True), today=evaluated_date)
                provisional_used = (all(provisional.get(key) == value for key, value in expected.items()
                    if key != "decision_trace") and all(initial_trace.get(key) == value
                    for key, value in expected["decision_trace"].items()) and expected["status"] == "provisional")
            except (TypeError, ValueError):
                provisional_used = False
            if provisional_used:
                weight = provisional["recommended_working_weight"]
        if not qualified and not provisional_used:
            reasons.append("qualified_working_load_unavailable")
        increment = context.get("increment")
        if not provisional_used and (not _finite(increment) or increment <= 0 or context.get("increment_unit") not in {"kg", "lb"}):
            reasons.append("declared_increment_unavailable")
        if not reasons:
            proposals = []
            try:
                for row in rows:
                    raw_weight = Decimal(str(weight)) * Decimal(row["percent"]) / Decimal("100")
                    if provisional_used:
                        attainable = provisional["decision_trace"]["calibration"]["attainable"]
                        selected, reason = _initial_attainable_weight(raw_weight, attainable)
                        proposed = float(selected) if selected is not None and selected < Decimal(str(weight)) else None
                        feasibility = {"status": "declared_attainable_provisional", "attainable": deepcopy(attainable),
                            "limitations": ["Warmup uses a provisional working-load estimate and user-declared equipment."],
                            "reason_code": reason}
                    else:
                        proposed, feasibility = _attainable_weight(raw_weight, weight, "decrease", context)
                    proposals.append(proposed)
            except DecimalException as error:
                # Accepted finite declarations can exceed the shared grid
                # owner's decimal precision. Preserve its rounding authority
                # and abstain rather than invent a minimum increment/grid.
                proposals = [None]
                reasons.append("warmup_grid_arithmetic_unresolved")
                feasibility = {"status": "unknown", "increment": increment,
                    "increment_unit": context.get("increment_unit"), "grid_anchor_weight": weight,
                    "arithmetic_error": type(error).__name__,
                    "limitations": ["Declared grid arithmetic cannot be resolved at the supported decimal precision."]}
            if any(value is None for value in proposals):
                reasons.append("attainable_warmup_load_unresolved")
            else:
                for row, proposed in zip(rows, proposals):
                    row["suggested_weight"] = proposed
        status = "manual" if reasons else "suggested"
        explanation = ("Source warmup targets are preserved; enter actual loads manually because load qualification is unresolved."
            if reasons else "Source warmup percentages use the provisional initial-load estimate and declared attainable loads."
            if provisional_used else "Source warmup percentages use the qualified next working load and the declared increment.")
    reasons = list(dict.fromkeys(reasons))
    return _safe_json({"version": VERSION, "source_count": source_count, "count": count, "status": status,
        "source_instructions": _source_instructions(protocol, count, protocol_qualified),
        "sets": rows, "reason_codes": reasons, "explanation": explanation, "equipment_feasibility": feasibility,
        "decision_trace": {"owner": "core_engine.authored_warmups", "version": VERSION,
            "permission": "source_warmup_guidance_only", "program_id": program_id,
            "source_count": source_count, "count": count, "source_lineage": deepcopy(exercise.get("source_lineage") or {}),
            "exercise_occurrence_id": exercise.get("exercise_occurrence_id"), "exercise_id": exercise.get("id"),
            "performed_variant": deepcopy(exercise.get("performed_variant")),
            "source_prescription": deepcopy(exercise.get("authored_prescription")),
            "source_protocol": deepcopy(protocol), "source_protocol_digest": _digest(protocol),
            "source_exercise_protocol_digest": exercise_protocol_digest,
            "source_recipe_digest": _digest(protocol.get("exercise_specific_warm_up")),
            "source_recipe_qualified": protocol_qualified and program_id in _AUTHORED_PROGRAMS,
            "working_recommendation_id": working.get("id"), "working_evidence_revision": working.get("evidence_revision"),
            "working_decision_digest": _digest(working), "working_decision_trace": deepcopy(working.get("decision_trace")),
            "working_scope": working.get("scope"), "qualified_working_weight": working.get("recommended_weight"),
            "provisional_working_weight": provisional.get("recommended_working_weight") if provisional_used else None,
            "provisional_decision_trace": deepcopy(provisional.get("decision_trace")) if provisional_used else None,
            "load_context": deepcopy(context), "status": status, "reason_codes": reasons,
            "sets": deepcopy(rows)}})
