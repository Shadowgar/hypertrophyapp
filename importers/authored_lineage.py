"""Build-time source and compiler identity for authorized authored artifacts."""
from copy import deepcopy
import hashlib
import json
import re
from pathlib import Path

IMPORTER_VERSION = "authored-fidelity-1"


def compiler_sha256():
    root = Path(__file__).resolve().parents[1]
    paths = ["importers/xlsx_to_program.py", "importers/structured_program_builder.py",
             "importers/xlsx_to_program_v2.py", "importers/xlsx_to_onboarding_v2.py", "importers/compile_authored_fidelity.py", "importers/authored_lineage.py",
             "apps/api/app/adaptive_schema.py", "packages/core-engine/core_engine/authored_prescription.py"]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.encode() + b"\0" + (root / path).read_bytes() + b"\0")
    return digest.hexdigest()


def stamp_source(payload, input_file, *, sheet_name):
    provenance = {"source_sha256": hashlib.sha256(input_file.read_bytes()).hexdigest(),
        "source_name": input_file.name, "sheet": sheet_name,
        "importer_version": IMPORTER_VERSION, "importer_sha256": compiler_sha256(),
        "artifact_version": "0.3.0"}
    payload["version"] = provenance["artifact_version"]
    payload["source_provenance"] = provenance
    week_index = 0
    for phase in payload["phases"]:
        for week in phase["weeks"]:
            week_index += 1
            for day_index, day in enumerate(week["days"], 1):
                for slot in day["slots"]:
                    slot_id = f"{payload['program_id']}:w{week_index}:d{day_index}:s{slot['order_index']}"
                    slot["source_lineage"] = {**provenance, "source_program_id": payload["program_id"],
                        "source_week": week_index, "source_session": day_index,
                        "source_slot": slot["order_index"], "source_row": slot.get("source_row"),
                        "source_slot_id": slot_id}
                    for item in slot["authored_prescription"]["sets"]:
                        item["source_set_id"] = f"{slot_id}:set{item['set_index']}"
                annotate_source_relationships(day["slots"])
    return payload


def annotate_source_relationships(slots):
    """Compile only relationships stated by a source label or instruction.

    Cross-slot links use source-slot IDs, so repeated catalog exercises remain
    separate. Warm-up and technique links stay inside the owning slot/set.
    """
    for slot in slots:
        slot["source_relationships"] = []
        lineage = slot["source_lineage"]
        slot_id = lineage["source_slot_id"]
        prescribed = slot["authored_prescription"]["sets"]
        warmups = str(slot.get("warm_up_sets") or "").strip()
        if warmups and warmups.lower() not in {"n/a", "na", "none", "-"} and not re.fullmatch(r"[+-]?0+(?:[.,]0+)?", warmups):
            slot["source_relationships"].append({
                "kind": "warmup_to_working", "group_id": f"{slot_id}:warmup",
                "source_slot_ids": [slot_id],
                "source_set_ids": [item["source_set_id"] for item in prescribed],
                "role": "working_sets", "hard": True,
                "source_row": lineage["source_row"], "raw": warmups,
            })
        for item in prescribed:
            technique = item.get("intensity_technique")
            if technique and str(technique).strip().lower() not in {"n/a", "na", "none", "-"}:
                set_id = item["source_set_id"]
                slot["source_relationships"].append({
                    "kind": "technique_child", "group_id": f"{set_id}:technique",
                    "source_slot_ids": [slot_id], "source_set_ids": [set_id],
                    "role": "parent_working_set", "hard": True,
                    "source_row": lineage["source_row"], "raw": technique,
                })

    # A numbered pair label is source evidence, with or without "Superset".
    # Adjacency by itself is not.
    labeled = {}
    for slot in slots:
        match = re.match(r"^(?:superset\s+)?([a-z])(\d+)\s*:", str(slot.get("exercise") or ""), re.I)
        if match:
            labeled.setdefault(match[1].upper(), []).append((int(match[2]), slot, match[0].rstrip(":").strip()))
    for label, members in labeled.items():
        if len(members) % 2 or [number for number, _, _ in members] != [1, 2] * (len(members) // 2):
            raise ValueError(f"Incomplete authored superset {label}")
        for offset in range(0, len(members), 2):
            pair = members[offset:offset + 2]
            ids = [slot["source_lineage"]["source_slot_id"] for _, slot, _ in pair]
            for number, slot, raw in pair:
                slot["source_relationships"].append({
                    "kind": "superset", "group_id": f"{ids[0]}:superset:{label}",
                    "source_slot_ids": ids, "source_set_ids": [], "role": f"{label}{number}",
                    "hard": True, "source_row": slot["source_lineage"]["source_row"],
                    "raw": raw,
                })

    for index, slot in enumerate(slots[:-1]):
        notes = str(slot.get("notes") or "").lower()
        next_slot = slots[index + 1]
        target = re.sub(r"^superset\s+[a-z]\d+\s*:\s*", "", str(next_slot.get("exercise") or ""), flags=re.I).lower()
        target = re.sub(r"[^a-z0-9 ]", " ", target).strip()
        if not target or not re.search(r"warm(?:ed|ing)?\s+up\s+before", notes):
            continue
        # Match the named next exercise (allow source prose to pluralize it).
        words = target.split()
        if len(words) < 2 or not re.search(r"\bbefore\s+(?:the\s+)?" + re.escape(" ".join(words[:2])), notes):
            continue
        ids = [slot["source_lineage"]["source_slot_id"], next_slot["source_lineage"]["source_slot_id"]]
        for member, role in ((slot, "primer"), (next_slot, "primed_work")):
            member["source_relationships"].append({
                "kind": "primer", "group_id": f"{ids[0]}:primer",
                "source_slot_ids": ids, "source_set_ids": [], "role": role,
                "hard": True, "source_row": slot["source_lineage"]["source_row"],
                "raw": "source note: warm-up before named next exercise",
            })


def artifact_sha256(payload):
    copied = deepcopy(payload)
    copied["source_provenance"].pop("artifact_sha256", None)
    return hashlib.sha256(json.dumps(copied, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def artifact_json(payload):
    """Keep repeated typed records compact while preserving existing readable JSON.

    Formatting is not part of the canonical semantic hash.
    """
    replacements = {}
    assert "__authored_compact_record_" not in json.dumps(payload)
    def walk(value):
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if key in {"authored_prescription", "source_lineage", "source_relationships", "work_sets"} and item is not None:
                    token = "__authored_compact_record_" + str(len(replacements)) + "__"
                    replacements[token] = json.dumps(item, separators=(",", ":"))
                    result[key] = token
                else:
                    result[key] = walk(item)
            return result
        if isinstance(value, list):
            return [walk(item) for item in value]
        return value
    emitted = json.dumps(walk(payload), indent=2)
    emitted = re.sub(r'"(__authored_compact_record_\d+__)"', lambda match: replacements[match[1]], emitted)
    return emitted + "\n"
