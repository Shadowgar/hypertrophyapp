"""
Schema validation tests for program templates, onboarding packages, and coaching rules.

Validates gold artifacts against the canonical Pydantic models defined in
adaptive_schema.py and template_schema.py. These tests ensure that all program
data files consumed by the runtime conform to the expected contracts.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[3]
PROGRAMS_GOLD = REPO_ROOT / "programs" / "gold"
RULES_CANONICAL = REPO_ROOT / "docs" / "rules" / "canonical"
RULES_GOLD = REPO_ROOT / "docs" / "rules" / "gold"

from app.adaptive_schema import (
    AdaptiveGoldProgramTemplate,
    AdaptiveGoldRuleSet,
    ProgramOnboardingPackage,
)


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Gold program templates (adaptive gold format)
# ---------------------------------------------------------------------------

class TestAdaptiveGoldTemplateValidation:
    def test_adaptive_gold_template_conforms_to_schema(self) -> None:
        path = PROGRAMS_GOLD / "adaptive_full_body_gold_v0_1.json"
        data = _load_json(path)
        template = AdaptiveGoldProgramTemplate.model_validate(data)
        assert template.program_id
        assert len(template.phases) > 0

    def test_adaptive_gold_template_has_valid_phases_weeks_days(self) -> None:
        path = PROGRAMS_GOLD / "adaptive_full_body_gold_v0_1.json"
        data = _load_json(path)
        template = AdaptiveGoldProgramTemplate.model_validate(data)
        for phase in template.phases:
            assert phase.phase_id
            assert len(phase.weeks) > 0
            for week in phase.weeks:
                assert week.week_index >= 1
                assert len(week.days) > 0
                for day in week.days:
                    assert day.day_id
                    assert day.day_name


# ---------------------------------------------------------------------------
# Canonical program templates (template_schema format)
# ---------------------------------------------------------------------------

class TestPhase1ProgramTemplateValidation:
    def test_phase1_template_conforms_to_adaptive_gold_schema(self) -> None:
        path = PROGRAMS_GOLD / "pure_bodybuilding_phase_1_full_body.json"
        data = _load_json(path)
        template = AdaptiveGoldProgramTemplate.model_validate(data)
        assert template.program_id == "pure_bodybuilding_phase_1_full_body"
        assert template.split == "full_body"
        assert len(template.phases) > 0

    def test_phase1_template_has_valid_phases_weeks_days_slots(self) -> None:
        path = PROGRAMS_GOLD / "pure_bodybuilding_phase_1_full_body.json"
        data = _load_json(path)
        template = AdaptiveGoldProgramTemplate.model_validate(data)
        for phase in template.phases:
            assert phase.phase_id
            assert len(phase.weeks) > 0
            for week in phase.weeks:
                assert week.week_index >= 1
                assert len(week.days) > 0
                for day in week.days:
                    assert day.day_id
                    assert day.day_name
                    for slot in day.slots:
                        assert slot.slot_id
                        assert slot.exercise_id
                        assert slot.order_index >= 1

    def test_phase1_template_has_10_week_sequence(self) -> None:
        path = PROGRAMS_GOLD / "pure_bodybuilding_phase_1_full_body.json"
        data = _load_json(path)
        template = AdaptiveGoldProgramTemplate.model_validate(data)
        total_weeks = sum(len(phase.weeks) for phase in template.phases)
        assert total_weeks == 10


# ---------------------------------------------------------------------------
# Onboarding packages
# ---------------------------------------------------------------------------

class TestOnboardingPackageValidation:
    def test_phase1_onboarding_package_conforms_to_schema(self) -> None:
        path = PROGRAMS_GOLD / "pure_bodybuilding_phase_1_full_body.onboarding.json"
        data = _load_json(path)
        package = ProgramOnboardingPackage.model_validate(data)
        assert package.program_id == "pure_bodybuilding_phase_1_full_body"
        assert package.blueprint.program_id == package.program_id
        assert package.program_intent.program_id == package.program_id

    def test_phase1_onboarding_blueprint_structure(self) -> None:
        path = PROGRAMS_GOLD / "pure_bodybuilding_phase_1_full_body.onboarding.json"
        data = _load_json(path)
        package = ProgramOnboardingPackage.model_validate(data)
        bp = package.blueprint
        assert bp.split in ("full_body", "upper_lower", "ppl")
        assert bp.default_training_days >= 2
        assert bp.total_weeks >= 1
        assert len(bp.week_sequence) == bp.total_weeks
        assert len(bp.week_templates) > 0

        template_ids = {t.week_template_id for t in bp.week_templates}
        for seq_id in bp.week_sequence:
            assert seq_id in template_ids, f"week_sequence references unknown template: {seq_id}"

    def test_phase1_onboarding_exercise_library_populated(self) -> None:
        path = PROGRAMS_GOLD / "pure_bodybuilding_phase_1_full_body.onboarding.json"
        data = _load_json(path)
        package = ProgramOnboardingPackage.model_validate(data)
        assert len(package.exercise_library) > 0 or len(package.exercise_catalog) > 0

    def test_phase1_onboarding_frequency_adaptation_rules(self) -> None:
        path = PROGRAMS_GOLD / "pure_bodybuilding_phase_1_full_body.onboarding.json"
        data = _load_json(path)
        package = ProgramOnboardingPackage.model_validate(data)
        rules = package.frequency_adaptation_rules
        assert rules.default_training_days >= 2
        assert rules.minimum_temporary_days >= 2
        assert rules.max_temporary_weeks >= 1
        assert len(rules.preserve_slot_roles) > 0
        assert rules.daily_slot_cap_when_compressed >= 3

    def test_phase1_onboarding_slot_uniqueness(self) -> None:
        """Verify slot_id and order_index uniqueness per day across all week templates."""
        path = PROGRAMS_GOLD / "pure_bodybuilding_phase_1_full_body.onboarding.json"
        data = _load_json(path)
        package = ProgramOnboardingPackage.model_validate(data)
        for template in package.blueprint.week_templates:
            for day in template.days:
                slot_ids = [s.slot_id for s in day.slots]
                assert len(slot_ids) == len(set(slot_ids)), f"Duplicate slot_ids in {day.day_id}"
                order_indices = [s.order_index for s in day.slots]
                assert len(order_indices) == len(set(order_indices)), f"Duplicate order_index in {day.day_id}"


# ---------------------------------------------------------------------------
# Coaching rules
# ---------------------------------------------------------------------------

class TestCoachingRuleSetValidation:
    def test_gold_rule_set_conforms_to_schema(self) -> None:
        path = RULES_GOLD / "adaptive_full_body_gold_v0_1.rules.json"
        data = _load_json(path)
        rule_set = AdaptiveGoldRuleSet.model_validate(data)
        assert rule_set.rule_set_id
        assert len(rule_set.program_scope) > 0
        assert rule_set.starting_load_rules.method
        assert rule_set.progression_rules.success_condition
        assert rule_set.deload_rules.scheduled_every_n_weeks >= 1

    def test_canonical_phase1_rule_set_conforms_to_schema(self) -> None:
        path = RULES_CANONICAL / "pure_bodybuilding_phase_1_full_body.rules.json"
        data = _load_json(path)
        rule_set = AdaptiveGoldRuleSet.model_validate(data)
        assert rule_set.rule_set_id
        assert "pure_bodybuilding_phase_1_full_body" in rule_set.program_scope

    def test_gold_rule_set_has_scheduler_rules(self) -> None:
        path = RULES_GOLD / "adaptive_full_body_gold_v0_1.rules.json"
        data = _load_json(path)
        rule_set = AdaptiveGoldRuleSet.model_validate(data)
        assert rule_set.generated_week_scheduler_rules is not None
        sched = rule_set.generated_week_scheduler_rules
        assert sched.mesocycle is not None
        assert sched.exercise_adjustment is not None
        assert sched.session_selection is not None
        assert sched.muscle_coverage is not None


@pytest.mark.parametrize("filename", [
    f.name
    for f in RULES_CANONICAL.glob("*.rules.json")
])
def test_canonical_rule_files_have_valid_structure(filename: str) -> None:
    """All canonical rule files must have at minimum: rule_set_id, program_scope, and core rule blocks."""
    path = RULES_CANONICAL / filename
    data = _load_json(path)
    assert "rule_set_id" in data, f"{filename}: missing rule_set_id"
    assert "program_scope" in data, f"{filename}: missing program_scope"
    assert isinstance(data.get("program_scope"), list), f"{filename}: program_scope must be a list"
    assert len(data["program_scope"]) > 0, f"{filename}: program_scope must not be empty"
    assert "starting_load_rules" in data, f"{filename}: missing starting_load_rules"
    assert "progression_rules" in data, f"{filename}: missing progression_rules"
    assert "deload_rules" in data, f"{filename}: missing deload_rules"


# ---------------------------------------------------------------------------
# Negative tests: invalid fixtures should fail validation
# ---------------------------------------------------------------------------

class TestSchemaRejection:
    def test_empty_program_template_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AdaptiveGoldProgramTemplate.model_validate({})

    def test_onboarding_package_mismatched_program_id_rejected(self) -> None:
        path = PROGRAMS_GOLD / "pure_bodybuilding_phase_1_full_body.onboarding.json"
        data = _load_json(path)
        data["program_id"] = "wrong_id"
        with pytest.raises(ValidationError, match="program_id must match"):
            ProgramOnboardingPackage.model_validate(data)

    def test_rule_set_empty_program_scope_rejected(self) -> None:
        path = RULES_GOLD / "adaptive_full_body_gold_v0_1.rules.json"
        data = _load_json(path)
        data["program_scope"] = []
        with pytest.raises(ValidationError, match="program_scope"):
            AdaptiveGoldRuleSet.model_validate(data)

    def test_template_no_phases_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AdaptiveGoldProgramTemplate.model_validate({
                "program_id": "test",
                "program_name": "Test",
                "source_workbook": "test.xlsx",
                "version": "1.0",
                "split": "full_body",
                "phases": [],
            })
