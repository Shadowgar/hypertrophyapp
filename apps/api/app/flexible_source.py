"""Admitted native Authored sessions and declared mandatory-rest evidence.

This adapter has no calendar, frequency, generation, load or persistence policy.
It preserves the admitted loader's complete prescription and source order.
"""
from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import json

from core_engine.authored_prescription import uniform_rep_range

from .adaptive_schema import AuthoredPrescription
from .program_loader import load_program_template


AUTHORED_PROGRAMS = frozenset((
    "pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"))
COVERAGE_NOTICE = (
    "Source-rest coverage is limited to declared admitted relationships; absence "
    "of a minimum-rest rule does not establish complete source recovery coverage "
    "or scientifically qualified recovery safety.")


def _source_slots(items):
    slots, source_sets = {}, set()
    for item in items:
        exercises = item["session"].get("exercises")
        if not isinstance(exercises, list) or not exercises:
            raise ValueError("Native source session has no admitted exercises")
        for exercise in exercises:
            if not isinstance(exercise, dict):
                raise ValueError("Malformed native source exercise")
            slot_id = (exercise.get("source_lineage") or {}).get("source_slot_id")
            if not isinstance(slot_id, str) or not slot_id.strip() or slot_id in slots:
                raise ValueError("Missing or duplicate native source slot identity")
            prescription = exercise.get("authored_prescription")
            if not isinstance(prescription, dict):
                raise ValueError("Native source requires a typed prescription")
            AuthoredPrescription.model_validate(prescription)
            sets = prescription["sets"]
            if type(exercise.get("sets")) is not int or exercise["sets"] != len(sets):
                raise ValueError("Native working-set dose differs from typed prescription")
            if exercise.get("rep_range") != uniform_rep_range(prescription):
                raise ValueError("Native numeric compatibility differs from typed prescription")
            for prescribed in sets:
                identity = prescribed.get("source_set_id")
                if not isinstance(identity, str) or not identity.strip() or identity in source_sets:
                    raise ValueError("Missing or duplicate native source set identity")
                source_sets.add(identity)
            slots[slot_id] = (item["position"], exercise)
    return slots


def _mandatory_relationships(slots):
    groups = {}
    for slot_id, (_, exercise) in slots.items():
        relations = exercise.get("source_relationships") or []
        if not isinstance(relations, list):
            raise ValueError("Malformed native source relationships")
        for relation in relations:
            if not isinstance(relation, dict) or type(relation.get("hard", True)) is not bool:
                raise ValueError("Malformed native source relationship")
            if relation.get("hard", True) is False:
                continue
            kind, group = relation.get("kind"), relation.get("group_id")
            members = relation.get("source_slot_ids")
            if (not isinstance(group, str) or not group.strip() or not isinstance(members, list)
                    or not members or any(not isinstance(member, str) for member in members)
                    or len(set(members)) != len(members) or slot_id not in members
                    or any(member not in slots for member in members)):
                raise ValueError("Incomplete or malformed mandatory source relationship")
            if kind in {"warmup_to_working", "technique_child"}:
                parents = relation.get("source_set_ids") or []
                source_sets = {entry["source_set_id"] for entry in exercise["authored_prescription"]["sets"]}
                if (members != [slot_id] or not isinstance(parents, list)
                        or any(not isinstance(parent, str) or parent not in source_sets for parent in parents)
                        or (kind == "technique_child" and len(parents) != 1)):
                    raise ValueError("Malformed mandatory internal source-set relationship")
                signature = (kind, tuple(members), tuple(parents))
            elif kind in {"superset", "primer"}:
                if len(members) < 2 or len({slots[member][0] for member in members}) != 1:
                    raise ValueError("Native source grouping splits a mandatory relationship")
                signature = (kind, tuple(members))
            elif kind == "minimum_rest":
                rest = relation.get("minimum_rest_days")
                if (len(members) != 2 or type(rest) is not int or rest < 0
                        or slots[members[0]][0] >= slots[members[1]][0]):
                    raise ValueError("Invalid mandatory source-rest dose or sequence")
                signature = (kind, tuple(members), rest)
            else:
                raise ValueError("Unknown mandatory source relationship kind")
            if group in groups and groups[group][0] != signature:
                raise ValueError("Conflicting mandatory source relationship declarations")
            stored = groups.setdefault(group, (signature, set()))
            if slot_id in stored[1]:
                raise ValueError("Duplicate mandatory source relationship declaration")
            stored[1].add(slot_id)
    rest_rules = []
    for group, (signature, declarations) in sorted(groups.items()):
        kind, members = signature[:2]
        if declarations != set(members):
            raise ValueError("Unreciprocated mandatory source relationship")
        if kind == "minimum_rest":
            rest_rules.append({"kind": kind, "group_id": group, "source_slot_ids": list(members),
                "minimum_rest_days": signature[2], "source_positions": [slots[member][0] for member in members]})
    return rest_rules


