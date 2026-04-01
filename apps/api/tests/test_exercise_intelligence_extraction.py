from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.knowledge_loader import load_exercise_library, load_source_registry
from importers.doctrine_extraction import ClaimCandidate
from importers.exercise_intelligence_extraction import (
    ALLOWED_SOURCE_FAMILIES,
    build_exercise_intelligence_extraction_result,
    compute_reachable_generated_full_body_candidate_set,
    extract_exercise_intelligence_claims,
    resolve_exercise_intelligence_claims,
)


FIXTURE_EXAMPLES = {
    "compound_fallback": "belt_squat",
    "supported_accessory": "bottom_half_ez_bar_preacher_curl",
    "unsupported_unilateral_accessory": "bent_over_cable_pec_flye",
}


def test_compute_reachable_generated_full_body_candidate_set_is_deterministic() -> None:
    first = compute_reachable_generated_full_body_candidate_set()
    second = compute_reachable_generated_full_body_candidate_set()

    assert first == second
    assert "hack_squat" in first
    assert "barbell_rdl" in first
    assert all(not exercise_id.startswith("weak_point_exercise") for exercise_id in first)


def test_extract_exercise_intelligence_claims_emit_allowed_values_and_source_families() -> None:
    source_registry = load_source_registry()
    current_library_dir = REPO_ROOT / "knowledge" / "compiled"
    reachable = compute_reachable_generated_full_body_candidate_set(compiled_dir=current_library_dir)
    current_library = load_exercise_library(current_library_dir)

    claims = extract_exercise_intelligence_claims(
        onboarding_dir=REPO_ROOT / "programs" / "gold",
        source_registry_bundle=source_registry,
        current_compiled_exercise_library=current_library,
        reachable_exercise_ids=reachable,
    )

    allowed_scalar_values = {"low", "moderate", "high"}
    assert claims
    assert {claim.source_family_id for claim in claims} <= ALLOWED_SOURCE_FAMILIES
    assert all(claim.claim_key.startswith("exercise:") for claim in claims)
    assert all(claim.target_id in reachable for claim in claims)
    assert all(claim.normalized_value in allowed_scalar_values for claim in claims)
    assert all(claim.scope["source_program_id"] in {"pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"} for claim in claims)
    assert all(claim.scope["evidence_type"] in {"structured", "regex"} for claim in claims)
    claim_lookup = {
        (claim.target_id, claim.payload_path): claim
        for claim in claims
    }
    assert claim_lookup[("belt_squat", "skill_demand")].normalized_value in {"moderate", "high"}
    assert claim_lookup[("belt_squat", "skill_demand")].scope["local_rule_id"] in {
        "skill_moderate_compound_role_fallback",
        "skill_high_freeweight_compound_local",
        "skill_high_unilateral_or_unsupported_compound_local",
    }
    assert claim_lookup[("bent_over_cable_pec_flye", "stability_demand")].normalized_value == "moderate"
    assert claim_lookup[("bent_over_cable_pec_flye", "stability_demand")].scope["local_rule_id"] == "stability_moderate_unilateral_or_unsupported_accessory_regex"
    assert claim_lookup[("bottom_half_ez_bar_preacher_curl", "skill_demand")].normalized_value == "low"
    assert claim_lookup[("bottom_half_ez_bar_preacher_curl", "skill_demand")].scope["local_rule_id"] in {
        "skill_low_supported_accessory_regex",
        "skill_low_supported_accessory_or_isolation_local",
    }


def test_local_skill_stability_rule_families_cover_named_fixture_examples() -> None:
    result = build_exercise_intelligence_extraction_result(
        onboarding_dir=REPO_ROOT / "programs" / "gold",
        source_registry_bundle=load_source_registry(),
        current_compiled_dir=REPO_ROOT / "knowledge" / "compiled",
        resolutions_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.resolutions.json",
        unresolved_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.unresolved.json",
    )
    metadata = result.metadata_by_exercise_id

    compound_id = FIXTURE_EXAMPLES["compound_fallback"]
    supported_id = FIXTURE_EXAMPLES["supported_accessory"]
    unsupported_id = FIXTURE_EXAMPLES["unsupported_unilateral_accessory"]

    assert metadata[compound_id]["skill_demand"] in {"moderate", "high"}
    assert metadata[compound_id]["stability_demand"] in {"moderate", "high"}

    assert metadata[supported_id]["skill_demand"] == "low"
    assert metadata[supported_id]["stability_demand"] == "low"

    assert metadata[unsupported_id]["skill_demand"] in {"moderate", "high"}
    assert metadata[unsupported_id]["stability_demand"] in {"moderate", "high"}


def test_unsupported_accessory_stability_is_higher_than_supported_accessory() -> None:
    result = build_exercise_intelligence_extraction_result(
        onboarding_dir=REPO_ROOT / "programs" / "gold",
        source_registry_bundle=load_source_registry(),
        current_compiled_dir=REPO_ROOT / "knowledge" / "compiled",
        resolutions_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.resolutions.json",
        unresolved_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.unresolved.json",
    )
    metadata = result.metadata_by_exercise_id
    order = {"low": 1, "moderate": 2, "high": 3}
    supported_level = str(metadata[FIXTURE_EXAMPLES["supported_accessory"]]["stability_demand"])
    unsupported_level = str(metadata[FIXTURE_EXAMPLES["unsupported_unilateral_accessory"]]["stability_demand"])
    assert order[unsupported_level] > order[supported_level]


