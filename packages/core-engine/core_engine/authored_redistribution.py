"""Deterministic, dose-preserving placement of authored source units.

This module changes session placement only. It owns no exercise selection,
substitution, set prescription, or date policy.
"""
from copy import deepcopy


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
    # Preserve the existing set-balancing behavior: whole source units move,
    # while their order within each destination day never changes.
    buckets = [{"sets": 0, "units": [], "first": len(units)} for _ in range(day_count)]
    for source_index, unit in enumerate(units):
        unit["source_index"] = source_index
        choices = []
        for index, bucket in enumerate(buckets):
            projected = bucket["sets"] + unit["sets"]
            maximum = adapted_days[index].get("max_working_sets")
            if maximum is not None and projected > int(maximum):
                continue
            choices.append((max(0, projected - targets[index]), abs(projected - targets[index]), bucket["sets"], index))
        if not choices:
            raise AuthoredAllocationInfeasible("Complete authored workload cannot fit hard target-day limits")
        index = min(choices)[-1]
        buckets[index]["sets"] += unit["sets"]
        buckets[index]["units"].append(unit)
        buckets[index]["first"] = min(buckets[index]["first"], source_index)
    if any(not bucket["units"] for bucket in buckets):
        raise AuthoredAllocationInfeasible("Hard relationships leave an empty target day")

    def balance_score():
        values = [bucket["sets"] for bucket in buckets]
        return max(values) - min(values), sum((value - targets[index]) ** 2 for index, value in enumerate(values))

    # Moving one whole unit can repair a greedy boundary imbalance without
    # changing the source order of any destination session or splitting links.
    for _ in range(len(units) * day_count):
        before = balance_score()
        best = None
        for source_index, source_bucket in enumerate(buckets):
            if len(source_bucket["units"]) <= 1:
                continue
            for unit in source_bucket["units"]:
                for target_index, target_bucket in enumerate(buckets):
                    if source_index == target_index:
                        continue
                    maximum = adapted_days[target_index].get("max_working_sets")
                    if maximum is not None and target_bucket["sets"] + unit["sets"] > int(maximum):
                        continue
                    source_bucket["sets"] -= unit["sets"]
                    target_bucket["sets"] += unit["sets"]
                    score = balance_score()
                    source_bucket["sets"] += unit["sets"]
                    target_bucket["sets"] -= unit["sets"]
                    candidate = (score, unit["source_index"], source_index, target_index)
                    if score < before and (best is None or candidate < best):
                        best = candidate
        if best is None:
            break
        _, unit_index, source_index, target_index = best
        source_bucket, target_bucket = buckets[source_index], buckets[target_index]
        unit = next(item for item in source_bucket["units"] if item["source_index"] == unit_index)
        source_bucket["units"].remove(unit)
        source_bucket["sets"] -= unit["sets"]
        target_bucket["units"].append(unit)
        target_bucket["units"].sort(key=lambda item: item["source_index"])
        target_bucket["sets"] += unit["sets"]
    for bucket in buckets:
        bucket["first"] = bucket["units"][0]["source_index"]
    bucket_order = sorted(range(day_count), key=lambda index: (buckets[index]["first"], index))

    sessions = []
    actuals = []
    for day_index, bucket_index in enumerate(bucket_order):
        day = adapted_days[day_index]
        selected = buckets[bucket_index]["units"]
        actuals.append(buckets[bucket_index]["sets"])
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
        "authored_redistribution_notes": "Source-order units within each adapted day; hard relationships stay together.",
    }
