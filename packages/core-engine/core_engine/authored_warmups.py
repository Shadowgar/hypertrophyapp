"""Pure source-bound Authored warmup guidance; no new training prescription.

The numeric recipes below interpret the existing compiled Phase 1/2 source
instructions only when their instruction digest matches. Working-load evidence
and attainable-grid rounding remain owned by M2A-1 load intelligence. This
owner neither falls back to a planned load nor invents equipment inventory.
"""
from copy import deepcopy
from decimal import Decimal
import re

from .load_intelligence import _attainable_weight, _context_reasons, _digest, _finite, _numeric_target, _safe_json

VERSION = "authored-warmup-v1"
_AUTHORED_PROGRAMS = {"pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"}
# SHA-256 of the canonical JSON exercise_specific_warm_up rows in both compiled
# programs/gold/*.onboarding.json artifacts. A source edit must be requalified;
# matching a count alone never grants permission to interpret a new protocol.
_SOURCE_RECIPE_DIGEST = "0fde24aa0701b7d4bbb813d392e5b77cc7853956e2b4b8104193e480fe5694c0"
_SOURCE_RECIPES = {1: ((60, 6, 10),), 2: ((50, 6, 10), (70, 4, 6)),
    3: ((45, 6, 10), (65, 4, 6), (85, 3, 4))}
_HARD_LOAD_KEYS = ("hard_load_instruction", "hard_load", "source_hard_load", "load_target")
_EXTERNAL_SEMANTICS = {None, "external_load", "external", "total_external", "per_hand", "machine_stack"}


def _source_count(exercise):
    raw = (exercise.get("authored_prescription") or {}).get("raw") or {}
    value = raw["warm_up_sets"] if "warm_up_sets" in raw else exercise.get("warm_up_sets")
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


def build_authored_warmup_guidance(*, exercise, working_decision, load_context, program_id, source_protocol):
    """Return lossless source count/text plus qualified canonical kg suggestions.

    Numeric but unsupported counts and textual counts have no synthetic rows.
    A recognized source recipe retains its rows/reps/percentages when load
    evidence abstains; every suggested_weight is then null for manual entry.
    """
    exercise, working, context, protocol = (deepcopy(value or {}) for value in
        (exercise, working_decision, load_context, source_protocol))
    source_count, count = _source_count(exercise)
    protocol_qualified = _digest(protocol.get("exercise_specific_warm_up")) == _SOURCE_RECIPE_DIGEST
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
        if (working.get("scope") != "next_exposure" or working.get("prefill_available") is not True
                or not _finite(weight) or weight <= 0):
            reasons.append("qualified_working_load_unavailable")
        increment = context.get("increment")
        if not _finite(increment) or increment <= 0 or context.get("increment_unit") not in {"kg", "lb"}:
            reasons.append("declared_increment_unavailable")
        if not reasons:
            proposals = []
            for row in rows:
                raw_weight = Decimal(str(weight)) * Decimal(row["percent"]) / Decimal("100")
                proposed, feasibility = _attainable_weight(raw_weight, weight, "decrease", context)
                proposals.append(proposed)
            if any(value is None for value in proposals):
                reasons.append("attainable_warmup_load_unresolved")
            else:
                for row, proposed in zip(rows, proposals):
                    row["suggested_weight"] = proposed
        status = "manual" if reasons else "suggested"
        explanation = ("Source warmup targets are preserved; enter actual loads manually because load qualification is unresolved."
            if reasons else "Source warmup percentages use the qualified next working load and the declared increment.")
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
            "source_recipe_digest": _digest(protocol.get("exercise_specific_warm_up")),
            "source_recipe_qualified": protocol_qualified and program_id in _AUTHORED_PROGRAMS,
            "working_recommendation_id": working.get("id"), "working_evidence_revision": working.get("evidence_revision"),
            "working_decision_digest": _digest(working), "working_decision_trace": deepcopy(working.get("decision_trace")),
            "working_scope": working.get("scope"), "qualified_working_weight": working.get("recommended_weight"),
            "load_context": deepcopy(context), "status": status, "reason_codes": reasons,
            "sets": deepcopy(rows)}})
