from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.knowledge_loader import load_exercise_library, load_source_registry
from importers.doctrine_extraction import (
    ClaimCandidate,
    cluster_claims,
    normalize_day_role,
    normalize_movement_pattern,
    normalize_slot_role,
    select_cluster_winner,
)
from importers.full_body_structural_doctrine import (
    build_day_structure_extractor,
    build_full_body_required_movement_patterns_rule,
    extract_required_movement_pattern_fragments,
)


def test_extractors_read_structured_gold_program_documents() -> None:
    compiled_dir = REPO_ROOT / "knowledge" / "compiled"
    source_registry = load_source_registry(compiled_dir)
    table_fragments, structure_fragments = extract_required_movement_pattern_fragments(
        program_dir=REPO_ROOT / "programs" / "gold",
        source_registry_bundle=source_registry,
    )

    assert table_fragments
    assert all(fragment.extractor_id == "table_workbook" for fragment in table_fragments)
    assert any(fragment.raw_extracted_value["exercise_id"] == "leg_press" for fragment in table_fragments)

    structure_extractor = build_day_structure_extractor()
    assert structure_fragments
    assert all(fragment.extractor_id == structure_extractor.extractor_id for fragment in structure_fragments)
    assert any(fragment.raw_extracted_value["day_role"] == "full_body_1" for fragment in structure_fragments)
    assert any(int(fragment.raw_extracted_value["slot_count"]) > 0 for fragment in structure_fragments)


def test_normalization_supports_movement_pattern_day_role_and_slot_role() -> None:
    compiled_dir = REPO_ROOT / "knowledge" / "compiled"
    exercise_library = load_exercise_library(compiled_dir)

    movement_pattern, movement_confidence, movement_method = normalize_movement_pattern(
        exercise_id="leg_press",
        exercise_library_bundle=exercise_library,
    )
    assert movement_pattern == "squat"
    assert movement_confidence == 1.0
    assert movement_method == "exercise_library_lookup"

    day_role, day_confidence, day_method = normalize_day_role("Full Body #1")
    assert day_role == "full_body_1"
    assert day_confidence == 0.9
    assert day_method == "lookup_table"

    slot_role, slot_confidence, slot_method = normalize_slot_role("primary_compound")
    assert slot_role == "primary_compound"
    assert slot_confidence == 1.0
    assert slot_method == "identity"


def test_conflict_resolution_uses_weighted_scoring_margin_and_manual_resolution_hash(tmp_path: Path) -> None:
    claim_low = ClaimCandidate(
        claim_key="rule:test:requirements:squat",
        target_type="doctrine_rule_field",
        target_id="test",
        payload_path="requirements[squat]",
        normalized_value={"movement_pattern": "squat", "minimum_weekly_exposures": 1, "priority_rank": 1},
        scope={"split_scope": "full_body"},
        normalization_method="identity",
        normalization_confidence=1.0,
        evidence_fragment_id="a1",
        source_id="source-a",
        source_family_id="family-a",
        authority_weight=1.0,
        classification_confidence=1.0,
        excerpt_quality=1.0,
    )
    claim_support = ClaimCandidate(
        claim_key="rule:test:requirements:squat",
        target_type="doctrine_rule_field",
        target_id="test",
        payload_path="requirements[squat]",
        normalized_value={"movement_pattern": "squat", "minimum_weekly_exposures": 1, "priority_rank": 1},
        scope={"split_scope": "full_body"},
        normalization_method="identity",
        normalization_confidence=1.0,
        evidence_fragment_id="a2",
        source_id="source-b",
        source_family_id="family-b",
        authority_weight=1.0,
        classification_confidence=1.0,
        excerpt_quality=1.0,
    )
    claim_conflict = ClaimCandidate(
        claim_key="rule:test:requirements:squat",
        target_type="doctrine_rule_field",
        target_id="test",
        payload_path="requirements[squat]",
        normalized_value={"movement_pattern": "squat", "minimum_weekly_exposures": 2, "priority_rank": 1},
        scope={"split_scope": "full_body"},
        normalization_method="identity",
        normalization_confidence=1.0,
        evidence_fragment_id="b1",
        source_id="source-c",
        source_family_id="family-c",
        authority_weight=1.0,
        classification_confidence=1.0,
        excerpt_quality=0.75,
    )

    cluster = cluster_claims([claim_low, claim_support, claim_conflict])["rule:test:requirements:squat"]
    winner = select_cluster_winner(cluster=cluster, threshold=0.85, resolutions={})
    assert winner.claim_key == "rule:test:requirements:squat"
    assert winner.chosen_value["minimum_weekly_exposures"] == 1
    assert winner.confidence >= 0.95


def test_end_to_end_rule_synthesis_builds_required_movement_patterns_rule(tmp_path: Path) -> None:
    compiled_dir = REPO_ROOT / "knowledge" / "compiled"
    source_registry = load_source_registry(compiled_dir)
    exercise_library = load_exercise_library(compiled_dir)
    unresolved_path = tmp_path / "multi_source_hypertrophy_v1.unresolved.json"
    resolutions_path = tmp_path / "multi_source_hypertrophy_v1.resolutions.json"

    result = build_full_body_required_movement_patterns_rule(
        program_dir=REPO_ROOT / "programs" / "gold",
        source_registry_bundle=source_registry,
        exercise_library_bundle=exercise_library,
        resolutions_path=resolutions_path,
        unresolved_path=unresolved_path,
    )

    assert result.extracted_claims
    assert not result.unresolved_conflicts
    assert result.resolved_rule_payload is not None
    assert result.resolved_rule_payload["rule_id"] == "full_body_required_movement_patterns_v1"
    assert result.resolved_rule_payload["status"] == "curated"
    assert [item["movement_pattern"] for item in result.resolved_rule_payload["payload"]["requirements"]] == [
        "squat",
        "hinge",
        "horizontal_press",
        "horizontal_pull",
        "vertical_pull",
        "vertical_press",
    ]
    assert unresolved_path.exists()
