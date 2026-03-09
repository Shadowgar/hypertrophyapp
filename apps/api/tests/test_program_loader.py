import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from test_db import configure_test_database

configure_test_database("test_program_loader")

from app.config import settings
from app.program_loader import load_program_rule_set, load_program_template


def test_load_program_template_validates_existing_template() -> None:
    template = load_program_template("ppl_v1")
    assert template["id"] == "ppl_v1"
    assert len(template["sessions"]) >= 1


def test_load_program_template_raises_on_invalid_schema(tmp_path: Path) -> None:
    broken = {
        "id": "broken_template",
        "version": "1.0.0",
        "split": "ppl",
        "days_supported": [3],
        "deload": {"trigger_weeks": 6, "set_reduction_pct": 35, "load_reduction_pct": 10},
        "progression": {"mode": "double_progression", "increment_kg": 2.5},
    }

    template_path = tmp_path / "broken_template.json"
    template_path.write_text(json.dumps(broken), encoding="utf-8")

    previous_programs_dir = settings.programs_dir
    settings.programs_dir = str(tmp_path)
    try:
        with pytest.raises(ValidationError):
            load_program_template("broken_template")
    finally:
        settings.programs_dir = previous_programs_dir


def test_load_program_rule_set_validates_existing_rules() -> None:
    rule_set = load_program_rule_set("pure_bodybuilding_phase_1_full_body")

    assert rule_set["rule_set_id"] == "pure_bodybuilding_phase_1_full_body_rules"
    assert "pure_bodybuilding_phase_1_full_body" in rule_set["program_scope"]
    assert rule_set["progression_rules"]["on_success"]["percent"] == pytest.approx(2.5)


@pytest.mark.parametrize(
    ("program_id", "expected_program_scope"),
    [
        ("ppl_v1", "pure_bodybuilding_phase_2_ppl_sheet"),
        ("upper_lower_v1", "pure_bodybuilding_phase_2_upper_lower_sheet"),
        ("pure_bodybuilding_full_body", "pure_bodybuilding_phase_1_full_body"),
        ("pure_bodybuilding_phase_2_full_body_sheet_1", "pure_bodybuilding_phase_2_full_body_sheet"),
        ("powerbuilding_3_0", "powerbuilding_3_0"),
        ("the_bodybuilding_transformation_system_beginner", "the_bodybuilding_transformation_system_beginner"),
        ("the_bodybuilding_transformation_system_intermediate_advanced", "the_bodybuilding_transformation_system_intermediate_advanced"),
        ("the_ultimate_push_pull_legs_system_4x", "the_ultimate_push_pull_legs_system_4x"),
        ("the_ultimate_push_pull_legs_system_5x", "the_ultimate_push_pull_legs_system_5x"),
        ("the_ultimate_push_pull_legs_system_6x", "the_ultimate_push_pull_legs_system_6x"),
    ],
)
def test_load_program_rule_set_resolves_runtime_program_aliases(
    program_id: str,
    expected_program_scope: str,
) -> None:
    rule_set = load_program_rule_set(program_id)

    assert expected_program_scope in rule_set["program_scope"]
    assert rule_set["progression_rules"]["on_under_target"]["after_exposures"] == 2
    assert isinstance(rule_set["source_sections"], list)


@pytest.mark.parametrize(
    "program_id",
    [
        "powerbuilding_3_0",
        "the_bodybuilding_transformation_system_beginner",
        "the_ultimate_push_pull_legs_system_4x",
    ],
)
def test_load_program_rule_set_loads_newly_distilled_catalog_rules(program_id: str) -> None:
    rule_set = load_program_rule_set(program_id)

    assert rule_set["source_pdf"]
    assert rule_set["rule_set_id"].endswith("_rules")
