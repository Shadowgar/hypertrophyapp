import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.adaptive_schema import AdaptiveGoldProgramTemplate, AdaptiveGoldRuleSet


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_gold_program_template_validates_against_adaptive_schema() -> None:
    program_path = _repo_root() / "programs" / "gold" / "adaptive_full_body_gold_v0_1.json"
    payload = json.loads(program_path.read_text(encoding="utf-8"))

    template = AdaptiveGoldProgramTemplate.model_validate(payload)

    assert template.program_id == "adaptive_full_body_gold_v0_1"
    assert template.phases
    assert template.phases[0].weeks
    assert template.phases[0].weeks[0].days
    assert template.phases[0].weeks[0].days[0].slots


def test_gold_rule_set_validates_and_scopes_to_gold_program() -> None:
    rules_path = _repo_root() / "docs" / "rules" / "gold" / "adaptive_full_body_gold_v0_1.rules.json"
    payload = json.loads(rules_path.read_text(encoding="utf-8"))

    rules = AdaptiveGoldRuleSet.model_validate(payload)

    assert rules.rule_set_id == "adaptive_full_body_gold_v0_1_rules"
    assert "adaptive_full_body_gold_v0_1" in rules.program_scope
    assert rules.progression_rules.on_success.action == "increase_load"
    assert rules.rationale_templates.get("deload")


def test_gold_program_template_rejects_duplicate_week_index_and_slot_order() -> None:
    program_path = _repo_root() / "programs" / "gold" / "adaptive_full_body_gold_v0_1.json"
    payload = json.loads(program_path.read_text(encoding="utf-8"))

    duplicate_week = deepcopy(payload)
    duplicate_week["phases"][0]["weeks"].append(deepcopy(duplicate_week["phases"][0]["weeks"][0]))

    with pytest.raises(ValidationError, match="weeks must have unique week_index values per phase"):
        AdaptiveGoldProgramTemplate.model_validate(duplicate_week)

    duplicate_slot_order = deepcopy(payload)
    slots = duplicate_slot_order["phases"][0]["weeks"][0]["days"][0]["slots"]
    slots[1]["order_index"] = slots[0]["order_index"]

    with pytest.raises(ValidationError, match="slots must have unique order_index values per day"):
        AdaptiveGoldProgramTemplate.model_validate(duplicate_slot_order)


def test_gold_program_template_rejects_invalid_work_set_type() -> None:
    program_path = _repo_root() / "programs" / "gold" / "adaptive_full_body_gold_v0_1.json"
    payload = json.loads(program_path.read_text(encoding="utf-8"))
    payload["phases"][0]["weeks"][0]["days"][0]["slots"][0]["work_sets"][0]["set_type"] = "drop"

    with pytest.raises(ValidationError):
        AdaptiveGoldProgramTemplate.model_validate(payload)


def test_gold_rule_set_rejects_empty_or_duplicate_program_scope() -> None:
    rules_path = _repo_root() / "docs" / "rules" / "gold" / "adaptive_full_body_gold_v0_1.rules.json"
    payload = json.loads(rules_path.read_text(encoding="utf-8"))

    empty_scope = deepcopy(payload)
    empty_scope["program_scope"] = []
    with pytest.raises(ValidationError, match="program_scope must contain at least one program_id"):
        AdaptiveGoldRuleSet.model_validate(empty_scope)

    duplicate_scope = deepcopy(payload)
    duplicate_scope["program_scope"] = ["adaptive_full_body_gold_v0_1", "adaptive_full_body_gold_v0_1"]
    with pytest.raises(ValidationError, match="program_scope must not contain duplicate program_id values"):
        AdaptiveGoldRuleSet.model_validate(duplicate_scope)
