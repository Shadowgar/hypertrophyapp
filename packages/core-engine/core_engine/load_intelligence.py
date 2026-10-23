"""Pure, load-only authored guidance from effective exercise occurrences.

Receipt identity and effective-history queries belong to the API. This owner
checks exact work coverage, preserves unknown evidence, and interprets only the
named authored progression rule. It never mutates a source prescription.
"""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
import math

VERSION = "authored-load-intelligence-v1"
_KG_PER_LB = Decimal("0.45359237")
_SOURCE_FIELDS = ("source_program_id", "source_sha256", "importer_sha256", "artifact_version", "source_session", "source_slot")
_SUPPORTED_BASES = {"total_external", "per_hand", "machine_stack"}
_SUPPORTED_RULES = {"pure_bodybuilding_phase_1_full_body_rules", "pure_bodybuilding_phase_2_full_body_rules"}


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _safe_json(value):
    if isinstance(value, dict):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_json(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return {"invalid_number": str(value)}
    return value


def _digest(value):
    return sha256(json.dumps(_safe_json(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _load_identity(context):
    return {key: context.get(key) for key in ("unit", "basis", "equipment_key")}


def _context_reasons(context):
    reasons = []
    if context.get("unit") != "kg":
        reasons.append("recorded_load_unit_unknown")
    if context.get("basis") not in _SUPPORTED_BASES:
        reasons.append("load_basis_unknown_or_unsupported")
    if context.get("basis") == "machine_stack" and not context.get("equipment_key"):
        reasons.append("machine_equipment_identity_unknown")
    semantics = context.get("load_semantics", context.get("semantics"))
    if semantics not in (None, "external_load", "external", "total_external", "per_hand", "machine_stack"):
        reasons.append("load_semantics_unsupported_or_contradictory")
    return reasons


def _numeric_target(target, kind):
    low, high = target.get("min"), target.get("max")
    if target.get("kind") != kind or not _finite(low) or not _finite(high) or low > high:
        return None
    if kind == "reps" and (low < 1 or not float(low).is_integer() or not float(high).is_integer()):
        return None
    if kind == "rpe" and (low < 0 or high > 10):
        return None
    return low, high


def _prescription_reasons(prescription, source):
    reasons = []
    sets = prescription.get("sets") or []
    if not sets or any(not isinstance(item, dict) for item in sets):
        return ["source_working_set_prescription_unknown"]
    for item in sets:
        if _numeric_target(item.get("rep_target") or {}, "reps") is None:
            reasons.append("rep_target_unresolved_or_amrap")
        if _numeric_target(item.get("effort_target") or {}, "rpe") is None:
            reasons.append("effort_target_unresolved")
    hard_keys = ("hard_load_instruction", "hard_load", "source_hard_load", "load_target")
    if any(container.get(key) for container in (prescription, source, *sets) for key in hard_keys):
        reasons.append("source_hard_load_instruction")
    if source.get("load_semantics") in {"bodyweight", "assistance", "unknown"}:
        reasons.append("load_semantics_unsupported_or_contradictory")
    return list(dict.fromkeys(reasons))


def comparison_key_for_exposure(exposure):
    """Cohort identity excludes date/week/occurrence IDs, retaining source position."""
    source = exposure.get("source_context") or {}
    context = exposure.get("load_context") or {}
    prescription = exposure.get("prescription") or {}
    if (any(source.get(key) is None or source.get(key) == "" for key in _SOURCE_FIELDS)
            or not exposure.get("performed_variant_id") or _context_reasons(context)
            or _prescription_reasons(prescription, source)):
        return None
    normalized = [{key: deepcopy(item.get(key)) for key in
        ("set_index", "set_type", "rep_target", "effort_target", "intensity_technique", "rest")}
        for item in prescription["sets"]]
    return _digest({"owner": VERSION, "source": {key: source[key] for key in _SOURCE_FIELDS},
        "prescription": normalized, "performed_variant_id": exposure["performed_variant_id"],
        "load_context": _load_identity(context)})


def summarize_completed_exercise_exposure(*, workout_occurrence_id, exercise_occurrence_id,
        prescription, effective_sets, performed_variant_id, load_context, source_context,
        closure="all_required_sets"):
    prescription = deepcopy(prescription or {})
    context, source = deepcopy(load_context or {}), deepcopy(source_context or {})
    prescribed = prescription.get("sets") or []
    required = [item.get("set_index") for item in prescribed if isinstance(item, dict)]
    reasons = []
    if (not required or len(required) != len(prescribed) or any(type(index) is not int or index < 1 for index in required)
            or len(required) != len(set(required))):
        reasons.append("source_working_set_identity_invalid")
    if not workout_occurrence_id or not exercise_occurrence_id:
        reasons.append("occurrence_identity_unknown")
    rows, excluded, by_id = [], [], {}
    for raw in effective_sets or []:
        if not isinstance(raw, dict):
            reasons.append("receipt_invalid")
            continue
        kind = str(raw.get("set_kind") or "work").strip().lower()
        if raw.get("voided_at") is not None or raw.get("parent_set_index") is not None or kind not in {"work", "top", "backoff"}:
            if raw.get("id"):
                excluded.append(str(raw["id"]))
            continue
        row = {key: deepcopy(raw.get(key)) for key in ("id", "set_index", "reps", "weight", "rpe", "parent_set_index")}
        row["set_kind"] = kind
        if "load_context" in raw:
            row["load_context"] = deepcopy(raw["load_context"])
        if "source_set_id" in raw:
            row["source_set_id"] = raw["source_set_id"]
        record_id = row["id"]
        if not isinstance(record_id, str) or not record_id:
            reasons.append("receipt_identity_unknown")
        elif record_id in by_id:
            if _digest(row) != _digest(by_id[record_id]):
                reasons.append("conflicting_retry_receipt")
            continue
        by_id[record_id] = row
        rows.append(row)
    rows.sort(key=lambda row: (row["set_index"] if type(row["set_index"]) is int else 0, str(row["id"])))
    coverage = [row["set_index"] for row in rows]
    if any(type(index) is not int or index not in required for index in coverage):
        reasons.append("unexpected_working_set_identity")
    if len(coverage) != len(set(str(index) for index in coverage)):
        reasons.append("duplicate_working_set_identity")
    source_by_index = {item.get("set_index"): item for item in prescribed if isinstance(item, dict)}
    for row in rows:
        expected_source_id = source_by_index.get(row["set_index"], {}).get("source_set_id") if type(row["set_index"]) is int else None
        if row.get("source_set_id") is not None and row["source_set_id"] != expected_source_id:
            reasons.append("source_set_identity_mismatch")
    invalid = bool(reasons)
    full_coverage = not invalid and set(coverage) == set(required)
    complete = full_coverage and closure in {"all_required_sets", "finalized"}
    completion = "invalid" if invalid else "complete" if complete else "partial" if closure == "partial" else "incomplete"
    if not complete:
        reasons.append("partial_exposure" if closure == "partial" else "incomplete_exposure")
    reasons.extend(_context_reasons(context))
    reasons.extend(_prescription_reasons(prescription, source))
    actual_valid = all(_finite(row["weight"]) and row["weight"] > 0 and type(row["reps"]) is int and row["reps"] > 0
        and (row["rpe"] is None or (_finite(row["rpe"]) and 0 <= row["rpe"] <= 10)) for row in rows)
    if not actual_valid:
        reasons.append("actual_performance_invalid")
    if any(row["rpe"] is None for row in rows):
        reasons.append("actual_rpe_missing")
    if any("load_context" in row and (not isinstance(row["load_context"], dict)
            or _context_reasons(row["load_context"]) or _load_identity(row["load_context"]) != _load_identity(context)) for row in rows):
        reasons.append("recorded_load_context_incomparable")
    uniform_weight = rows[0]["weight"] if rows and actual_valid and all(row["weight"] == rows[0]["weight"] for row in rows) else None
    if rows and uniform_weight is None and actual_valid:
        reasons.append("mixed_working_loads")
    result = {"version": "completed-exposure-v1", "workout_occurrence_id": workout_occurrence_id,
        "exercise_occurrence_id": exercise_occurrence_id, "complete": complete, "completion": completion,
        "prescription": prescription, "effective_sets": rows, "effective_set_ids": [row["id"] for row in rows],
        "excluded_set_ids": sorted(set(excluded)), "required_working_set_count": len(required),
        "completed_working_set_count": len(set(coverage)) if not invalid else 0,
        "performed_variant_id": performed_variant_id, "load_context": context, "source_context": source,
        "known_baseline_weight": uniform_weight if not _context_reasons(context)
            and "recorded_load_context_incomparable" not in reasons else None,
        "reason_codes": list(dict.fromkeys(reasons))}
    key = comparison_key_for_exposure(result)
    if key is None and not any(code in result["reason_codes"] for code in ("load_basis_unknown_or_unsupported", "effort_target_unresolved", "rep_target_unresolved_or_amrap")):
        result["reason_codes"].append("source_or_comparison_context_unknown")
    result["comparison_key"] = key
    result["comparable"] = complete and key is not None and not result["reason_codes"]
    result["evidence_digest"] = _digest(result)
    return result


def _rule_runtime(rule_set):
    rules = rule_set or {}
    progression = rules.get("progression_rules") or {}
    success, failure = progression.get("on_success") or {}, progression.get("on_under_target") or {}
    if (rules.get("rule_set_id") not in _SUPPORTED_RULES or not rules.get("version")
            or progression.get("success_condition") != "reach_top_of_rep_range_then_add_load"
            or success.get("action") != "increase_load" or failure.get("action") != "hold_or_reduce"
            or (progression.get("on_in_range") or {}).get("action") != "hold_load_chase_reps"
            or not _finite(success.get("percent")) or success["percent"] <= 0
            or not _finite(failure.get("reduce_percent")) or not 0 < failure["reduce_percent"] < 100
            or type(failure.get("after_exposures")) is not int or failure["after_exposures"] < 1):
        return None
    return {"increase_percent": success["percent"], "reduce_percent": failure["reduce_percent"],
        "after_exposures": failure["after_exposures"]}


def _outcome(exposure):
    prescribed = {item["set_index"]: item for item in exposure["prescription"]["sets"]}
    values = [(row, prescribed[row["set_index"]]) for row in exposure["effective_sets"]]
    below = any(row["reps"] < item["rep_target"]["min"] for row, item in values)
    top = bool(values) and all(row["reps"] >= item["rep_target"]["max"] for row, item in values)
    within_effort = bool(values) and all(item["effort_target"]["min"] <= row["rpe"] <= item["effort_target"]["max"] for row, item in values)
    reached_effort = bool(values) and all(row["rpe"] >= item["effort_target"]["min"] for row, item in values)
    return {"below": below, "top": top, "within_effort": within_effort, "reached_effort": reached_effort}


def _percentage_weight(baseline, percent, *, direction):
    # Retain exact source percentages through midpoint rounding; converting an
    # already multiplied binary float to Decimal cannot recover its precision.
    return Decimal(str(baseline)) * (Decimal("1") + direction * Decimal(str(percent)) / Decimal("100"))


def _attainable_weight(raw_weight, baseline, action, context):
    increment, unit = context.get("increment"), context.get("increment_unit")
    limitations = []
    if increment is None:
        increment, unit = 0.5, "kg"
        status = "compatibility_increment_unverified"
        limitations.append("Using the existing 0.5 kg compatibility increment; equipment inventory is unknown.")
    elif not _finite(increment) or increment <= 0 or unit not in {"kg", "lb"}:
        return None, {"status": "unknown", "increment": increment, "increment_unit": unit,
            "limitations": ["Declared increment must be positive and have an explicit kg or lb unit."]}
    else:
        status = "declared_increment"
        limitations.append("Increment is user-declared; complete equipment inventory and available bounds are unverified.")
    if not context.get("equipment_key"):
        limitations.append("Equipment calibration identity is unknown.")
    feasible = {"status": status, "increment": increment, "increment_unit": unit, "limitations": limitations}
    if action == "hold":
        return float(baseline), feasible  # An actual performed load does not acquire rounding drift.
    factor = _KG_PER_LB if unit == "lb" else Decimal("1")
    increment_decimal = Decimal(str(increment))
    anchor = Decimal(str(baseline)) if status == "declared_increment" else Decimal("0")
    # A performed load is attainable evidence; a declared step does not prove
    # a zero-origin stack/bar grid. Move whole increments from that actual load.
    units = (Decimal(str(raw_weight)) - anchor) / factor
    rounded = anchor + (units / increment_decimal).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * increment_decimal * factor
    feasible["grid_anchor_weight"] = float(anchor)
    value = float(rounded)
    if value <= 0 or (action == "increase" and value <= baseline) or (action == "decrease" and value >= baseline):
        feasible["limitations"].append("The declared rounding does not produce a positive load in the requested direction.")
        return None, feasible
    return value, feasible


def _evidence(exposures, latest, streak=0):
    key = latest.get("comparison_key") if latest else None
    matching = [item for item in exposures if item.get("complete") and key is not None and item.get("comparison_key") == key and item.get("comparable")]
    rows = latest.get("effective_sets") or [] if latest else []
    return {"completed_exposure_count": sum(bool(item.get("complete")) for item in exposures),
        "comparable_completed_exposure_count": len(matching), "consecutive_underperformance_count": streak,
        "actual_rpe_count": sum(row.get("rpe") is not None for row in rows),
        "actual_rpe_sufficient": bool(rows) and all(_finite(row.get("rpe")) and 0 <= row["rpe"] <= 10 for row in rows),
        "required_working_set_count": latest.get("required_working_set_count", 0) if latest else 0,
        "effective_set_ids": [record_id for item in exposures for record_id in item.get("effective_set_ids") or []],
        "exposure_ids": [{"workout_occurrence_id": item.get("workout_occurrence_id"), "exercise_occurrence_id": item.get("exercise_occurrence_id")}
            for item in exposures if item.get("complete")]}


def _decision(*, action, weight, baseline, reasons, explanation, exposures, latest, rule_set, context, streak=0, scope="next_exposure"):
    recommended, feasibility = (None, {"status": "unknown", "increment": context.get("increment"), "increment_unit": context.get("increment_unit"),
        "limitations": ["No qualified load proposal."]}) if weight is None else _attainable_weight(weight, baseline, action, context)
    if weight is not None and recommended is None:
        action = "monitor"
        reasons = [*reasons, "attainable_load_unresolved"]
        explanation = "The declared equipment increment cannot produce a qualified load in the requested direction."
    evidence = _evidence(exposures, latest, streak)
    quality = "insufficient" if action == "monitor" else "complete_comparable" if scope == "next_exposure" else "current_set_comparable"
    return {"action": action, "scope": scope, "recommended_weight": recommended,
        "known_baseline_weight": baseline, "prefill_available": recommended is not None and action != "monitor",
        "reason_codes": list(dict.fromkeys(reasons)), "explanation": explanation, "evidence": evidence,
        "evidence_quality": quality, "confidence": quality, "equipment_feasibility": feasibility,
        "decision_trace": {"owner": "core_engine.load_intelligence", "version": VERSION, "scope": scope,
            "comparison_key": latest.get("comparison_key") if latest else None,
            "rule_set_id": (rule_set or {}).get("rule_set_id"), "rule_version": (rule_set or {}).get("version"),
            "rule_digest": _digest(rule_set or {}), "rule_inputs": _rule_runtime(rule_set),
            "evidence_digests": [item.get("evidence_digest") for item in exposures], "load_context": deepcopy(context),
            "evidence": evidence, "action": action, "recommended_weight": recommended,
            "permission": "working_load_only", "reason_codes": list(dict.fromkeys(reasons))}}


def decide_next_working_load(*, exposures, rule_set, load_context):
    """Fold chronological occurrence summaries; no historical counter is an input."""
    distinct, seen, conflict = [], {}, False
    for exposure in exposures or []:
        identity = (exposure.get("workout_occurrence_id"), exposure.get("exercise_occurrence_id"))
        if identity in seen:
            conflict |= seen[identity].get("evidence_digest") != exposure.get("evidence_digest")
            continue
        seen[identity] = exposure
        distinct.append(exposure)
    latest = distinct[-1] if distinct else None
    context = deepcopy(load_context or {})
    baseline = latest.get("known_baseline_weight") if latest else None
    runtime = _rule_runtime(rule_set)
    reasons = [*(latest.get("reason_codes") or [])] if latest else ["no_completed_exposure_evidence"]
    if latest is not None and _load_identity(context) != _load_identity(latest.get("load_context") or {}):
        reasons.append("requested_load_context_incomparable")
        baseline = None
    reasons.extend(_context_reasons(context))
    if runtime is None:
        reasons.append("source_progression_rule_unsupported")
    if conflict:
        reasons.append("conflicting_exposure_identity")
    if latest is None or not latest.get("comparable") or reasons:
        return _decision(action="monitor", weight=None, baseline=baseline, reasons=reasons,
            explanation="A new load decision needs complete comparable working sets, known actual RPE and explicit source/load context.",
            exposures=distinct, latest=latest, rule_set=rule_set, context=context)
    outcome = _outcome(latest)
    streak = 0
    if outcome["below"] and outcome["reached_effort"]:
        for previous in reversed(distinct):
            previous_key = previous.get("comparison_key")
            if previous_key is not None and previous_key != latest["comparison_key"]:
                continue  # Other source positions/variants have independent histories.
            if not previous.get("comparable"):
                break
            previous_outcome = _outcome(previous)
            if not previous_outcome["below"] or not previous_outcome["reached_effort"]:
                break
            streak += 1
        if streak >= runtime["after_exposures"]:
            action, weight, reasons = "decrease", _percentage_weight(baseline, runtime["reduce_percent"], direction=-1), ["repeated_comparable_underperformance"]
            explanation = f"{streak} consecutive comparable completed exposures were below the authored rep target; apply the named source reduction."
        else:
            action, weight, reasons = "hold", baseline, ["single_underperforming_exposure_protected"]
            explanation = "Hold the actual performed load; one poor completed exposure does not establish repeated underperformance."
    elif not outcome["within_effort"]:
        action, weight, reasons = "monitor", None, ["actual_effort_outside_source_target"]
        explanation = "Actual RPE was outside the explicit authored effort target; no new progression conclusion is qualified."
    elif outcome["top"]:
        action, weight, reasons = "increase", _percentage_weight(baseline, runtime["increase_percent"], direction=1), ["source_top_rep_range_met"]
        explanation = "All required working sets reached the authored rep ceiling with actual RPE within their source targets."
    else:
        action, weight, reasons = "hold", baseline, ["source_rep_range_met"]
        explanation = "Completed working sets were in the authored rep range with actual RPE within their source targets; hold the actual load."
    return _decision(action=action, weight=weight, baseline=baseline, reasons=reasons, explanation=explanation,
        exposures=distinct, latest=latest, rule_set=rule_set, context=context, streak=streak)


def decide_remaining_working_load(*, exposure, rule_set, load_context=None):
    """Temporary guidance: below typed reps plus actual RPE above typed source max."""
    recorded_context = exposure.get("load_context") or {}
    context = deepcopy(recorded_context if load_context is None else load_context)
    baseline = exposure.get("known_baseline_weight")
    runtime = _rule_runtime(rule_set)
    rows = exposure.get("effective_sets") or []
    reasons = [code for code in exposure.get("reason_codes") or [] if code == "incomplete_exposure" or code == "actual_rpe_missing"]
    blockers = [code for code in exposure.get("reason_codes") or [] if code not in {"incomplete_exposure", "actual_rpe_missing"}]
    blockers.extend(_context_reasons(context))
    if _load_identity(context) != _load_identity(recorded_context):
        blockers.append("requested_load_context_incomparable")
        baseline = None
    if (runtime is None or not rows or baseline is None or blockers or not exposure.get("comparison_key")
            or exposure.get("complete") or exposure.get("completion") == "partial"):
        return _decision(action="monitor", weight=None, baseline=baseline,
            reasons=[*blockers, "remaining_sets_not_qualified"],
            explanation="No temporary load adjustment is qualified for the remaining authored sets.",
            exposures=[exposure], latest=exposure, rule_set=rule_set, context=context, scope="remaining_sets")
    last = rows[-1]
    prescribed = next(item for item in exposure["prescription"]["sets"] if item["set_index"] == last["set_index"])
    if last["rpe"] is None:
        action, weight, reasons = "monitor", None, ["actual_rpe_missing"]
        explanation = "Actual RPE is unknown; retain the chosen load without a new qualified adjustment."
    elif last["reps"] < prescribed["rep_target"]["min"] and last["rpe"] > prescribed["effort_target"]["max"]:
        action, weight, reasons = "decrease", _percentage_weight(baseline, runtime["reduce_percent"], direction=-1), ["current_set_below_reps_above_source_rpe"]
        explanation = "This working set was below its authored rep minimum and above its explicit RPE target; the named reduction applies only to remaining sets."
    else:
        action, weight, reasons = "hold", baseline, ["no_current_set_reduction_trigger"]
        explanation = "Keep the actual working load; this set does not meet both source-relative conditions for a temporary reduction."
    return _decision(action=action, weight=weight, baseline=baseline, reasons=reasons, explanation=explanation,
        exposures=[exposure], latest=exposure, rule_set=rule_set, context=context, scope="remaining_sets")


INITIAL_VERSION = "authored-initial-load-v1"
_INITIAL_PROGRAMS = {"pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"}
_INITIAL_EXPLANATIONS = {
    "current_working_sets_take_precedence": "Current working sets use the existing remaining-set guidance.",
    "effective_history_takes_precedence": "Existing working history takes precedence, including incomplete or unqualified history; retain its baseline or manual guidance.",
    "authored_program_unqualified": "Initial estimates are available only for Authored Phase 1 and Phase 2.",
    "source_program_mismatch": "The source program does not match this Authored program.",
    "initial_rep_target_unsupported": "The first source work set needs a numeric rep target with an upper bound from 6 to 12.",
    "initial_effort_target_unsupported": "The first source work set needs an explicit source RPE range within 7 to 10.",
    "first_working_set_not_ordinary": "The first source work set must be ordinary work without an intensity technique.",
    "source_hard_load_instruction": "A source load directive prevents an initial estimate.",
    "authored_constraint_unresolved": "Resolve the exercise constraint or substitution before estimating a load.",
    "pain_or_unsafe_report": "A pain or unsafe-execution report prevents an initial estimate.",
    "recorded_load_unit_unknown": "Canonical load context must use kg.",
    "load_basis_unknown_or_unsupported": "Declare total external, per-hand, or same-machine stack load basis.",
    "load_semantics_unsupported_or_contradictory": "The source and declared load meanings are unsupported or inconsistent.",
    "equipment_identity_required": "Identify the exact equipment setup for this benchmark.",
    "machine_equipment_identity_unknown": "Identify this exact machine setup.",
    "equipment_unavailable": "Declare available equipment matching this performed exercise.",
    "calibration_load_invalid": "Enter a positive finite benchmark load.",
    "calibration_unit_unknown": "Declare the benchmark unit as lb or kg.",
    "calibration_date_invalid": "Enter a valid observation date that is not in the future.",
    "exact_setup_confirmation_required": "Confirm the report still represents this exact variant, side, range of motion and setup.",
    "performed_variant_mismatch": "The benchmark must describe the current performed variant.",
    "setup_details_required": "Describe the side, range of motion, grip, attachment and relevant settings.",
    "calibration_method_unsupported": "Use a reported known 1RM or a recent set with explicit RIR.",
    "recent_set_evidence_invalid": "A recent set needs 1–10 completed reps and explicit 0–3 RIR, with reps plus RIR at most 10.",
    "attainable_loads_invalid": "Declare positive attainable loads or a positive minimum, step and maximum in lb or kg.",
    "no_attainable_load_at_or_below_estimate": "No declared attainable load is at or below the estimate; enter a load manually.",
    "initial_arithmetic_unresolved": "The declared load cannot be represented for an initial estimate; enter a load manually.",
}


def _initial_number(value):
    """Input numbers must also fit the canonical finite-float transport."""
    try:
        return Decimal(str(value)) if _finite(value) else None
    except (OverflowError, ValueError):
        return None


def _initial_attainable_weight(raw_weight, attainable):
    """Floor on an explicitly declared original-unit inventory; no fallback grid.

    Returns (Decimal kg or None, reason or None). The bounded list is input
    validation; grids are computed arithmetically without materializing them.
    """
    from decimal import Context, ROUND_FLOOR, localcontext
    invalid = (None, "attainable_loads_invalid")
    if not isinstance(attainable, dict) or attainable.get("unit") not in {"lb", "kg"}:
        return invalid
    factor = _KG_PER_LB if attainable["unit"] == "lb" else Decimal("1")
    with localcontext(Context(prec=800)):
        if "values" in attainable:
            values = attainable["values"]
            if (any(key in attainable for key in ("min", "step", "max"))
                    or not isinstance(values, list) or not 1 <= len(values) <= 1000):
                return invalid
            parsed = [_initial_number(value) for value in values]
            if any(value is None or value <= 0 for value in parsed):
                return invalid
            selected = max((value * factor for value in parsed if value * factor <= raw_weight), default=None)
        else:
            minimum, step, maximum = (_initial_number(attainable.get(key)) for key in ("min", "step", "max"))
            if any(value is None or value <= 0 for value in (minimum, step, maximum)) or minimum > maximum:
                return invalid
            limit = min(raw_weight, maximum * factor)
            count = ((limit - minimum * factor) / (step * factor)).to_integral_value(rounding=ROUND_FLOOR)
            selected = minimum * factor + count * step * factor if count >= 0 else None
        return (selected, None) if selected is not None else (None, "no_attainable_load_at_or_below_estimate")


def decide_initial_working_load(*, exercise, program_id, calibration, load_context,
        has_current_work=False, has_effective_history=False, today=None):
    """Provisional first-load estimate; never performed evidence or progression.

    The caller supplies exact-cohort effective-history/current-work presence and
    enforces account, occurrence, calibration revision and setup applicability.
    This pure owner checks the source and calibration, with no source mutation.
    """
    from datetime import date
    from decimal import Context, DecimalException, localcontext
    from .equipment_profile import canonicalize_equipment_profile

    ex, cal, context = (deepcopy(value) if isinstance(value, dict) else {} for value in
        (exercise, calibration, load_context))
    prescription = ex.get("authored_prescription") or {}
    source = ex.get("source_lineage") or {}
    sets = prescription.get("sets") or []
    first = sets[0] if sets and isinstance(sets[0], dict) else {}
    variant = ex.get("performed_variant") or {}
    performed_id = (variant.get("exercise_id") or variant.get("id") or variant.get("variant_id")
        or variant.get("option_id") or ex.get("id"))
    reasons = []
    calculations = {}
    result = {"version": INITIAL_VERSION, "status": "unavailable", "unit": "kg",
        "recommended_working_weight": None, "reported_1rm": None, "estimated_1rm": None}
    evaluated_date = today if isinstance(today, date) else date.today()
    trace = {"owner": "core_engine.load_intelligence", "version": INITIAL_VERSION,
        "permission": "provisional_initial_working_load_only", "program_id": program_id,
        "source_lineage": source, "source_prescription": prescription,
        "performed_variant_id": performed_id, "load_context": context, "calibration": cal,
        "has_current_work": bool(has_current_work), "has_effective_history": bool(has_effective_history),
        "evaluated_date": evaluated_date.isoformat(), "calculations": calculations}

    def finish():
        codes = list(dict.fromkeys(reasons))
        explanation = " ".join(_INITIAL_EXPLANATIONS[code] for code in codes) if codes else (
            "Suggested starting weight — estimate. Uses your confirmed exact-setup report and the first source rep/RPE target, "
            "rounded down to a declared attainable load. This is provisional, not performed evidence or a guarantee of effort; adjust the actual load as needed.")
        if result["status"] == "provisional":
            codes = ["provisional_initial_load_estimate"]
        result.update(reason_codes=codes, explanation=explanation, decision_trace=trace)
        trace.update(status=result["status"], reason_codes=codes)
        return _safe_json(result)

    if has_current_work:
        reasons.append("current_working_sets_take_precedence")
    elif has_effective_history:
        reasons.append("effective_history_takes_precedence")
    if reasons:
        return finish()
    if program_id not in _INITIAL_PROGRAMS:
        reasons.append("authored_program_unqualified")
    if source.get("source_program_id") != program_id:
        reasons.append("source_program_mismatch")
    reps = _numeric_target(first.get("rep_target") or {}, "reps")
    effort = _numeric_target(first.get("effort_target") or {}, "rpe")
    if reps is None or not 6 <= reps[1] <= 12:
        reasons.append("initial_rep_target_unsupported")
    if effort is None or not 7 <= effort[0] <= effort[1] <= 10:
        reasons.append("initial_effort_target_unsupported")
    if (first.get("set_type") != "work" or type(first.get("set_index")) is not int
            or first["set_index"] != 1 or first.get("intensity_technique")):
        reasons.append("first_working_set_not_ordinary")
    containers = (ex, source, prescription, prescription.get("raw") or {}, *sets)
    if any(isinstance(item, dict) and any(item.get(key) for key in
            ("hard_load_instruction", "hard_load", "source_hard_load", "load_target")) for item in containers):
        reasons.append("source_hard_load_instruction")
    constraint = ex.get("authored_constraint") or {}
    if (constraint.get("status") not in (None, "ready", "confirmed")
            or constraint.get("execution_status") not in (None, "ready")):
        reasons.append("authored_constraint_unresolved")
    if any(container.get(key) for container in (ex, cal, context) for key in ("pain", "unsafe", "pain_reported", "unsafe_reported")):
        reasons.append("pain_or_unsafe_report")
    reasons.extend(_context_reasons(context))
    semantics_allowed = {None, "external_load", "external", *_SUPPORTED_BASES}
    for container in (ex, prescription, source, variant, context):
        for key in ("load_semantics", "semantics"):
            semantics = container.get(key)
            if semantics not in semantics_allowed or semantics in _SUPPORTED_BASES and semantics != context.get("basis"):
                reasons.append("load_semantics_unsupported_or_contradictory")
    if not isinstance(context.get("equipment_key"), str) or not context["equipment_key"].strip():
        reasons.append("equipment_identity_required")
    required = (variant or ex).get("equipment_tags")
    available = context.get("equipment_tags")
    if (not isinstance(required, list) or not isinstance(available, list)
            or not set(canonicalize_equipment_profile(required)) & set(canonicalize_equipment_profile(available))):
        reasons.append("equipment_unavailable")
    benchmark = _initial_number(cal.get("load"))
    if benchmark is None or benchmark <= 0:
        reasons.append("calibration_load_invalid")
    if cal.get("unit") not in {"kg", "lb"}:
        reasons.append("calibration_unit_unknown")
    try:
        observed = date.fromisoformat(cal.get("observed_date"))
        if observed > evaluated_date:
            raise ValueError("future observation")
    except (TypeError, ValueError):
        reasons.append("calibration_date_invalid")
    if cal.get("confirmed") is not True:
        reasons.append("exact_setup_confirmation_required")
    if not performed_id or cal.get("variant_id") != performed_id:
        reasons.append("performed_variant_mismatch")
    if not isinstance(cal.get("setup_details"), str) or not cal["setup_details"].strip():
        reasons.append("setup_details_required")
    method = cal.get("method")
    if method not in {"known_1rm", "recent_set"}:
        reasons.append("calibration_method_unsupported")
    recent_reps, recent_rir = cal.get("reps"), _initial_number(cal.get("rir"))
    if method == "recent_set" and (type(recent_reps) is not int or not 1 <= recent_reps <= 10
            or recent_rir is None or not 0 <= recent_rir <= 3 or recent_rir > 10 - recent_reps):
        reasons.append("recent_set_evidence_invalid")
    if reasons:
        return finish()
    try:
        with localcontext(Context(prec=800)):
            benchmark *= _KG_PER_LB if cal["unit"] == "lb" else Decimal("1")
            target_reps = Decimal(str(reps[1]))
            target_rir = Decimal("10") - Decimal(str(effort[0]))
            strength_factor = (Decimal("30") + recent_reps + recent_rir
                if method == "recent_set" and recent_reps + recent_rir != 1 else Decimal("30"))
            strength = benchmark * strength_factor / Decimal("30")
            # Cancel the common /30 before division to retain exact grid ties.
            numerator = benchmark * strength_factor
            denominator = Decimal("30") + target_reps + target_rir
            raw = numerator / denominator
            selected, reason = _initial_attainable_weight(raw, cal.get("attainable"))
            calculations.update(benchmark_kg=str(benchmark.normalize()),
                target_reps=str(target_reps.normalize()), provisional_target_rir=str(target_rir.normalize()),
                strength_kg=str(strength.normalize()), raw_start_numerator=str(numerator.normalize()), raw_start_denominator=str(denominator.normalize()),
                raw_start_kg=str(raw.normalize()), selected_kg=str(selected.normalize()) if selected is not None else None)
            if reason:
                reasons.append(reason)
            elif not all(math.isfinite(float(value)) and float(value) > 0 for value in (strength, selected)):
                reasons.append("initial_arithmetic_unresolved")
            else:
                result.update(status="provisional", recommended_working_weight=float(selected))
                result["reported_1rm" if method == "known_1rm" else "estimated_1rm"] = float(strength)
    except (DecimalException, OverflowError, ValueError):
        reasons.append("initial_arithmetic_unresolved")
    return finish()
