"""Lossless authored targets. Parsing never supplies a missing prescription.

Raw values remain authoritative when a cell cannot be interpreted unambiguously.
Numeric compatibility is available only for one uniform numeric rep target.
"""
from copy import deepcopy
import re

PRESCRIPTION_VERSION = "authored-prescription-v1"
SOURCE_FIELDS = (
    "exercise", "working_sets", "reps", "warm_up_sets", "early_set_rpe",
    "last_set_rpe", "effort", "rest", "last_set_intensity_technique", "notes",
    "tracking_set_1", "tracking_set_2", "tracking_set_3", "tracking_set_4",
    "substitution_option_1", "substitution_option_2",
)


def target(raw, *, kind="reps"):
    if raw is None or not str(raw).strip():
        return {"kind": "unknown", "raw": None}
    raw = str(raw).strip()
    if kind == "reps" and raw.upper() == "AMRAP":
        return {"kind": "amrap", "raw": raw}
    text = raw.replace("–", "-").replace("—", "-")
    match = re.fullmatch(r"(~)?\s*(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?", text)
    if match:
        low, high = float(match[2]), float(match[3] or match[2])
        if low <= high and (kind != "reps" or (low >= 1 and low.is_integer() and high.is_integer())):
            return {"kind": kind, "raw": raw, "min": low, "max": high, "approximate": bool(match[1])}
    return {"kind": "text", "raw": raw}


def _per_set(raw, count):
    # Comma/semicolon/slash lists are positional only when every working set is named.
    # A hyphen is a range, never a positional delimiter.
    parts = re.split(r"\s*[,;/]\s*", str(raw)) if raw is not None else []
    return parts if len(parts) == count else [raw] * count


def preserve_prescription(raw_fields, count, *, effort_kind="rpe", set_type="work"):
    raw = {key: raw_fields.get(key) for key in SOURCE_FIELDS}
    reps = _per_set(raw["reps"], count)
    early = _per_set(raw["early_set_rpe"], count)
    last = raw["last_set_rpe"]
    sets = []
    for index in range(count):
        effort = (last if index == count - 1 else early[index])
        if effort is None and raw["effort"] is not None:
            effort = raw["effort"]
        # An absent last-set cell remains unknown; it does not inherit early-set effort.
        rep_raw = reps[index]
        role = re.fullmatch(r"(top|backoff)(?: set)?\s*:\s*(.+)", str(rep_raw), re.IGNORECASE)
        rep_target = target(role[2] if role else rep_raw)
        if role:
            rep_target["raw"] = rep_raw
        sets.append({"set_index": index + 1, "set_type": role[1].lower() if role else set_type,
            "rep_target": rep_target, "effort_target": target(effort, kind=effort_kind),
            "rest": raw["rest"],
            "intensity_technique": raw["last_set_intensity_technique"] if index == count - 1 else None})
    return {"version": PRESCRIPTION_VERSION, "raw": raw, "sets": sets}


def uniform_rep_range(prescription):
    sets = (prescription or {}).get("sets") or []
    targets = [item["rep_target"] for item in sets]
    if not targets or any(item.get("kind") != "reps" for item in targets):
        return None
    ranges = {(int(item["min"]), int(item["max"])) for item in targets}
    return list(next(iter(ranges))) if len(ranges) == 1 else None


def execution_fields(exercise):
    return {key: deepcopy(exercise[key]) for key in ("authored_prescription", "source_lineage") if exercise.get(key) is not None}


def requires_typed_tracking(exercise):
    return bool((exercise or {}).get("authored_prescription")) and uniform_rep_range(exercise["authored_prescription"]) is None


def is_bodyweight_authored(exercise):
    return bool((exercise or {}).get("authored_prescription")) and exercise.get("load_semantics") == "bodyweight"


def requires_receipt_tracking(exercise):
    return requires_typed_tracking(exercise) or is_bodyweight_authored(exercise)


def typed_tracking_feedback(exercise, *, completed_sets, set_index=1):
    """Receipt/count evidence only; no numeric progression for an unsupported target."""
    prescribed = exercise["authored_prescription"]["sets"]
    current = prescribed[min(max(1, set_index), len(prescribed)) - 1]
    trace = {"owner": "core_engine.authored_prescription", "version": PRESCRIPTION_VERSION,
        "source_lineage": deepcopy(exercise.get("source_lineage")),
        "set_prescription": deepcopy(current), "numeric_progression": "not_applicable",
        "completed_sets": completed_sets}
    return {"completed_sets": completed_sets, "remaining_sets": max(0, int(exercise["sets"]) - completed_sets),
        "recommended_reps_min": None, "recommended_reps_max": None,
        "recommended_weight": 0.0 if is_bodyweight_authored(exercise) else float(exercise["recommended_working_weight"]),
        "guidance": "Follow the authored target and record actual reps.",
        "guidance_rationale": "authored_typed_target", "decision_trace": trace}
