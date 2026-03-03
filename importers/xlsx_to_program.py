#!/usr/bin/env python3
"""Build-time importer for converting XLSX templates into canonical program JSON.

Runtime services must never read XLSX/PDF. This script is explicitly build-time only.
"""

import argparse
from dataclasses import dataclass
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


@dataclass(slots=True)
class ParsedSheet:
    name: str
    rows: list[list[str]]


@dataclass(slots=True)
class SessionParseState:
    sessions: list[dict]
    current_session_name: str | None
    current_exercises: list[dict]


def infer_equipment_tags_from_name(exercise_name: str) -> list[str]:
    tags: list[str] = []
    for pattern, equipment_tag in _EQUIPMENT_RULES:
        if pattern.search(exercise_name) and equipment_tag not in tags:
            tags.append(equipment_tag)
    return tags


def infer_movement_pattern(exercise_name: str) -> str | None:
    normalized = exercise_name.lower()
    rules: tuple[tuple[tuple[str, ...], str], ...] = (
        (("bench", "press"), "horizontal_press"),
        (("shoulder press", "overhead"), "vertical_press"),
        (("row",), "horizontal_pull"),
        (("pulldown", "pull-up", "chin-up"), "vertical_pull"),
        (("squat", "leg press", "split squat"), "squat"),
        (("rdl", "deadlift", "hinge", "hyperextension"), "hinge"),
        (("lunge",), "lunge"),
        (("calf",), "calf_raise"),
        (("lateral raise",), "lateral_raise"),
        (("curl",), "curl"),
        (("triceps", "extension", "pushdown"), "triceps_extension"),
    )
    for keywords, pattern in rules:
        if any(keyword in normalized for keyword in keywords):
            return pattern
    return None


def infer_primary_muscles(movement_pattern: str | None) -> list[str]:
    mapping: dict[str, list[str]] = {
        "horizontal_press": ["chest", "triceps", "front_delts"],
        "vertical_press": ["front_delts", "triceps"],
        "horizontal_pull": ["lats", "mid_back", "biceps"],
        "vertical_pull": ["lats", "biceps"],
        "squat": ["quads", "glutes"],
        "hinge": ["hamstrings", "glutes", "erectors"],
        "lunge": ["quads", "glutes"],
        "calf_raise": ["calves"],
        "lateral_raise": ["side_delts"],
        "curl": ["biceps"],
        "triceps_extension": ["triceps"],
    }
    if movement_pattern is None:
        return []
    return mapping.get(movement_pattern, [])


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "exercise"


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
        "working_sets": find_index("working", "sets"),
        "reps": find_index("reps"),
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


def _read_shared_strings(workbook_zip: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook_zip.namelist():
        return []
    root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
    shared_strings: list[str] = []
    for item in root.findall("a:si", _NS):
        tokens = [node.text or "" for node in item.findall(".//a:t", _NS)]
        shared_strings.append("".join(tokens))
    return shared_strings


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


def _resolve_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
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
    return raw


def _parse_sheet_rows(sheet_xml: bytes, shared_strings: list[str]) -> list[list[str]]:
    sheet_root = ET.fromstring(sheet_xml)
    rows: list[list[str]] = []
    for row in sheet_root.findall("a:sheetData/a:row", _NS):
        row_values: list[str] = []
        for cell in row.findall("a:c", _NS):
            col_index = _column_index_from_reference(cell.attrib.get("r", ""))
            while len(row_values) < col_index:
                row_values.append("")
            row_values.append(_resolve_cell_value(cell, shared_strings))
        rows.append(normalize_row(row_values))
    return rows


def read_xlsx_sheets(path: Path) -> list[ParsedSheet]:
    with zipfile.ZipFile(path) as workbook_zip:
        shared_strings = _read_shared_strings(workbook_zip)
        targets = _read_sheet_targets(workbook_zip)
        sheets: list[ParsedSheet] = []
        for sheet_name, target in targets:
            if not target or target not in workbook_zip.namelist():
                continue
            rows = _parse_sheet_rows(workbook_zip.read(target), shared_strings)
            sheets.append(ParsedSheet(name=sheet_name, rows=rows))
        return sheets


def _find_header_index(rows: list[list[str]]) -> int:
    for idx, row in enumerate(rows):
        lowered = " ".join(value.lower() for value in row if value)
        if "exercise" in lowered and "working sets" in lowered and "reps" in lowered:
            return idx
    return -1


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


def _parse_exercise_row(row: list[str], mapped: dict[str, int], exercise_idx: int) -> dict | None:
    exercise_name = column_value(row, exercise_idx)
    if not exercise_name:
        return None

    movement_pattern = infer_movement_pattern(exercise_name)
    return normalize_slot_exercise(
        {
            "id": slugify(exercise_name),
            "name": exercise_name,
            "sets": parse_int(column_value(row, mapped["working_sets"]), fallback=3),
            "rep_range": parse_rep_range(column_value(row, mapped["reps"])),
            "start_weight": 20,
            "movement_pattern": movement_pattern,
            "primary_muscles": infer_primary_muscles(movement_pattern),
            "substitution_candidates": _extract_substitution_candidates(row, mapped),
            "notes": pick_notes(row, mapped),
            "video": _extract_youtube_url(row, mapped),
        }
    )


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
    if session_candidate and not session_candidate.lower().startswith("week"):
        _flush_session(state)
        state.current_session_name = session_candidate

    if state.current_session_name is None:
        state.current_session_name = default_session_name

    parsed_exercise = _parse_exercise_row(row, mapped, exercise_idx)
    if parsed_exercise is not None:
        state.current_exercises.append(parsed_exercise)


def parse_sheet_to_sessions(sheet: ParsedSheet) -> list[dict]:
    header_row_index = _find_header_index(sheet.rows)
    if header_row_index < 0:
        return []

    header = sheet.rows[header_row_index]
    mapped = as_column_map(header)
    exercise_idx = mapped["exercise"]
    if exercise_idx < 0:
        return []

    state = SessionParseState(sessions=[], current_session_name=None, current_exercises=[])

    for raw_row in sheet.rows[header_row_index + 1 :]:
        row = normalize_row(raw_row)
        if not any(row):
            continue
        _process_session_row(state, row, mapped, exercise_idx, sheet.name)

    _flush_session(state)
    return state.sessions


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
    for sheet in selected_sheets:
        parsed_sessions.extend(parse_sheet_to_sessions(sheet))

    if not parsed_sessions:
        raise ValueError(
            "No session data parsed. Ensure the workbook contains columns like Exercise/Working Sets/Reps."
        )

    template = {
        "id": slugify(input_file.stem),
        "version": "1.0.0",
        "split": split_from_filename(input_file),
        "days_supported": [2, 3, 4],
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 35, "load_reduction_pct": 10},
        "progression": {"mode": "double_progression", "increment_kg": 2.5},
        "sessions": parsed_sessions,
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
