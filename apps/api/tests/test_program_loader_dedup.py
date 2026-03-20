import json
from pathlib import Path

from test_db import configure_test_database

configure_test_database("test_program_loader_dedup")

from app import program_loader


def _write_template(path: Path, *, template_id: str, split: str, first_exercise: str) -> None:
    payload = {
        "id": template_id,
        "version": "1.0.0",
        "split": split,
        "days_supported": [2, 3, 4],
        "deload": {
            "trigger_weeks": 6,
            "set_reduction_pct": 35,
            "load_reduction_pct": 10,
        },
        "progression": {
            "mode": "double_progression",
            "increment_kg": 2.5,
        },
        "sessions": [
            {
                "name": "Day 1",
                "exercises": [
                    {
                        "id": first_exercise,
                        "primary_exercise_id": first_exercise,
                        "name": first_exercise,
                        "sets": 3,
                        "rep_range": [8, 12],
                        "start_weight": 20,
                        "priority": "standard",
                        "movement_pattern": "horizontal_press",
                        "primary_muscles": ["chest"],
                        "equipment_tags": ["dumbbell"],
                        "substitution_candidates": [],
                        "notes": None,
                        "video": None,
                    }
                ],
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_list_program_templates_deduplicates_identical_payloads(monkeypatch, tmp_path: Path) -> None:
    _write_template(
        tmp_path / "pure_bodybuilding_phase_2_full_body_sheet.json",
        template_id="pure_bodybuilding_phase_2_full_body_sheet",
        split="full_body",
        first_exercise="bench",
    )
    _write_template(
        tmp_path / "pure_bodybuilding_phase_2_full_body_sheet_1.json",
        template_id="pure_bodybuilding_phase_2_full_body_sheet_1",
        split="full_body",
        first_exercise="bench",
    )
    _write_template(
        tmp_path / "upper_lower_v1.json",
        template_id="upper_lower_v1",
        split="upper_lower",
        first_exercise="row",
    )
    _write_template(
        tmp_path / "legacy_imported_template_imported.json",
        template_id="legacy_imported_template",
        split="full_body",
        first_exercise="legacy",
    )

    monkeypatch.setattr(program_loader, "_resolve_programs_path", lambda: tmp_path)

    templates = program_loader.list_program_templates(active_only=False)
    ids = {item["id"] for item in templates}

    assert "upper_lower_v1" in ids
    assert "pure_bodybuilding_phase_2_full_body" in ids
    assert "pure_bodybuilding_phase_2_full_body_sheet_1" not in ids
    assert "legacy_imported_template" not in ids
    assert len(ids) == 2