def native_source(program_id: str) -> dict:
    """Freeze complete native sessions using global source ordinals, never dates."""
    if program_id not in AUTHORED_PROGRAMS:
        raise ValueError("Flexible native source requires a distinct Authored program")
    admitted = load_program_template(program_id)
    if admitted.get("id") != program_id:
        raise ValueError("Admitted source program binding differs")
    weeks = admitted.get("authored_weeks")
    if not isinstance(weeks, list) or not weeks:
        raise ValueError("Admitted native source weeks are missing")
    items = []
    for ordinal, week in enumerate(weeks, 1):
        if not isinstance(week, dict) or type(week.get("week_index")) is not int or week["week_index"] != ordinal:
            raise ValueError("Native source requires consecutive global week ordinals")
        sessions = week.get("sessions")
        if not isinstance(sessions, list) or not sessions:
            raise ValueError("Admitted native source sessions are missing")
        for session_index, session in enumerate(sessions, 1):
            if not isinstance(session, dict):
                raise ValueError("Malformed native source session")
            items.append({"position": len(items), "source_week": ordinal,
                "source_session": session_index, "session": deepcopy(session)})
    rest_rules = _mandatory_relationships(_source_slots(items))
    digest = sha256(json.dumps(admitted, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
    return {"program_id": program_id, "source_digest": digest, "items": items,
        "rest_rules": rest_rules, "coverage_notice": COVERAGE_NOTICE}


def evaluate_rest(source_catalog: dict, current_position: int,
        actual_days: dict[str, list[date]], local_day: date) -> dict:
    """Evaluate only declared incoming mandatory edges against actual evidence.

    Dates are local calendar dates; the gap must contain the declared number of
    full intervening days. Unknown evidence never acquires a fabricated anchor.
    """
    if type(local_day) is not date:
        raise ValueError("Rest evaluation requires an explicit local calendar date")
    blockers, earliest, unknown = [], local_day, False
    try:
        items = source_catalog["items"]
        if type(current_position) is not int or not 0 <= current_position < len(items):
            raise ValueError("Invalid current source position")
        rules = _mandatory_relationships(_source_slots(items))
        if source_catalog.get("rest_rules") != rules:
            raise ValueError("Mandatory source-rest catalog differs from admitted relationships")
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return {"blockers": [{"code": "source_admission_conflict", "reason": str(exc)}], "earliest_day": None}
    for rule in rules:
        if rule["source_positions"][1] != current_position:
            continue
        before = rule["source_slot_ids"][0]
        days = actual_days.get(before) if isinstance(actual_days, dict) else None
        details = {"group_id": rule["group_id"], "source_slot_ids": list(rule["source_slot_ids"])}
        if (not isinstance(days, list) or not days
                or any(type(day) is not date or day > local_day for day in days)):
            unknown = True
            blockers.append({"code": "mandatory_evidence_unknown", **details})
            continue
        try:
            eligible = max(days) + timedelta(days=rule["minimum_rest_days"] + 1)
        except OverflowError:
            unknown = True
            blockers.append({"code": "mandatory_evidence_unknown", **details})
            continue
        earliest = max(earliest, eligible)
        if eligible > local_day:
            blockers.append({"code": "hard_rest_wait", **details, "earliest_day": eligible.isoformat()})
    return {"blockers": blockers, "earliest_day": None if unknown else earliest.isoformat()}
