from __future__ import annotations

from pathlib import Path
from typing import Any

from importers.xlsx_to_program import (
    infer_equipment_tags_from_name,
    parse_sheet_to_structured_sessions,
    parse_sheet_to_sessions,
    read_xlsx_sheets,
    slugify,
)


_WEAK_POINT_LABEL = "weak point"
_PRIMARY_COMPOUND_TOKENS = ("squat", "bench", "deadlift", "pull-up", "pulldown", "press", "row")
_SECONDARY_COMPOUND_TOKENS = ("split squat", "rdl", "leg press", "incline")
_ISOLATION_TOKENS = ("curl", "extension", "raise", "fly", "pushdown", "calf")
_DAY_ROLE_BY_NAME = {
    "full body #1": "full_body_1",
    "full body #2": "full_body_2",
    "full body #3": "full_body_3",
    "full body #4": "full_body_4",
    "arms & weak points": "weak_point_arms",
}


def collect_sessions_from_workbook(
    input_file: Path,
    *,
    sheet_name: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    sheets = read_xlsx_sheets(input_file)
    if not sheets:
        raise ValueError(f"No readable worksheets found in {input_file}")

    selected_sheets = sheets
    if sheet_name:
        selected_sheets = [sheet for sheet in sheets if sheet.name == sheet_name]
        if not selected_sheets:
            raise ValueError(f"Sheet '{sheet_name}' not found in {input_file.name}")

    sessions: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    selected_sheet_names: list[str] = []
    for sheet in selected_sheets:
        parsed = parse_sheet_to_sessions(sheet)
        sessions.extend(parsed.sessions)
        diagnostics.extend(item.as_dict() for item in parsed.diagnostics)
        selected_sheet_names.append(sheet.name)

    if not sessions:
        raise ValueError(
            "No session data parsed. Ensure the workbook contains columns like Exercise/Working Sets/Reps."
        )

    return sessions, diagnostics, selected_sheet_names


def collect_structured_phases_from_workbook(
    input_file: Path,
    *,
    sheet_name: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    sheets = read_xlsx_sheets(input_file)
    if not sheets:
        raise ValueError(f"No readable worksheets found in {input_file}")

    selected_sheets = sheets
    if sheet_name:
        selected_sheets = [sheet for sheet in sheets if sheet.name == sheet_name]
        if not selected_sheets:
            raise ValueError(f"Sheet '{sheet_name}' not found in {input_file.name}")

    phases: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    selected_sheet_names: list[str] = []
    for sheet in selected_sheets:
        parsed = parse_sheet_to_structured_sessions(sheet)
        phases.extend(
            {
                "phase_id": phase.phase_id,
                "phase_name": phase.phase_name,
                "weeks": [
                    {"week_index": week.week_index, "sessions": week.sessions}
                    for week in phase.weeks
                    if week.sessions
                ],
            }
            for phase in parsed.phases
            if any(week.sessions for week in phase.weeks)
        )
        diagnostics.extend(item.as_dict() for item in parsed.diagnostics)
        selected_sheet_names.append(sheet.name)

    return phases, diagnostics, selected_sheet_names


def default_program_name(program_id: str) -> str:
    return " ".join(part.capitalize() for part in program_id.replace("-", "_").split("_") if part)


def is_structural_session(session_name: str) -> bool:
    lowered = session_name.strip().lower()
    return lowered.startswith("warm up") or lowered.startswith(_WEAK_POINT_LABEL) or lowered.startswith("block ")


def is_rest_session(session_name: str) -> bool:
    return "rest" in session_name.strip().lower()


def slot_role(exercise_name: str, session_name: str) -> str:
    lowered = exercise_name.lower()
    if _WEAK_POINT_LABEL in lowered or _WEAK_POINT_LABEL in session_name.lower():
        return "weak_point"
    if any(token in lowered for token in _PRIMARY_COMPOUND_TOKENS):
        return "primary_compound"
    if any(token in lowered for token in _SECONDARY_COMPOUND_TOKENS):
        return "secondary_compound"
    if any(token in lowered for token in _ISOLATION_TOKENS):
        return "isolation"
    return "accessory"


def coaching_cues(notes: str | None) -> list[str]:
    if not notes:
        return []
    parts = [part.strip() for part in notes.replace("!", ".").split(".")]
    return [part for part in parts if part][:3]


def day_role(session_name: str) -> str | None:
    return _DAY_ROLE_BY_NAME.get(session_name.strip().lower())


def _normalized_rep_target(exercise: dict[str, Any]) -> dict[str, int]:
    rep_range = exercise.get("rep_range") or [8, 12]
    rep_min = int(rep_range[0]) if rep_range else 8
    rep_max = int(rep_range[1]) if len(rep_range) > 1 else rep_min
    rep_min, rep_max = sorted((rep_min, rep_max))
    return {"min": rep_min, "max": rep_max}


def _warmup_prescription(exercise: dict[str, Any]) -> list[dict[str, int]]:
    explicit_warmups = int(exercise.get("warmup_sets") or 0)
    if explicit_warmups > 0:
        templates: dict[int, list[dict[str, int]]] = {
            1: [{"percent": 60, "reps": 5}],
            2: [{"percent": 50, "reps": 8}, {"percent": 70, "reps": 5}],
            3: [{"percent": 45, "reps": 8}, {"percent": 65, "reps": 5}, {"percent": 80, "reps": 3}],
            4: [
                {"percent": 40, "reps": 8},
                {"percent": 55, "reps": 5},
                {"percent": 70, "reps": 3},
                {"percent": 85, "reps": 1},
            ],
        }
        return templates.get(explicit_warmups, templates[4][: min(explicit_warmups, 4)])

    movement_pattern = str(exercise.get("movement_pattern") or "")
    if movement_pattern in {"horizontal_press", "vertical_press", "horizontal_pull", "vertical_pull", "squat", "hinge"}:
        return [
            {"percent": 50, "reps": 8},
            {"percent": 70, "reps": 5},
            {"percent": 85, "reps": 2},
        ]
    return [
        {"percent": 50, "reps": 8},
        {"percent": 70, "reps": 5},
    ]


def _valid_sessions(session_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for session in session_rows:
        session_name = str(session.get("name") or "").strip()
        if not session_name or is_structural_session(session_name) or is_rest_session(session_name):
            continue
        valid.append(session)
    return valid


def _exercise_video(exercise: dict[str, Any]) -> dict[str, Any]:
    raw_video = exercise.get("video")
    return raw_video if isinstance(raw_video, dict) else {}


def _exercise_notes(exercise: dict[str, Any]) -> str | None:
    return exercise.get("notes") if isinstance(exercise.get("notes"), str) else None


def _exercise_primary_muscles(exercise: dict[str, Any]) -> list[str]:
    return [str(muscle) for muscle in (exercise.get("primary_muscles") or []) if str(muscle).strip()]


def _build_blueprint_slot(
    *,
    exercise: dict[str, Any],
    session_name: str,
    day_counter: int,
    order_index: int,
) -> dict[str, Any] | None:
    exercise_name = str(exercise.get("name") or "").strip()
    if not exercise_name:
        return None

    video = _exercise_video(exercise)
    notes = _exercise_notes(exercise)
    demo_url = str(exercise.get("demo_url") or video.get("youtube_url") or "") or None
    work_set = {
        "set_type": str(exercise.get("set_type") or "work"),
        "sets": int(exercise.get("sets") or 3),
        "rep_target": _normalized_rep_target(exercise),
        "rir_target": 2 if exercise.get("rpe_target") is None else None,
        "rpe_target": exercise.get("rpe_target"),
        "load_target": exercise.get("load_target"),
    }
    return {
        "slot_id": f"d{day_counter}_s{order_index}",
        "order_index": order_index,
        "exercise_id": str(exercise.get("primary_exercise_id") or exercise.get("id") or slugify(exercise_name)),
        "slot_role": slot_role(exercise_name, session_name),
        "primary_muscles": _exercise_primary_muscles(exercise),
        "exercise": str(exercise.get("exercise") or exercise_name),
        "last_set_intensity_technique": exercise.get("last_set_intensity_technique"),
        "warm_up_sets": exercise.get("warm_up_sets"),
        "working_sets": exercise.get("working_sets"),
        "reps": exercise.get("reps"),
        "early_set_rpe": exercise.get("early_set_rpe"),
        "last_set_rpe": exercise.get("last_set_rpe"),
        "rest": exercise.get("rest"),
        "tracking_set_1": exercise.get("tracking_set_1"),
        "tracking_set_2": exercise.get("tracking_set_2"),
        "tracking_set_3": exercise.get("tracking_set_3"),
        "tracking_set_4": exercise.get("tracking_set_4"),
        "substitution_option_1": exercise.get("substitution_option_1"),
        "substitution_option_2": exercise.get("substitution_option_2"),
        "demo_url": demo_url,
        "video_url": demo_url,
        "warmup_prescription": _warmup_prescription(exercise),
        "work_sets": [work_set],
        "notes": notes,
    }


def _build_blueprint_day(session: dict[str, Any], *, day_counter: int) -> dict[str, Any] | None:
    session_name = str(session.get("name") or "").strip()
    slots = [
        slot
        for order_index, exercise in enumerate(session.get("exercises") or [], start=1)
        for slot in [_build_blueprint_slot(exercise=exercise, session_name=session_name, day_counter=day_counter, order_index=order_index)]
        if slot is not None
    ]
    if not slots:
        return None
    return {
        "day_id": f"d{day_counter}",
        "day_name": session_name,
        "day_role": day_role(session_name),
        "slots": slots,
    }


def build_blueprint_week_template(
    session_rows: list[dict[str, Any]],
    *,
    week_template_id: str = "week_base",
) -> dict[str, Any]:
    days = [
        day
        for day_counter, session in enumerate(_valid_sessions(session_rows), start=1)
        for day in [_build_blueprint_day(session, day_counter=day_counter)]
        if day is not None
    ]

    return {"week_template_id": week_template_id, "days": days}


def build_week_templates_from_structured_phases(structured_phases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    templates: list[dict[str, Any]] = []
    for phase in structured_phases:
        phase_id = str(phase.get("phase_id") or "phase")
        for week in phase.get("weeks") or []:
            template = build_blueprint_week_template(
                week.get("sessions") or [],
                week_template_id=f"{phase_id}_week_{int(week.get('week_index') or len(templates) + 1)}",
            )
            if template["days"]:
                templates.append(template)
    return templates


def build_program_blueprint(
    *,
    program_id: str,
    program_name: str,
    source_workbook: str,
    split: str,
    total_weeks: int,
    session_rows: list[dict[str, Any]],
    structured_phases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    week_templates = build_week_templates_from_structured_phases(structured_phases or [])
    if len(week_templates) > 1:
        resolved_total_weeks = len(week_templates)
        week_sequence = [template["week_template_id"] for template in week_templates]
    else:
        week_template = build_blueprint_week_template(session_rows)
        week_templates = [week_template]
        resolved_total_weeks = total_weeks
        week_sequence = ["week_base" for _ in range(total_weeks)]

    return {
        "program_id": program_id,
        "program_name": program_name,
        "source_workbook": source_workbook,
        "split": split,
        "default_training_days": max(2, min(7, len(week_templates[0]["days"]) or 5)),
        "total_weeks": resolved_total_weeks,
        "week_sequence": week_sequence,
        "week_templates": week_templates,
    }


def _build_substitutions(exercise: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "exercise_id": slugify(str(candidate)),
            "rationale": "Workbook substitution option",
            "equipment_tags": infer_equipment_tags_from_name(str(candidate)),
        }
        for candidate in (exercise.get("substitution_candidates") or [])
        if str(candidate).strip()
    ]


def _build_exercise_library_entry(*, session_name: str, exercise: dict[str, Any]) -> dict[str, Any] | None:
    exercise_name = str(exercise.get("name") or "").strip()
    if not exercise_name:
        return None

    exercise_id = str(exercise.get("primary_exercise_id") or exercise.get("id") or slugify(exercise_name))
    notes = _exercise_notes(exercise) or ""
    movement_pattern = str(exercise.get("movement_pattern") or "accessory")
    video = _exercise_video(exercise)
    return {
        "exercise_id": exercise_id,
        "canonical_name": exercise_name,
        "aliases": [exercise_name],
        "execution": notes or "Execute with controlled tempo and full range of motion.",
        "coaching_cues": coaching_cues(notes),
        "primary_muscles": _exercise_primary_muscles(exercise),
        "secondary_muscles": [],
        "equipment_tags": infer_equipment_tags_from_name(exercise_name),
        "movement_pattern": movement_pattern,
        "valid_substitutions": _build_substitutions(exercise),
        "default_video_url": str(video.get("youtube_url") or "") or None,
        "slot_usage_rationale": f"Used in {session_name} to preserve session intent and progression continuity.",
    }


def build_exercise_library(session_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    entries: list[dict[str, Any]] = []

    for session in _valid_sessions(session_rows):
        session_name = str(session.get("name") or "")
        for exercise in session.get("exercises") or []:
            entry = _build_exercise_library_entry(session_name=session_name, exercise=exercise)
            if entry is None:
                continue
            exercise_id = str(entry["exercise_id"])
            if exercise_id in seen:
                continue
            seen.add(exercise_id)
            entries.append(entry)

    return entries


def _build_gold_work_sets(slot: dict[str, Any]) -> list[dict[str, Any]]:
    work_sets: list[dict[str, Any]] = []
    for work_set in slot.get("work_sets") or []:
        work_sets.append(
            {
                "set_type": str(work_set.get("set_type") or "work"),
                "sets": int(work_set.get("sets") or 1),
                "rep_target": {
                    "min": int(((work_set.get("rep_target") or {}).get("min") or 8)),
                    "max": int(((work_set.get("rep_target") or {}).get("max") or 12)),
                },
                "rir_target": int(work_set.get("rir_target")) if work_set.get("rir_target") is not None else None,
                "rpe_target": float(work_set.get("rpe_target")) if work_set.get("rpe_target") is not None else None,
                "load_target": str(work_set.get("load_target")) if work_set.get("load_target") else None,
            }
        )
    return work_sets


def _build_gold_day(day: dict[str, Any], *, week_index: int, day_index: int) -> dict[str, Any]:
    week_day_id = f"w{week_index}d{day_index}"
    slots = []
    for slot in day.get("slots") or []:
        order_index = int(slot.get("order_index") or len(slots) + 1)
        slots.append(
            {
                "slot_id": f"{week_day_id}_s{order_index}",
                "order_index": order_index,
                "exercise_id": str(slot.get("exercise_id") or "unknown_exercise"),
                "slot_role": slot.get("slot_role"),
                "video_url": slot.get("video_url"),
                "warmup_prescription": list(slot.get("warmup_prescription") or []),
                "work_sets": _build_gold_work_sets(slot),
                "notes": slot.get("notes"),
            }
        )

    return {
        "day_id": week_day_id,
        "day_name": str(day.get("day_name") or f"Day {day_index}"),
        "day_role": day.get("day_role"),
        "slots": slots,
    }


def _build_gold_week(week_template: dict[str, Any], *, week_index: int) -> dict[str, Any]:
    days = [
        _build_gold_day(day, week_index=week_index, day_index=day_index)
        for day_index, day in enumerate(week_template["days"], start=1)
    ]
    return {"week_index": week_index, "days": days}


def _infer_authored_week_role(phase_name: str, *, week_index_in_phase: int, total_phase_weeks: int) -> str | None:
    lowered = phase_name.strip().lower()
    if "build" in lowered:
        if week_index_in_phase <= min(2, total_phase_weeks):
            return "adaptation"
        return "accumulation"
    if "novelty" in lowered:
        return "intensification"
    if "deload" in lowered:
        return "deload"
    if "intens" in lowered:
        return "intensification"
    return None


def build_adaptive_gold_program_template(
    *,
    program_id: str,
    program_name: str,
    source_workbook: str,
    split: str,
    total_weeks: int,
    session_rows: list[dict[str, Any]],
    structured_phases: list[dict[str, Any]] | None = None,
    phase_id: str = "accumulation_1",
    phase_name: str = "Accumulation",
    version: str = "0.2.0",
) -> dict[str, Any]:
    authored_week_count = sum(len(phase.get("weeks") or []) for phase in (structured_phases or []))
    if structured_phases and authored_week_count > 1:
        emitted_phases = []
        for raw_phase in structured_phases:
            templates = build_week_templates_from_structured_phases([raw_phase])
            if not templates:
                continue
            raw_phase_name = str(raw_phase.get("phase_name") or phase_name)
            emitted_phases.append(
                {
                    "phase_id": str(raw_phase.get("phase_id") or phase_id),
                    "phase_name": raw_phase_name,
                    "weeks": [
                        {
                            **_build_gold_week(template, week_index=index),
                            "week_role": _infer_authored_week_role(
                                raw_phase_name,
                                week_index_in_phase=index,
                                total_phase_weeks=len(templates),
                            ),
                        }
                        for index, template in enumerate(templates, start=1)
                    ],
                }
            )

        if emitted_phases:
            return {
                "program_id": program_id,
                "program_name": program_name,
                "source_workbook": source_workbook,
                "version": version,
                "split": split,
                "phases": emitted_phases,
            }

    week_template = build_blueprint_week_template(session_rows)
    if not week_template["days"]:
        raise ValueError("No valid training days parsed from workbook")

    weeks = [_build_gold_week(week_template, week_index=week_index) for week_index in range(1, total_weeks + 1)]

    return {
        "program_id": program_id,
        "program_name": program_name,
        "source_workbook": source_workbook,
        "version": version,
        "split": split,
        "phases": [
            {
                "phase_id": phase_id,
                "phase_name": phase_name,
                "weeks": weeks,
            }
        ],
    }


def build_import_report(
    *,
    input_file: Path,
    selected_sheet_names: list[str],
    session_rows: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
    export_type: str,
    output_path: Path,
    total_weeks: int,
    phase_count: int,
    day_count: int,
) -> dict[str, Any]:
    return {
        "export_type": export_type,
        "source_workbook": str(input_file),
        "output_path": str(output_path),
        "sheet_count": len(selected_sheet_names),
        "sheet_names": selected_sheet_names,
        "session_count": len(session_rows),
        "phase_count": phase_count,
        "week_count": total_weeks,
        "day_count": day_count,
        "diagnostic_status": "warnings" if diagnostics else "clean",
        "diagnostic_count": len(diagnostics),
        "items": diagnostics,
    }