def test_extraction_result_is_deterministic_and_keeps_source_scope_local() -> None:
    first = build_exercise_intelligence_extraction_result(
        onboarding_dir=REPO_ROOT / "programs" / "gold",
        source_registry_bundle=load_source_registry(),
        current_compiled_dir=REPO_ROOT / "knowledge" / "compiled",
        resolutions_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.resolutions.json",
        unresolved_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.unresolved.json",
    )
    second = build_exercise_intelligence_extraction_result(
        onboarding_dir=REPO_ROOT / "programs" / "gold",
        source_registry_bundle=load_source_registry(),
        current_compiled_dir=REPO_ROOT / "knowledge" / "compiled",
        resolutions_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.resolutions.json",
        unresolved_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.unresolved.json",
    )

    assert first.reachable_exercise_ids == second.reachable_exercise_ids
    assert first.metadata_by_exercise_id == second.metadata_by_exercise_id
    assert first.input_signature_parts == second.input_signature_parts
    assert all(
        claim.scope["source_program_id"] in {"pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"}
        for claim in first.extracted_claims
    )


def test_strong_fields_remain_unchanged_for_reference_exercises() -> None:
    result = build_exercise_intelligence_extraction_result(
        onboarding_dir=REPO_ROOT / "programs" / "gold",
        source_registry_bundle=load_source_registry(),
        current_compiled_dir=REPO_ROOT / "knowledge" / "compiled",
        resolutions_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.resolutions.json",
        unresolved_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.unresolved.json",
    )
    metadata = result.metadata_by_exercise_id

    assert metadata["barbell_rdl"]["fatigue_cost"] == "high"
    assert metadata["barbell_rdl"]["progression_compatibility"] == "moderate"


def test_resolve_exercise_intelligence_claims_emits_unresolved_below_threshold(tmp_path: Path) -> None:
    unresolved_path = tmp_path / "exercise_library_extraction.unresolved.json"
    claim = ClaimCandidate(
        claim_key="exercise:test_lift:progression_compatibility",
        target_type="exercise_field",
        target_id="test_lift",
        payload_path="progression_compatibility",
        normalized_value="moderate",
        scope={
            "split_scope": "full_body",
            "source_program_id": "pure_bodybuilding_phase_1_full_body",
            "source_path": "reference/Pure Bodybuilding Phase 1 - Full Body Sheet.xlsx",
            "evidence_type": "regex",
            "local_rule_id": "progression_high_regex",
        },
        normalization_method="direct_enum_mapping",
        normalization_confidence=1.0,
        evidence_fragment_id="fragment:test",
        source_id="pure-bodybuilding-phase-1-full-body-sheet-46f50999",
        source_family_id="pure_bodybuilding_phase_1",
        authority_weight=1.0,
        classification_confidence=0.8,
        excerpt_quality=0.9,
    )

    resolved, unresolved = resolve_exercise_intelligence_claims(
        claims=(claim,),
        resolutions_path=None,
        unresolved_path=unresolved_path,
    )

    assert resolved == ()
    assert len(unresolved) == 1
    assert unresolved[0].reason == "below_threshold"
    assert unresolved_path.exists()


def test_build_exercise_intelligence_extraction_result_end_to_end() -> None:
    result = build_exercise_intelligence_extraction_result(
        onboarding_dir=REPO_ROOT / "programs" / "gold",
        source_registry_bundle=load_source_registry(),
        current_compiled_dir=REPO_ROOT / "knowledge" / "compiled",
        resolutions_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.resolutions.json",
        unresolved_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.unresolved.json",
    )

    assert result.reachable_exercise_ids
    assert result.extracted_claims
    assert result.resolved_claims
    assert isinstance(result.unresolved_conflicts, tuple)
    assert all(claim.target_id in result.reachable_exercise_ids for claim in result.extracted_claims)
    assert all(not claim.claim_key.startswith("rule:") for claim in result.extracted_claims)
    assert set(result.metadata_by_exercise_id).issubset(set(result.reachable_exercise_ids))
    assert result.metadata_by_exercise_id["belt_squat"]["skill_demand"] == "moderate"
    assert result.metadata_by_exercise_id["wide_grip_lat_pulldown"]["stability_demand"] == "moderate"
    assert result.metadata_by_exercise_id["bent_over_cable_pec_flye"]["skill_demand"] == "moderate"
    assert result.metadata_by_exercise_id["bottom_half_ez_bar_preacher_curl"]["stability_demand"] == "low"
    if "neutral_grip_pullup" in result.metadata_by_exercise_id:
        assert result.metadata_by_exercise_id["neutral_grip_pullup"]["skill_demand"] in {"moderate", "high"}
