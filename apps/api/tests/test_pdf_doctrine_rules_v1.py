import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.adaptive_schema import AdaptiveGoldRuleSet
from importers.pdf_doctrine_rules_v1 import build_rule_set_payload, distill_rule_set


def test_build_rule_set_payload_extracts_grounded_rule_hints(tmp_path: Path) -> None:
    guide_doc = tmp_path / "guide.md"
    guide_doc.write_text(
        """
        IMPORTANT PROGRAM NOTES
        For the first 2 weeks of this program, most sets are taken to an RPE of ~7-8 or ~8-9.
        This means you will be leaving 1-3 reps in the tank on most exercises.
        After the first two weeks, the intensity will increase and most sets will be taken to failure.
        Each exercise substitutions column should be used when equipment mismatch exists.
        All other aspects of the program, including how to progress through the rep ranges given, are explained in the handbook.
        Perform a full general warm-up and exercise-specific warm-up every workout.
        """,
        encoding="utf-8",
    )

    payload = build_rule_set_payload(
        program_id="pure_bodybuilding_phase_1_full_body",
        source_pdf="reference/The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf",
        guide_doc=guide_doc,
    )
    rules = AdaptiveGoldRuleSet.model_validate(payload)

    assert rules.starting_load_rules.default_rir_target == 2
    assert rules.starting_load_rules.method == "rep_range_rir_start"
    assert rules.substitution_rules.equipment_mismatch == "use_first_compatible_substitution"
    assert any(section.field == "substitution_rules.equipment_mismatch" for section in rules.source_sections)
    assert any(section.field == "starting_load_rules.default_rir_target" for section in rules.source_sections)


def test_distill_rule_set_writes_valid_rules_json(tmp_path: Path) -> None:
    guide_doc = tmp_path / "guide.md"
    output = tmp_path / "rules.json"
    guide_doc.write_text(
        """
        IMPORTANT PROGRAM NOTES
        For the first week of the program, most sets are taken to an RPE of ~6-7.
        This means you will be leaving 3-4 reps in the tank on most exercises.
        After the first week, the intensity will increase.
        Use the exercise substitutions column when equipment mismatch exists.
        Progress through the rep ranges given before increasing load.
        """,
        encoding="utf-8",
    )

    destination = distill_rule_set(
        source_pdf="reference/The_Bodybuilding_Transformation_System_-_Beginner.pdf",
        program_id="bodybuilding_transformation_beginner",
        output_file=output,
        guide_doc=guide_doc,
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))
    rules = AdaptiveGoldRuleSet.model_validate(payload)

    assert rules.rule_set_id == "bodybuilding_transformation_beginner_rules"
    assert rules.starting_load_rules.default_rir_target == 4
    assert rules.source_sections


def test_build_rule_set_payload_extracts_scheduled_deload_cadence_when_present(tmp_path: Path) -> None:
    guide_doc = tmp_path / "guide.md"
    guide_doc.write_text(
        """
        IMPORTANT PROGRAM NOTES
        For the first week of this program, most sets are taken to an RPE of ~7-8.
        Deload every 6 weeks to manage accumulated fatigue.
        Progress through the rep ranges given before increasing load.
        """,
        encoding="utf-8",
    )

    payload = build_rule_set_payload(
        program_id="pure_bodybuilding_phase_1_full_body",
        source_pdf="reference/The_Pure_Bodybuilding_Program - Phase 1 - Full_Body.pdf",
        guide_doc=guide_doc,
    )
    rules = AdaptiveGoldRuleSet.model_validate(payload)

    assert rules.deload_rules.scheduled_every_n_weeks == 6
