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
    return payload


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
                if key in {"authored_prescription", "source_lineage", "work_sets"} and item is not None:
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
