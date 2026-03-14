import os
from pathlib import Path

from app.config import settings
from app.program_loader import list_program_templates, load_program_template


def test_program_loader_fallback_to_repo_programs() -> None:
    """If the configured programs_dir does not exist, loader should fall back to repo programs/ dir."""
    previous = settings.programs_dir
    try:
        settings.programs_dir = "/path/that/does/not/exist"

        summaries = list_program_templates()
        assert isinstance(summaries, list)
        # one-program-first mode exposes canonical phase1 template as active catalog choice
        ids = {p["id"] for p in summaries}
        assert "pure_bodybuilding_phase_1_full_body" in ids
        assert "ppl_v1" not in ids
        assert "upper_lower_v1" not in ids

        # loading specific template should work too
        tpl = load_program_template("ppl_v1")
        assert tpl["id"] == "ppl_v1"
        assert len(tpl.get("sessions", [])) >= 1
    finally:
        settings.programs_dir = previous
