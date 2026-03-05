import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from test_db import configure_test_database

configure_test_database("test_program_loader")

from app.config import settings
from app.program_loader import load_program_template


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
