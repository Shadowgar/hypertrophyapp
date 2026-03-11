#!/usr/bin/env python3
"""Build-time importer for converting XLSX templates into canonical program JSON.

Runtime services must never read XLSX/PDF. This script is explicitly build-time only.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json
import re
import zipfile
from xml.etree import ElementTree as ET


_EQUIPMENT_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?:^|[^a-z0-9])d\.?b\.?($|[^a-z0-9])|\bdumbbell\b", re.IGNORECASE), "dumbbell"),
    (re.compile(r"(?:^|[^a-z0-9])b\.?b\.?($|[^a-z0-9])|\bbarbell\b", re.IGNORECASE), "barbell"),
    (re.compile(r"\bCABLE\b", re.IGNORECASE), "cable"),
    (re.compile(r"\bMACHINE\b", re.IGNORECASE), "machine"),
    (re.compile(r"\bBW\b|\bBODYWEIGHT\b", re.IGNORECASE), "bodyweight"),
)

_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

_YOUTUBE_URL_RE = re.compile(r"https?://[^\s\"]*(?:youtube\.com|youtu\.be)[^\s\"]*", re.IGNORECASE)
_SESSION_META_LABELS = {
    "warm up protocol",
    "weak point table",
    "weak points table",
}
_EXERCISE_META_LABELS = {
    "warm up protocol",
    "weak point table",
    "weak points table",
    "mandatory rest day",
}
_SPLIT_DAY_LABEL_RE = re.compile(r"^(?:full\s*body|upper|lower|push|pull|legs?)\s*#?\s*\d+$", re.IGNORECASE)
_BLOCK_PREFIX = "block "
_PHASE_PREFIX = "phase "
_EXCEL_DATE_EPOCH = datetime(1899, 12, 30)
_EXERCISE_PREFIX_RE = re.compile(r"^(?:(?:superset)\s+)?[a-z]\d+\s*:\s*", re.IGNORECASE)
_EXERCISE_METADATA_OVERRIDES: dict[str, dict[str, object]] = {
    "cross_body_lat_pull_around": {
        "movement_pattern": "vertical_pull",
        "primary_muscles": ["lats"],
        "equipment_tags": ["cable"],
    },
    "low_incline_smith_machine_press": {
        "movement_pattern": "horizontal_press",
        "primary_muscles": ["chest", "triceps", "front_delts"],
        "equipment_tags": ["machine"],
    },
    "machine_hip_adduction": {
        "movement_pattern": "hip_adduction",
        "primary_muscles": ["adductors"],
        "equipment_tags": ["machine"],
    },
    "leg_press": {
        "movement_pattern": "squat",
        "primary_muscles": ["quads", "glutes"],
        "equipment_tags": ["machine"],
    },
    "lying_paused_rope_face_pull": {
        "movement_pattern": "horizontal_pull",
        "primary_muscles": ["rear_delts", "upper_back"],
        "equipment_tags": ["cable"],
    },
    "seated_db_shoulder_press": {
        "movement_pattern": "vertical_press",
        "primary_muscles": ["front_delts", "triceps"],
        "equipment_tags": ["dumbbell"],
    },
    "paused_barbell_rdl": {
        "movement_pattern": "hinge",
        "primary_muscles": ["hamstrings", "glutes", "erectors"],
        "equipment_tags": ["barbell"],
    },
    "chest_supported_machine_row": {
        "movement_pattern": "horizontal_pull",
        "primary_muscles": ["lats", "mid_back", "biceps"],
        "equipment_tags": ["machine"],
    },
    "hammer_preacher_curl": {
        "movement_pattern": "curl",
        "primary_muscles": ["biceps", "brachialis"],
        "equipment_tags": ["dumbbell"],
    },
    "cuffed_behind_the_back_lateral_raise": {
        "movement_pattern": "lateral_raise",
        "primary_muscles": ["side_delts"],
        "equipment_tags": ["cable"],
    },
    "assisted_pull_up": {
        "movement_pattern": "vertical_pull",
        "primary_muscles": ["lats", "biceps"],
        "equipment_tags": ["bodyweight", "machine"],
    },
    "paused_assisted_dip": {
        "movement_pattern": "horizontal_press",
        "primary_muscles": ["chest", "triceps", "front_delts"],
        "equipment_tags": ["bodyweight", "machine"],
    },
    "seated_leg_curl": {
        "movement_pattern": "leg_curl",
        "primary_muscles": ["hamstrings"],
        "equipment_tags": ["machine"],
    },
    "lying_leg_curl": {
        "movement_pattern": "leg_curl",
        "primary_muscles": ["hamstrings"],
        "equipment_tags": ["machine"],
    },
    "leg_extension": {
        "movement_pattern": "knee_extension",
        "primary_muscles": ["quads"],
        "equipment_tags": ["machine"],
    },
    "cable_paused_shrug_in": {
        "movement_pattern": "shrug",
        "primary_muscles": ["traps"],
        "equipment_tags": ["cable"],
    },
    "roman_chair_leg_raise": {
        "movement_pattern": "core",
        "primary_muscles": ["abs"],
        "equipment_tags": ["bodyweight"],
    },
    "bent_over_cable_pec_flye": {
        "movement_pattern": "chest_fly",
        "primary_muscles": ["chest"],
        "equipment_tags": ["cable"],
    },
    "neutral_grip_lat_pulldown": {
        "movement_pattern": "vertical_pull",
        "primary_muscles": ["lats", "biceps"],
        "equipment_tags": ["cable"],
    },
    "leg_press_calf_press": {
        "movement_pattern": "plantar_flexion",
        "primary_muscles": ["calves"],
        "equipment_tags": ["machine"],
    },
    "cable_reverse_flye": {
        "movement_pattern": "reverse_flye",
        "primary_muscles": ["rear_delts", "upper_back"],
        "equipment_tags": ["cable"],
    },
    "bayesian_cable_curl": {
        "movement_pattern": "curl",
        "primary_muscles": ["biceps"],
        "equipment_tags": ["cable"],
    },
    "triceps_pressdown_bar": {
        "movement_pattern": "triceps_extension",
        "primary_muscles": ["triceps"],
        "equipment_tags": ["cable"],
    },
    "constant_tension_preacher_curl": {
        "movement_pattern": "curl",
        "primary_muscles": ["biceps"],
        "equipment_tags": ["machine"],
    },
    "cable_triceps_kickback": {
        "movement_pattern": "triceps_extension",
        "primary_muscles": ["triceps"],
        "equipment_tags": ["cable"],
    },
    "standing_calf_raise": {
        "movement_pattern": "plantar_flexion",
        "primary_muscles": ["calves"],
        "equipment_tags": ["machine"],
    },
}


@dataclass(slots=True)
class ParsedSheet:
    name: str
    rows: list[list[str]]


@dataclass(slots=True)
class SessionParseState:
    sessions: list[dict]
    current_session_name: str | None
    current_exercises: list[dict]


@dataclass(slots=True)
class ImportDiagnostic:
    sheet_name: str
    row_index: int | None
    code: str
    message: str

    def as_dict(self) -> dict:
        return {
            "sheet_name": self.sheet_name,
            "row_index": self.row_index,
            "code": self.code,
            "message": self.message,
        }


@dataclass(slots=True)
class ParsedSheetResult:
    sessions: list[dict]
    diagnostics: list[ImportDiagnostic]


@dataclass(slots=True)
class StructuredWeek:
    week_index: int
    sessions: list[dict]


@dataclass(slots=True)
class StructuredPhase:
    phase_id: str
    phase_name: str
    weeks: list[StructuredWeek]


@dataclass(slots=True)
class ParsedStructuredSheetResult:
    phases: list[StructuredPhase]
    diagnostics: list[ImportDiagnostic]


def _exercise_metadata_override(exercise_name: str) -> dict[str, object]:
    return _EXERCISE_METADATA_OVERRIDES.get(slugify(normalize_exercise_name(exercise_name)), {})


def infer_equipment_tags_from_name(exercise_name: str) -> list[str]:
    tags: list[str] = [str(tag) for tag in (_exercise_metadata_override(exercise_name).get("equipment_tags") or [])]
    for pattern, equipment_tag in _EQUIPMENT_RULES:
        if pattern.search(exercise_name) and equipment_tag not in tags:
            tags.append(equipment_tag)
    return tags


def infer_movement_pattern(exercise_name: str) -> str | None:
    override = _exercise_metadata_override(exercise_name)
    if override.get("movement_pattern"):
        return str(override["movement_pattern"])

    normalized = exercise_name.lower()
    rules: tuple[tuple[tuple[str, ...], str], ...] = (
        (("shoulder press", "overhead"), "vertical_press"),
        (("squat", "leg press", "split squat"), "squat"),
        (("triceps", "pushdown", "extension"), "triceps_extension"),
        (("pulldown", "pull-up", "chin-up", "pull around"), "vertical_pull"),
        (("row", "face pull"), "horizontal_pull"),
        (("rdl", "deadlift", "hinge", "hyperextension"), "hinge"),
        (("lunge",), "lunge"),
        (("calf",), "plantar_flexion"),
        (("lateral raise",), "lateral_raise"),
        (("curl",), "curl"),
        (("bench", "press", "dip"), "horizontal_press"),
    )
    for keywords, pattern in rules:
        if any(keyword in normalized for keyword in keywords):
            return pattern
    return None


def infer_primary_muscles(movement_pattern: str | None, exercise_name: str | None = None) -> list[str]:
    if exercise_name:
        override = _exercise_metadata_override(exercise_name)
        if override.get("primary_muscles"):
            return [str(muscle) for muscle in override["primary_muscles"]]

    mapping: dict[str, list[str]] = {
        "horizontal_press": ["chest", "triceps", "front_delts"],
        "vertical_press": ["front_delts", "triceps"],
        "horizontal_pull": ["lats", "mid_back", "biceps"],
        "vertical_pull": ["lats", "biceps"],
        "squat": ["quads", "glutes"],
        "hinge": ["hamstrings", "glutes", "erectors"],
        "lunge": ["quads", "glutes"],
        "plantar_flexion": ["calves"],
        "lateral_raise": ["side_delts"],
        "curl": ["biceps"],
        "triceps_extension": ["triceps"],
        "leg_curl": ["hamstrings"],
        "knee_extension": ["quads"],
        "core": ["abs"],
        "hip_adduction": ["adductors"],
        "shrug": ["traps"],
        "reverse_flye": ["rear_delts", "upper_back"],
        "chest_fly": ["chest"],
    }
    if movement_pattern is None:
        return []
    return mapping.get(movement_pattern, [])


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "exercise"


def normalize_exercise_name(raw_value: str) -> str:
    return _EXERCISE_PREFIX_RE.sub("", raw_value).strip()


def parse_rep_range(raw_value: str) -> list[int]:
    values = [int(match) for match in re.findall(r"\d+", raw_value)]
    if len(values) >= 2:
        lower, upper = sorted((values[0], values[1]))
        return [lower, upper]
    if len(values) == 1:
        return [values[0], values[0]]
    return [8, 12]


def parse_int(raw_value: str, fallback: int) -> int:
    match = re.search(r"\d+", raw_value)
    if not match:
        return fallback
    return int(match.group(0))


def parse_float(raw_value: str) -> float | None:
    values = [float(match) for match in re.findall(r"\d+(?:\.\d+)?", raw_value)]
    if not values:
        return None
    bounded = [value for value in values if 0 < value <= 10]
    if not bounded:
        return None
    if len(bounded) >= 2:
        return round((bounded[0] + bounded[1]) / 2, 1)
    return bounded[0]


def normalize_row(row: list[str]) -> list[str]:
    return [cell.strip() for cell in row]


def as_column_map(header: list[str]) -> dict[str, int]:
    normalized = [cell.lower() for cell in header]

    def find_index(*keywords: str) -> int:
        for idx, label in enumerate(normalized):
            if all(keyword in label for keyword in keywords):
                return idx
        return -1

    def find_any_index(*keywords: str) -> int:
        for idx, label in enumerate(normalized):
            if any(keyword in label for keyword in keywords):
                return idx
        return -1

    return {
        "session": 0,
        "exercise": find_index("exercise"),
        "warmup_sets": find_index("warm", "sets"),
        "working_sets": find_index("working", "sets"),
        "reps": find_index("reps"),
        "load": find_any_index("load"),
        "percent_1rm": find_any_index("%1rm", "percent 1rm", "percentage 1rm"),
        "rpe": find_any_index("rpe", "rir"),
        "rest": find_any_index("rest"),
        "sub1": find_index("substitution", "option", "1"),
        "sub2": find_index("substitution", "option", "2"),
        "video": find_any_index("youtube", "video", "url", "link"),
    }


def column_value(row: list[str], index: int) -> str:
    if index < 0 or index >= len(row):
        return ""
    return row[index].strip()


def pick_notes(row: list[str], mapped: dict[str, int]) -> str | None:
    used_columns = {index for index in mapped.values() if index >= 0}
    trailing_values = [
        value
        for idx, value in enumerate(row)
        if idx not in used_columns and value.strip() and re.search(r"[A-Za-z]", value)
    ]
    if not trailing_values:
        return None
    return " ".join(trailing_values)


def split_from_filename(path: Path) -> str:
    name = path.stem.lower()
    if "upper" in name and "lower" in name:
        return "upper_lower"
    if "ppl" in name or "push_pull_legs" in name:
        return "ppl"
    return "full_body"


def infer_days_supported(path: Path, split: str) -> list[int]:
    name = path.stem.lower()

    explicit_days = sorted(
        {
            int(match)
            for match in re.findall(r"(?:^|\D)(\d)(?:x|\s*days?)(?:\D|$)", name)
            if match.isdigit() and 2 <= int(match) <= 7
        }
    )
    if explicit_days:
        return explicit_days

    if split == "upper_lower":
        return [4]
    if split == "ppl":
        return [3, 4, 5, 6]
    return [2, 3, 4, 5]


def _read_shared_strings(workbook_zip: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook_zip.namelist():
        return []
    root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
    shared_strings: list[str] = []
    for item in root.findall("a:si", _NS):
        tokens = [node.text or "" for node in item.findall(".//a:t", _NS)]
        shared_strings.append("".join(tokens))
    return shared_strings


def _read_style_number_formats(workbook_zip: zipfile.ZipFile) -> dict[int, str]:
    if "xl/styles.xml" not in workbook_zip.namelist():
        return {}

    styles_root = ET.fromstring(workbook_zip.read("xl/styles.xml"))
    custom_numfmts = {
        int(node.attrib.get("numFmtId", "0")): node.attrib.get("formatCode", "")
        for node in styles_root.findall("a:numFmts/a:numFmt", _NS)
    }
    builtins = {
        14: "m/d/yyyy",
        15: "d-mmm-yy",
        16: "d-mmm",
        17: "mmm-yy",
        22: "m/d/yyyy h:mm",
    }
    custom_numfmts.update(builtins)

    cell_xfs = styles_root.find("a:cellXfs", _NS)
    if cell_xfs is None:
        return {}

    style_formats: dict[int, str] = {}
    for index, xf in enumerate(cell_xfs.findall("a:xf", _NS)):
        num_fmt_id = int(xf.attrib.get("numFmtId", "0"))
        if num_fmt_id in custom_numfmts:
            style_formats[index] = custom_numfmts[num_fmt_id]
    return style_formats


def _read_sheet_targets(workbook_zip: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook_root = ET.fromstring(workbook_zip.read("xl/workbook.xml"))
    rels_root = ET.fromstring(workbook_zip.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels_root.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
    }

    targets: list[tuple[str, str]] = []
    for sheet in workbook_root.findall("a:sheets/a:sheet", _NS):
        sheet_name = sheet.attrib.get("name", "Sheet")
        relation_id = sheet.attrib.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        target = rid_to_target.get(relation_id or "", "")
        if target and not target.startswith("xl/"):
            target = f"xl/{target}"
        targets.append((sheet_name, target))
    return targets


def _column_index_from_reference(reference: str) -> int:
    match = re.match(r"([A-Z]+)", reference)
    if not match:
        return 0
    col_index = 0
    for char in match.group(1):
        col_index = col_index * 26 + (ord(char) - 64)
    return max(col_index - 1, 0)


def _format_excel_date(raw: str, format_code: str) -> str:
    try:
        serial = float(raw)
    except ValueError:
        return raw

    dt = _EXCEL_DATE_EPOCH + timedelta(days=serial)
    normalized_format = format_code.lower().replace("\\", "")
    if "m-d" in normalized_format and "y" not in normalized_format:
        return f"{dt.month}-{dt.day}"
    return raw


def _resolve_cell_value(cell: ET.Element, shared_strings: list[str], style_number_formats: dict[int, str]) -> str:
    cell_type = cell.attrib.get("t")
    inline_node = cell.find("a:is/a:t", _NS)
    if inline_node is not None:
        return inline_node.text or ""

    value_node = cell.find("a:v", _NS)
    if value_node is None:
        return ""

    raw = value_node.text or ""
    if cell_type == "s" and raw.isdigit() and int(raw) < len(shared_strings):
        return shared_strings[int(raw)]
    style_index = cell.attrib.get("s")
    if style_index is not None:
        format_code = style_number_formats.get(int(style_index))
        if format_code:
            return _format_excel_date(raw, format_code)
    return raw


def _parse_sheet_rows(
    sheet_xml: bytes,
    shared_strings: list[str],
    style_number_formats: dict[int, str],
) -> list[list[str]]:
    sheet_root = ET.fromstring(sheet_xml)
    rows: list[list[str]] = []
    for row in sheet_root.findall("a:sheetData/a:row", _NS):
        row_values: list[str] = []
        for cell in row.findall("a:c", _NS):
            col_index = _column_index_from_reference(cell.attrib.get("r", ""))
            while len(row_values) < col_index:
                row_values.append("")
            row_values.append(_resolve_cell_value(cell, shared_strings, style_number_formats))
        rows.append(normalize_row(row_values))
    return rows


def read_xlsx_sheets(path: Path) -> list[ParsedSheet]:
    with zipfile.ZipFile(path) as workbook_zip:
        shared_strings = _read_shared_strings(workbook_zip)
        style_number_formats = _read_style_number_formats(workbook_zip)
        targets = _read_sheet_targets(workbook_zip)
        sheets: list[ParsedSheet] = []
        for sheet_name, target in targets:
            if not target or target not in workbook_zip.namelist():
                continue
            rows = _parse_sheet_rows(workbook_zip.read(target), shared_strings, style_number_formats)
            sheets.append(ParsedSheet(name=sheet_name, rows=rows))
        return sheets


def _find_header_index(rows: list[list[str]]) -> int:
    best_index = -1
    best_score = -1
    for idx, row in enumerate(rows):
        normalized = [_normalize_label(value) for value in row if value.strip()]
        if not normalized:
            continue

        has_exercise = any(label == "exercise" for label in normalized)
        has_working_sets = any("working sets" in label for label in normalized)
        has_reps = any(label == "reps" for label in normalized)
        if not (has_exercise and has_working_sets and has_reps):
            continue

        signal_tokens = (
            "last set intensity technique",
            "warm up sets",
            "early set rpe",
            "last set rpe",
            "rest",
            "substitution option 1",
            "substitution option 2",
            "notes",
        )
        score = sum(any(token in label for label in normalized) for token in signal_tokens)
        if score > best_score:
            best_score = score
            best_index = idx
    return best_index


def _extract_substitution_candidates(row: list[str], mapped: dict[str, int]) -> list[str]:
    return [
        candidate
        for candidate in [column_value(row, mapped["sub1"]), column_value(row, mapped["sub2"])]
        if candidate
    ]


def _extract_youtube_url(row: list[str], mapped: dict[str, int]) -> dict[str, str] | None:
    candidates: list[str] = []

    video_idx = mapped.get("video", -1)
    if video_idx >= 0:
        candidates.append(column_value(row, video_idx))

    candidates.extend(cell for cell in row if cell)
    for raw in candidates:
        match = _YOUTUBE_URL_RE.search(raw)
        if match:
            return {"youtube_url": match.group(0).strip()}
    return None


def _parse_set_type(exercise_name: str, notes: str | None) -> str:
    lowered = f"{exercise_name} {notes or ''}".lower()
    if "back off" in lowered or "backoff" in lowered or "back-off" in lowered:
        return "backoff"
    if "top set" in lowered or "top single" in lowered:
        return "top"
    return "work"


def _parse_load_target(row: list[str], mapped: dict[str, int]) -> str | None:
    for key in ("percent_1rm", "load"):
        raw_value = column_value(row, mapped.get(key, -1)).strip()
        if not raw_value or raw_value.upper() == "N/A":
            continue
        if re.fullmatch(r"\d{4,}(?:\.\d+)?", raw_value):
            continue
        return raw_value
    return None


def _parse_rest_seconds(raw_value: str) -> int | None:
    cleaned = raw_value.strip().lower()
    if not cleaned or re.fullmatch(r"\d{4,}(?:\.\d+)?", cleaned):
        return None

    values = [int(match) for match in re.findall(r"\d+", cleaned)]
    if not values:
        return None
    if "min" in cleaned:
        if len(values) >= 2:
            return int(((values[0] + values[1]) / 2) * 60)
        return values[0] * 60
    if "sec" in cleaned or cleaned.endswith("s"):
        return values[0]
    return None


def _parse_phase_label(*values: str) -> str | None:
    for value in values:
        normalized = _normalize_label(value)
        if normalized.startswith(_BLOCK_PREFIX) or normalized.startswith(_PHASE_PREFIX):
            return value.strip()
    return None


def _parse_week_index(*values: str) -> int | None:
    for value in values:
        match = re.search(r"week\s*(\d+)", value, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def _has_numeric_prescription(raw_value: str) -> bool:
    return bool(re.search(r"\d", raw_value))


def _is_structural_session_label(value: str) -> bool:
    normalized = _normalize_label(value)
    if not normalized:
        return True
    if normalized in _SESSION_META_LABELS:
        return True
    return (
        normalized.startswith("week ")
        or normalized.startswith(_BLOCK_PREFIX)
        or normalized.startswith(_PHASE_PREFIX)
        or normalized.startswith("semi deload")
        or normalized.startswith("deload week")
    )


def _is_structural_exercise_label(value: str) -> bool:
    normalized = _normalize_label(value)
    if not normalized:
        return True
    if normalized in _EXERCISE_META_LABELS:
        return True
    if normalized.startswith("week ") or normalized.startswith(_BLOCK_PREFIX) or normalized.startswith(_PHASE_PREFIX):
        return True
    if normalized.startswith("semi deload") or normalized.startswith("deload week"):
        return True
    if _SPLIT_DAY_LABEL_RE.match(normalized):
        return True
    return False


def _parse_exercise_row(row: list[str], mapped: dict[str, int], exercise_idx: int) -> dict | None:
    raw_exercise_name = column_value(row, exercise_idx)
    if not raw_exercise_name:
        return None

    if _is_structural_exercise_label(raw_exercise_name):
        return None
    exercise_name = normalize_exercise_name(raw_exercise_name)

    working_sets_raw = column_value(row, mapped["working_sets"])
    reps_raw = column_value(row, mapped["reps"])
    if not (_has_numeric_prescription(working_sets_raw) and _has_numeric_prescription(reps_raw)):
        return None

    movement_pattern = infer_movement_pattern(exercise_name)
    notes = pick_notes(row, mapped)
    return normalize_slot_exercise(
        {
            "id": slugify(exercise_name),
            "name": exercise_name,
            "sets": parse_int(working_sets_raw, fallback=3),
            "rep_range": parse_rep_range(reps_raw),
            "start_weight": 20,
            "movement_pattern": movement_pattern,
            "primary_muscles": infer_primary_muscles(movement_pattern, exercise_name),
            "substitution_candidates": _extract_substitution_candidates(row, mapped),
            "notes": notes,
            "video": _extract_youtube_url(row, mapped),
            "set_type": _parse_set_type(exercise_name, notes),
            "rpe_target": parse_float(column_value(row, mapped.get("rpe", -1))),
            "load_target": _parse_load_target(row, mapped),
            "warmup_sets": parse_int(column_value(row, mapped.get("warmup_sets", -1)), fallback=0),
            "rest_seconds": _parse_rest_seconds(column_value(row, mapped.get("rest", -1))),
        }
    )


def _phase_id_from_name(phase_name: str, fallback_index: int) -> str:
    phase_id = slugify(phase_name)
    return phase_id or f"phase_{fallback_index}"


def _append_structured_session(
    *,
    phases: list[StructuredPhase],
    phase_id: str,
    phase_name: str,
    week_index: int,
    session_name: str | None,
    exercises: list[dict],
) -> None:
    if not session_name or not exercises:
        return

    phase = next((item for item in phases if item.phase_id == phase_id), None)
    if phase is None:
        phase = StructuredPhase(phase_id=phase_id, phase_name=phase_name, weeks=[])
        phases.append(phase)

    week = next((item for item in phase.weeks if item.week_index == week_index), None)
    if week is None:
        week = StructuredWeek(week_index=week_index, sessions=[])
        phase.weeks.append(week)

    week.sessions.append({"name": session_name, "exercises": list(exercises)})


def _initial_phase_context(
    rows: list[list[str]],
    *,
    header_row_index: int,
    session_idx: int,
    exercise_idx: int,
    fallback_phase_name: str,
) -> tuple[str, str]:
    for scan_index in range(header_row_index, -1, -1):
        row = normalize_row(rows[scan_index])
        if not any(row):
            continue
        session_candidate = column_value(row, session_idx)
        exercise_name = column_value(row, exercise_idx)
        phase_label = _parse_phase_label(session_candidate, exercise_name)
        if phase_label:
            return phase_label, _phase_id_from_name(phase_label, 1)
    return fallback_phase_name, _phase_id_from_name(fallback_phase_name, 1)


def _transition_structured_context(
    *,
    session_candidate: str,
    exercise_name: str,
    current_phase_name: str,
    current_week_index: int,
    current_session_name: str | None,
    phase_count: int,
    flush: callable,
) -> tuple[str, str | None, int, str | None]:
    next_phase_name = current_phase_name
    next_phase_id: str | None = None
    next_week_index = current_week_index
    next_session_name = current_session_name

    phase_label = _parse_phase_label(session_candidate, exercise_name)
    week_index = _parse_week_index(session_candidate, exercise_name)

    if phase_label and phase_label != current_phase_name:
        flush()
        next_phase_name = phase_label
        next_phase_id = _phase_id_from_name(phase_label, phase_count + 1)
        if week_index is None:
            next_week_index = 1

    if week_index is not None and week_index != next_week_index:
        flush()
        next_week_index = week_index

    if session_candidate and not _is_structural_session_label(session_candidate) and next_session_name != session_candidate:
        flush()
        next_session_name = session_candidate

    return next_phase_name, next_phase_id, next_week_index, next_session_name


def _append_structured_skip_diagnostic(
    *,
    diagnostics: list[ImportDiagnostic],
    sheet_name: str,
    row_index: int,
    session_candidate: str,
    exercise_name: str,
) -> None:
    if exercise_name and _is_structural_exercise_label(exercise_name):
        diagnostics.append(
            _build_diagnostic(
                sheet_name,
                row_index,
                "structural_exercise_label_skipped",
                f"Structural exercise label '{exercise_name}' was ignored.",
            )
        )
        return

    if session_candidate and _is_structural_session_label(session_candidate):
        diagnostics.append(
            _build_diagnostic(
                sheet_name,
                row_index,
                "structural_session_label_skipped",
                f"Structural session label '{session_candidate}' was ignored.",
            )
        )


def _build_diagnostic(sheet_name: str, row_index: int | None, code: str, message: str) -> ImportDiagnostic:
    return ImportDiagnostic(sheet_name=sheet_name, row_index=row_index, code=code, message=message)


def _missing_header_result(sheet_name: str) -> ParsedSheetResult:
    return ParsedSheetResult(
        sessions=[],
        diagnostics=[
            _build_diagnostic(
                sheet_name,
                None,
                "missing_header",
                "Sheet skipped because no Exercise/Working Sets/Reps header row was found.",
            )
        ],
    )


def _missing_exercise_column_result(sheet_name: str, header_row_index: int) -> ParsedSheetResult:
    return ParsedSheetResult(
        sessions=[],
        diagnostics=[
            _build_diagnostic(
                sheet_name,
                header_row_index + 1,
                "missing_exercise_column",
                "Sheet skipped because the Exercise column could not be resolved from the header row.",
            )
        ],
    )


def _update_session_name(
    *,
    state: SessionParseState,
    diagnostics: list[ImportDiagnostic],
    sheet_name: str,
    row_index: int,
    session_candidate: str,
    exercise_name: str,
) -> None:
    if session_candidate and _is_structural_session_label(session_candidate):
        diagnostics.append(
            _build_diagnostic(
                sheet_name,
                row_index,
                "structural_session_label_skipped",
                f"Structural session label '{session_candidate}' was ignored.",
            )
        )

    if session_candidate and not _is_structural_session_label(session_candidate):
        if state.current_session_name != session_candidate:
            _flush_session(state)
            state.current_session_name = session_candidate

    if state.current_session_name is None:
        state.current_session_name = sheet_name
        if exercise_name and not _is_structural_exercise_label(exercise_name):
            diagnostics.append(
                _build_diagnostic(
                    sheet_name,
                    row_index,
                    "defaulted_session_name",
                    f"No session label found; defaulted session grouping to sheet name '{sheet_name}'.",
                )
            )


def _append_row_diagnostic(
    diagnostics: list[ImportDiagnostic],
    *,
    sheet_name: str,
    row_index: int,
    code: str,
    message: str,
) -> None:
    diagnostics.append(_build_diagnostic(sheet_name, row_index, code, message))


def _handle_exercise_row(
    *,
    state: SessionParseState,
    diagnostics: list[ImportDiagnostic],
    sheet_name: str,
    row_index: int,
    row: list[str],
    mapped: dict[str, int],
    exercise_idx: int,
) -> None:
    exercise_name = column_value(row, exercise_idx)
    if not exercise_name:
        return
    if _is_structural_exercise_label(exercise_name):
        _append_row_diagnostic(
            diagnostics,
            sheet_name=sheet_name,
            row_index=row_index,
            code="structural_exercise_label_skipped",
            message=f"Structural exercise label '{exercise_name}' was ignored.",
        )
        return

    working_sets_raw = column_value(row, mapped["working_sets"])
    reps_raw = column_value(row, mapped["reps"])
    if not _has_numeric_prescription(working_sets_raw):
        _append_row_diagnostic(
            diagnostics,
            sheet_name=sheet_name,
            row_index=row_index,
            code="missing_working_sets",
            message=f"Exercise '{exercise_name}' was skipped because Working Sets is missing or non-numeric.",
        )
        return
    if not _has_numeric_prescription(reps_raw):
        _append_row_diagnostic(
            diagnostics,
            sheet_name=sheet_name,
            row_index=row_index,
            code="missing_reps",
            message=f"Exercise '{exercise_name}' was skipped because Reps is missing or non-numeric.",
        )
        return

    parsed_exercise = _parse_exercise_row(row, mapped, exercise_idx)
    if parsed_exercise is not None:
        state.current_exercises.append(parsed_exercise)


def _flush_session(state: SessionParseState) -> None:
    if state.current_session_name and state.current_exercises:
        state.sessions.append(
            {
                "name": state.current_session_name,
                "exercises": state.current_exercises,
            }
        )
        state.current_exercises = []


def _process_session_row(
    state: SessionParseState,
    row: list[str],
    mapped: dict[str, int],
    exercise_idx: int,
    default_session_name: str,
) -> None:
    session_candidate = column_value(row, mapped["session"])
    if session_candidate and not _is_structural_session_label(session_candidate):
        _flush_session(state)
        state.current_session_name = session_candidate

    if state.current_session_name is None:
        state.current_session_name = default_session_name

    parsed_exercise = _parse_exercise_row(row, mapped, exercise_idx)
    if parsed_exercise is not None:
        state.current_exercises.append(parsed_exercise)


def parse_sheet_to_sessions(sheet: ParsedSheet) -> ParsedSheetResult:
    header_row_index = _find_header_index(sheet.rows)
    if header_row_index < 0:
        return _missing_header_result(sheet.name)

    header = sheet.rows[header_row_index]
    mapped = as_column_map(header)
    exercise_idx = mapped["exercise"]
    if exercise_idx < 0:
        return _missing_exercise_column_result(sheet.name, header_row_index)

    state = SessionParseState(sessions=[], current_session_name=None, current_exercises=[])
    diagnostics: list[ImportDiagnostic] = []

    for row_index, raw_row in enumerate(sheet.rows[header_row_index + 1 :], start=header_row_index + 2):
        row = normalize_row(raw_row)
        if not any(row):
            continue

        session_candidate = column_value(row, mapped["session"])
        exercise_name = column_value(row, exercise_idx)
        _update_session_name(
            state=state,
            diagnostics=diagnostics,
            sheet_name=sheet.name,
            row_index=row_index,
            session_candidate=session_candidate,
            exercise_name=exercise_name,
        )
        _handle_exercise_row(
            state=state,
            diagnostics=diagnostics,
            sheet_name=sheet.name,
            row_index=row_index,
            row=row,
            mapped=mapped,
            exercise_idx=exercise_idx,
        )

    _flush_session(state)
    return ParsedSheetResult(sessions=state.sessions, diagnostics=diagnostics)


def parse_sheet_to_structured_sessions(sheet: ParsedSheet) -> ParsedStructuredSheetResult:
    header_row_index = _find_header_index(sheet.rows)
    if header_row_index < 0:
        result = _missing_header_result(sheet.name)
        return ParsedStructuredSheetResult(phases=[], diagnostics=result.diagnostics)

    header = sheet.rows[header_row_index]
    mapped = as_column_map(header)
    exercise_idx = mapped["exercise"]
    if exercise_idx < 0:
        result = _missing_exercise_column_result(sheet.name, header_row_index)
        return ParsedStructuredSheetResult(phases=[], diagnostics=result.diagnostics)

    diagnostics: list[ImportDiagnostic] = []
    phases: list[StructuredPhase] = []
    current_phase_name, current_phase_id = _initial_phase_context(
        sheet.rows,
        header_row_index=header_row_index,
        session_idx=mapped["session"],
        exercise_idx=exercise_idx,
        fallback_phase_name=sheet.name,
    )
    current_week_index = 1
    current_session_name: str | None = None
    current_exercises: list[dict] = []

    def flush() -> None:
        nonlocal current_exercises
        _append_structured_session(
            phases=phases,
            phase_id=current_phase_id,
            phase_name=current_phase_name,
            week_index=current_week_index,
            session_name=current_session_name,
            exercises=current_exercises,
        )
        current_exercises = []

    for row_index, raw_row in enumerate(sheet.rows[header_row_index + 1 :], start=header_row_index + 2):
        row = normalize_row(raw_row)
        if not any(row):
            continue

        session_candidate = column_value(row, mapped["session"])
        exercise_name = column_value(row, exercise_idx)
        current_phase_name, phase_id_override, current_week_index, current_session_name = _transition_structured_context(
            session_candidate=session_candidate,
            exercise_name=exercise_name,
            current_phase_name=current_phase_name,
            current_week_index=current_week_index,
            current_session_name=current_session_name,
            phase_count=len(phases),
            flush=flush,
        )
        if phase_id_override is not None:
            current_phase_id = phase_id_override

        if current_session_name is None:
            current_session_name = sheet.name

        parsed_exercise = _parse_exercise_row(row, mapped, exercise_idx)
        if parsed_exercise is None:
            _append_structured_skip_diagnostic(
                diagnostics=diagnostics,
                sheet_name=sheet.name,
                row_index=row_index,
                session_candidate=session_candidate,
                exercise_name=exercise_name,
            )
            continue

        current_exercises.append(parsed_exercise)

    flush()
    return ParsedStructuredSheetResult(phases=phases, diagnostics=diagnostics)


def import_workbook(input_file: Path, output_file: Path | None = None, sheet_name: str | None = None) -> Path:
    sheets = read_xlsx_sheets(input_file)
    if not sheets:
        raise ValueError(f"No readable worksheets found in {input_file}")

    selected_sheets = sheets
    if sheet_name:
        selected_sheets = [sheet for sheet in sheets if sheet.name == sheet_name]
        if not selected_sheets:
            raise ValueError(f"Sheet '{sheet_name}' not found in {input_file.name}")

    parsed_sessions: list[dict] = []
    diagnostics: list[dict] = []
    for sheet in selected_sheets:
        parsed = parse_sheet_to_sessions(sheet)
        parsed_sessions.extend(parsed.sessions)
        diagnostics.extend(item.as_dict() for item in parsed.diagnostics)

    if not parsed_sessions:
        raise ValueError(
            "No session data parsed. Ensure the workbook contains columns like Exercise/Working Sets/Reps."
        )

    split = split_from_filename(input_file)
    template = {
        "id": slugify(input_file.stem),
        "version": "1.0.0",
        "source_workbook": str(input_file),
        "split": split,
        "days_supported": infer_days_supported(input_file, split),
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 35, "load_reduction_pct": 10},
        "progression": {"mode": "double_progression", "increment_kg": 2.5},
        "sessions": parsed_sessions,
        "import_diagnostics": {
            "status": "warnings" if diagnostics else "clean",
            "sheet_count": len(selected_sheets),
            "session_count": len(parsed_sessions),
            "diagnostic_count": len(diagnostics),
            "items": diagnostics,
        },
    }

    destination = output_file or Path("programs") / f"{slugify(input_file.stem)}_imported.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(template, indent=2), encoding="utf-8")
    return destination


def normalize_slot_exercise(raw_exercise: dict) -> dict:
    name = str(raw_exercise.get("name", "")).strip()
    explicit_tags = raw_exercise.get("equipment_tags") or []
    substitutions = raw_exercise.get("substitution_candidates") or raw_exercise.get("substitutions") or []

    return {
        "id": raw_exercise.get("id"),
        "primary_exercise_id": raw_exercise.get("primary_exercise_id") or raw_exercise.get("id"),
        "name": name,
        "sets": raw_exercise.get("sets", 3),
        "rep_range": raw_exercise.get("rep_range", [8, 12]),
        "start_weight": raw_exercise.get("start_weight", 20),
        "priority": raw_exercise.get("priority", "standard"),
        "movement_pattern": raw_exercise.get("movement_pattern"),
        "primary_muscles": raw_exercise.get("primary_muscles", []),
        "equipment_tags": list(dict.fromkeys(explicit_tags))
        if explicit_tags
        else infer_equipment_tags_from_name(name),
        "substitution_candidates": list(dict.fromkeys(substitutions)),
        "notes": raw_exercise.get("notes"),
        "video": raw_exercise.get("video"),
        "set_type": raw_exercise.get("set_type", "work"),
        "rpe_target": raw_exercise.get("rpe_target"),
        "load_target": raw_exercise.get("load_target"),
        "warmup_sets": raw_exercise.get("warmup_sets", 0),
        "rest_seconds": raw_exercise.get("rest_seconds"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert workout XLSX into canonical JSON template")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("reference/Edited PPL 5x.xlsx"),
        help="Path to XLSX file in reference folder",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (defaults to programs/<input>_imported.json)",
    )
    parser.add_argument(
        "--sheet",
        type=str,
        default=None,
        help="Optional specific sheet name to import",
    )
    args = parser.parse_args()

    output_file = import_workbook(args.input, args.output, args.sheet)
    print(f"Imported template written to: {output_file.resolve()}")
    print("No runtime dependency on reference files is allowed.")


if __name__ == "__main__":
    main()
