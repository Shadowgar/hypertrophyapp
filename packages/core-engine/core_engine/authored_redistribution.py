"""Deterministic, dose-preserving placement of authored source units.

This module changes session placement only. It owns no exercise selection,
substitution or set prescription. Optional dates activate the declared advisory
calendar-gap objective; omitted dates retain the M1-C allocation policy.
"""
from copy import deepcopy
from itertools import combinations
from datetime import date
from hashlib import sha256
import json


class AuthoredAllocationInfeasible(ValueError):
    """The requested placement cannot retain the complete authored workload."""


DATE_OBJECTIVE = {
    "version": "selected-date-lexical-v1",
    "order": ["consecutive_overlapping_working_sets", "working_set_range", "target_squared_deviation", "source_cuts"],
    "overlap_unit": "sum of minimum primary-muscle attributed working sets on consecutive calendar-date edges",
    "authority": "advisory scheduling policy; no recovery or clinical qualification",
}


def _muscle_work(exercises):
    work = {}
    for exercise in exercises:
        for muscle in sorted(set(str(value).strip().lower() for value in exercise.get("primary_muscles") or [] if str(value).strip())):
            work[muscle] = work.get(muscle, 0) + int(exercise.get("sets") or 0)
    return work


def _overlap(left, right):
    return sum(min(left.get(muscle, 0), right.get(muscle, 0)) for muscle in sorted(left.keys() & right.keys()))


def _date_context(selected_dates, previous_context, next_context):
    if any(type(value) is not date for value in selected_dates) or list(selected_dates) != sorted(set(selected_dates)):
        raise AuthoredAllocationInfeasible("Selected dates must be distinct ordered local calendar dates")
    contexts = []
    for side, context in (("previous", previous_context), ("next", next_context)):
        if context is None:
            contexts.append(None)
            continue
        if not isinstance(context, dict) or type(context.get("date")) is not date:
            raise AuthoredAllocationInfeasible("Neighbor context needs an explicit local calendar date")
        if (side == "previous" and context["date"] >= selected_dates[0]) or (side == "next" and context["date"] <= selected_dates[-1]):
            raise AuthoredAllocationInfeasible("Neighbor context must be outside the selected date range")
        exercises = context.get("exercises")
        if exercises is not None and (not isinstance(exercises, list) or any(not isinstance(item, dict) for item in exercises)):
            raise AuthoredAllocationInfeasible("Malformed neighbor workout context")
        contexts.append(context)
    return contexts


