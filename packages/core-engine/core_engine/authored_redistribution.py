"""Deterministic, dose-preserving placement of authored source units.

This module changes session placement only. It owns no exercise selection,
substitution, set prescription, or date policy.
"""
from copy import deepcopy
from itertools import combinations


class AuthoredAllocationInfeasible(ValueError):
    """The requested placement cannot retain the complete authored workload."""


def redistribute_authored_sessions(source_sessions, adapted_days):
    day_count = len(adapted_days)
    if not source_sessions or day_count not in (2, 3, 4):
        raise AuthoredAllocationInfeasible("Authored redistribution needs source sessions and 2–4 target days")

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
    for _, slot_id, exercise in entries:
        for relation in exercise.get("source_relationships") or []:
            if relation.get("kind") not in {"superset", "primer"} or not relation.get("hard"):
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

    units = []
    for index, (_, _, exercise) in enumerate(entries):
        root = find(index)
        if units and units[-1]["root"] == root:
            units[-1]["exercises"].append(exercise)
            units[-1]["sets"] += int(exercise.get("sets") or 0)
        else:
            units.append({"root": root, "exercises": [exercise], "sets": int(exercise.get("sets") or 0)})
    if len(units) < day_count:
        raise AuthoredAllocationInfeasible("Hard relationships leave fewer units than target days")

    total_sets = sum(unit["sets"] for unit in units)
    targets = [total_sets // day_count + (index < total_sets % day_count) for index in range(day_count)]
    prefix_sets = [0]
    for unit in units:
        prefix_sets.append(prefix_sets[-1] + unit["sets"])

    # Each day receives a nonempty contiguous source range. This preserves
    # source order across the entire week, not merely within each session.
    best = None
    for cuts in combinations(range(1, len(units)), day_count - 1):
        boundaries = (0, *cuts, len(units))
        actuals = [prefix_sets[boundaries[index + 1]] - prefix_sets[boundaries[index]] for index in range(day_count)]
        if any(
            adapted_days[index].get("max_working_sets") is not None
            and actuals[index] > int(adapted_days[index]["max_working_sets"])
            for index in range(day_count)
        ):
            continue
        score = (max(actuals) - min(actuals),
                 sum((actuals[index] - targets[index]) ** 2 for index in range(day_count)),
                 cuts)
        if best is None or score < best[0]:
            best = (score, boundaries, actuals)
    if best is None:
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
    return sessions, {
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
