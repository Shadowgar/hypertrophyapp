import json
from pathlib import Path

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