def redistribute_authored_sessions(source_sessions, adapted_days, *, selected_dates=None,
        previous_context=None, next_context=None, preserve_grouping=False):
    day_count = len(adapted_days)
    if not source_sessions or day_count not in ((2, 3, 4, 5) if selected_dates is not None else (2, 3, 4)):
        bounds = "2–5" if selected_dates is not None else "2–4"
        raise AuthoredAllocationInfeasible(f"Authored redistribution needs source sessions and {bounds} target days")

    if selected_dates is not None:
        if len(selected_dates) != day_count:
            raise AuthoredAllocationInfeasible("Selected date count must equal target day count")
        previous_context, next_context = _date_context(selected_dates, previous_context, next_context)
    elif previous_context is not None or next_context is not None or preserve_grouping:
        raise AuthoredAllocationInfeasible("Date context and fixed grouping require selected dates")

    entries = []
    by_slot = {}
    for session_index, session in enumerate(source_sessions):
        for exercise_index, exercise in enumerate(session.get("exercises") or []):
            if not isinstance(exercise, dict):
                raise AuthoredAllocationInfeasible("Malformed authored source slot")
            slot_id = str((exercise.get("source_lineage") or {}).get("source_slot_id") or f"legacy:{session_index}:{exercise_index}")
            if slot_id in by_slot:
                raise AuthoredAllocationInfeasible(f"Duplicate authored source slot: {slot_id}")
            by_slot[slot_id] = len(entries)
            entries.append((session_index, slot_id, exercise))
    if not entries:
        raise AuthoredAllocationInfeasible("No authored source slots to place")

    parent = list(range(len(entries)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def join(left, right):
        parent[find(right)] = find(left)

    groups = {}
    rest_rules = {}
    for _, slot_id, exercise in entries:
        for relation in exercise.get("source_relationships") or []:
            if not isinstance(relation, dict):
                raise AuthoredAllocationInfeasible("Malformed authored relationship")
            if not relation.get("hard"):
                continue
            if relation.get("kind") not in {"superset", "primer"}:
                if selected_dates is None:
                    continue  # Preserve the legacy count-only relationship boundary.
                if relation.get("kind") in {"warmup_to_working", "technique_child"}:
                    parents = relation.get("source_set_ids") or []
                    source_sets = {item.get("source_set_id") for item in (exercise.get("authored_prescription") or {}).get("sets") or []}
                    if (not relation.get("group_id") or relation.get("source_slot_ids") != [slot_id]
                            or not isinstance(parents, list) or not set(parents) <= source_sets
                            or (relation["kind"] == "technique_child" and len(parents) != 1)):
                        raise AuthoredAllocationInfeasible(f"Malformed authored internal source-set relationship: {relation.get('group_id')}")
                    continue  # Moving the complete owning slot retains warm-ups and technique children.
                if relation.get("kind") != "minimum_rest":
                    raise AuthoredAllocationInfeasible(f"Unsupported authored hard relationship: {relation.get('kind')}")
                members = tuple(relation.get("source_slot_ids") or [])
                group_id = str(relation.get("group_id") or "")
                rest = relation.get("minimum_rest_days")
                if not group_id or len(members) != 2 or slot_id not in members or type(rest) is not int or rest < 0:
                    raise AuthoredAllocationInfeasible("Malformed authored minimum rest relationship")
                signature = (members, rest)
                if rest_rules.setdefault(group_id, signature) != signature:
                    raise AuthoredAllocationInfeasible(f"Conflicting authored minimum rest relationship: {group_id}")
                continue
            group_id = str(relation.get("group_id") or "")
            members = tuple(relation.get("source_slot_ids") or [])
            if not group_id or len(members) < 2 or slot_id not in members:
                raise AuthoredAllocationInfeasible("Malformed authored hard relationship")
            if any(member not in by_slot for member in members):
                raise AuthoredAllocationInfeasible(f"Incomplete authored hard relationship: {group_id}")
            signature = (relation["kind"], members)
            previous = groups.setdefault(group_id, signature)
            if previous != signature:
                raise AuthoredAllocationInfeasible(f"Conflicting authored hard relationship: {group_id}")
    for group_id, (kind, members) in groups.items():
        if any(not any(
            r.get("kind") == kind and r.get("hard") is True
            and r.get("group_id") == group_id
            and tuple(r.get("source_slot_ids") or []) == members
            for r in entries[by_slot[member]][2].get("source_relationships") or []
        ) for member in members):
            raise AuthoredAllocationInfeasible(f"Unreciprocated authored hard relationship: {group_id}")
        positions = sorted(by_slot[member] for member in members)
        # Keep intervening source work in order if a source link spans it.
        for index in range(positions[0], positions[-1]):
            join(index, index + 1)

    for group_id, (members, rest) in rest_rules.items():
        if any(member not in by_slot for member in members):
            raise AuthoredAllocationInfeasible(f"Incomplete authored minimum rest relationship: {group_id}")
        if by_slot[members[0]] >= by_slot[members[1]]:
            raise AuthoredAllocationInfeasible(f"Source order conflicts with minimum rest relationship: {group_id}")
        if any(not any(r.get("kind") == "minimum_rest" and r.get("hard") is True
                and r.get("group_id") == group_id and tuple(r.get("source_slot_ids") or []) == members
                and r.get("minimum_rest_days") == rest
                for r in entries[by_slot[member]][2].get("source_relationships") or []) for member in members):
            raise AuthoredAllocationInfeasible(f"Unreciprocated authored minimum rest relationship: {group_id}")

    units = []
    for index, (_, slot_id, exercise) in enumerate(entries):
        root = find(index)
        if units and units[-1]["root"] == root:
            units[-1]["exercises"].append(exercise)
            units[-1]["slots"].append(slot_id)
            units[-1]["sets"] += int(exercise.get("sets") or 0)
        else:
            units.append({"root": root, "exercises": [exercise], "slots": [slot_id], "sets": int(exercise.get("sets") or 0)})
    if len(units) < day_count:
        affected = [unit["slots"] for unit in units]
        raise AuthoredAllocationInfeasible(f"Hard relationships leave fewer units than target days: {len(units)} units for {day_count} days; source units {affected}")

    total_sets = sum(unit["sets"] for unit in units)
    targets = [total_sets // day_count + (index < total_sets % day_count) for index in range(day_count)]
    prefix_sets = [0]
    for unit in units:
        prefix_sets.append(prefix_sets[-1] + unit["sets"])

    # Each day receives a nonempty contiguous source range. This preserves
    # source order across the entire week, not merely within each session.
    best = None
    candidate_count = 0
    feasible_count = 0
    rest_rejections = 0
    candidates = combinations(range(1, len(units)), day_count - 1)
    if preserve_grouping:
        if len(source_sessions) != day_count or any(not session.get("exercises") for session in source_sessions):
            raise AuthoredAllocationInfeasible("Complete workout sessions cannot fit the selected date count")
        entry_boundaries = set()
        consumed = 0
        for session in source_sessions[:-1]:
            consumed += len(session["exercises"])
            entry_boundaries.add(consumed)
        fixed_cuts = []
        consumed = 0
        for index, unit in enumerate(units, 1):
            consumed += len(unit["exercises"])
            if consumed in entry_boundaries:
                fixed_cuts.append(index)
        if len(fixed_cuts) != day_count - 1:
            raise AuthoredAllocationInfeasible("Preserved grouping splits an authored hard relationship")
        candidates = [tuple(fixed_cuts)]
    for cuts in candidates:
        candidate_count += 1
        boundaries = (0, *cuts, len(units))
        actuals = [prefix_sets[boundaries[index + 1]] - prefix_sets[boundaries[index]] for index in range(day_count)]
        if any(
            adapted_days[index].get("max_working_sets") is not None
            and actuals[index] > int(adapted_days[index]["max_working_sets"])
            for index in range(day_count)
        ):
            continue
        if selected_dates is not None:
            slot_days = {slot_id: day_index for day_index in range(day_count)
                for unit in units[boundaries[day_index]:boundaries[day_index + 1]] for slot_id in unit["slots"]}
            if any((selected_dates[slot_days[members[1]]] - selected_dates[slot_days[members[0]]]).days - 1 < rest
                    for members, rest in rest_rules.values()):
                rest_rejections += 1
                continue
        feasible_count += 1
        score = (max(actuals) - min(actuals),
                 sum((actuals[index] - targets[index]) ** 2 for index in range(day_count)),
                 cuts)
        if selected_dates is not None:
            profiles = [_muscle_work([exercise for unit in units[boundaries[index]:boundaries[index + 1]] for exercise in unit["exercises"]])
                for index in range(day_count)]
            overlap = sum(_overlap(profiles[index], profiles[index + 1]) for index in range(day_count - 1)
                if (selected_dates[index + 1] - selected_dates[index]).days == 1)
            for context, index in ((previous_context, 0), (next_context, day_count - 1)):
                if context is not None and context.get("exercises") is not None and abs((context["date"] - selected_dates[index]).days) == 1:
                    overlap += _overlap(profiles[index], _muscle_work(context["exercises"]))
            score = (overlap, *score)
        if best is None or score < best[0]:
            best = (score, boundaries, actuals)
    if best is None:
        if rest_rejections:
            raise AuthoredAllocationInfeasible(f"Complete authored workload cannot fit explicit source minimum rest constraints on selected dates {[value.isoformat() for value in selected_dates]}; affected source groups {sorted(rest_rules)}")
        raise AuthoredAllocationInfeasible("Complete authored workload cannot fit hard target-day limits")
    _, boundaries, actuals = best

    sessions = []
    for day_index in range(day_count):
        day = adapted_days[day_index]
        selected = units[boundaries[day_index]:boundaries[day_index + 1]]
        sessions.append({
            "name": str(day.get("day_name") or f"Adapted Full Body #{day_index + 1}"),
            "day_role": str(day.get("day_role") or f"full_body_adapted_{day_index + 1}"),
            "day_offset": min(6, day_index),
            "exercises": [deepcopy(exercise) for unit in selected for exercise in unit["exercises"]],
        })
    trace = {
        "authored_adaptation_policy": "dose_preserving_redistribution",
        "authored_source_week_total_sets": total_sets,
        "authored_selected_day_count": day_count,
        "authored_redistributed_session_set_targets": targets,
        "authored_redistributed_session_set_actuals": actuals,
        "authored_redistribution_preserved_exercise_count": len(entries),
        "authored_redistribution_preserved_weekly_sets": sum(actuals),
        "authored_hard_relationship_count": len(groups),
        "authored_redistribution_notes": "Contiguous source-order ranges across the adapted week; hard relationships stay together.",
    }

    if selected_dates is not None:
        trace["selected_date_allocation"] = {
            "policy": deepcopy(DATE_OBJECTIVE),
            "candidate_count": candidate_count,
            "feasible_candidate_count": feasible_count,
            "minimum_rest_rejected_candidate_count": rest_rejections,
            "source_minimum_rest_rules": [{"group_id": group_id, "source_slot_ids": list(members), "minimum_rest_days": rest}
                for group_id, (members, rest) in sorted(rest_rules.items())],
            "selected_dates": [value.isoformat() for value in selected_dates],
            "gap_days": [(right - left).days for left, right in zip(selected_dates, selected_dates[1:])],
            "context_completeness": {side: "known" if context is not None and context.get("exercises") is not None else "unknown"
                for side, context in (("previous", previous_context), ("next", next_context))},
            "unknown_primary_muscle_slot_count": sum(not exercise.get("primary_muscles") for _, _, exercise in entries),
            "neighbor_unknown_primary_muscle_slot_counts": {side: sum(not exercise.get("primary_muscles") for exercise in context["exercises"])
                if context is not None and context.get("exercises") is not None else None
                for side, context in (("previous", previous_context), ("next", next_context))},
            "objective": {"consecutive_overlapping_working_sets": best[0][0], "working_set_range": best[0][1],
                "target_squared_deviation": best[0][2], "source_cuts": list(best[0][3])},
            "grouping": "preserved" if preserve_grouping else "allocated",
            "source_digest": sha256(json.dumps([entry[2] for entry in entries], sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest(),
            "rule_digest": sha256(json.dumps(DATE_OBJECTIVE, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        }
    return sessions, trace
