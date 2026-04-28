import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.knowledge_loader import load_exercise_library, load_exercise_metadata_v2
from importers.exercise_intelligence_extraction import compute_reachable_generated_full_body_candidate_set


VISIBLE_GROUPS = {
    "arms",
    "back",
    "calves",
    "chest",
    "core",
    "delts",
    "glutes",
    "hamstrings",
    "lower_back",
    "quads",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_reachable_generated_full_body_exercises_have_metadata_v2_coverage() -> None:
    reachable = set(compute_reachable_generated_full_body_candidate_set(compiled_dir=REPO_ROOT / "knowledge" / "compiled"))
    bundle = load_exercise_metadata_v2(REPO_ROOT / "knowledge" / "compiled")
    assert bundle is not None

    metadata_ids = {record.exercise_id for record in bundle.records}
    missing = sorted(reachable - metadata_ids)
    assert not missing, f"missing metadata_v2 for reachable generated full-body exercises: {missing}"


def test_metadata_v2_curated_and_compiled_artifacts_are_in_sync() -> None:
    curated = _json(REPO_ROOT / "knowledge" / "curation" / "exercise_metadata.v2.json")
    compiled = _json(REPO_ROOT / "knowledge" / "compiled" / "exercise_library.metadata.v2.json")

    curated_ids = sorted(record["exercise_id"] for record in curated["records"])
    compiled_ids = sorted(record["exercise_id"] for record in compiled["records"])

    assert curated_ids == compiled_ids


def test_metadata_v2_records_have_required_sections_and_non_empty_substitution_families() -> None:
    bundle = load_exercise_metadata_v2(REPO_ROOT / "knowledge" / "compiled")
    assert bundle is not None

    required_sections = {
        "muscle_targeting",
        "movement",
        "role",
        "fatigue",
        "overlap",
        "substitution",
        "skill_stability_safety",
        "hypertrophy_methods",
        "time_efficiency",
        "restrictions",
        "provenance",
    }

    for record in bundle.records:
        payload = record.metadata_v2.model_dump(mode="json")
        assert required_sections <= set(payload)
        substitution = payload["substitution"]
        assert substitution["substitution_family"].strip()
        assert substitution["equipment_substitution_family"].strip()


def test_visible_grouped_muscle_mapping_is_normalized_and_deterministic() -> None:
    bundle = load_exercise_metadata_v2(REPO_ROOT / "knowledge" / "compiled")
    assert bundle is not None

    for record in bundle.records:
        groups = record.metadata_v2.muscle_targeting.visible_grouped_muscle_mapping
        assert groups == sorted(set(groups))
        assert set(groups) <= VISIBLE_GROUPS


def test_overlap_tags_present_for_risk_patterns() -> None:
    bundle = load_exercise_metadata_v2(REPO_ROOT / "knowledge" / "compiled")
    assert bundle is not None

    risk_patterns = {
        "horizontal_push",
        "vertical_push",
        "horizontal_pull",
        "vertical_pull",
        "squat",
        "hinge",
        "elbow_flexion",
        "elbow_extension",
    }

    for record in bundle.records:
        pattern = record.metadata_v2.movement.primary_pattern
        if pattern not in risk_patterns:
            continue
        overlap = record.metadata_v2.overlap
        assert any(
            [
                overlap.pressing_overlap,
                overlap.front_delt_overlap,
                overlap.triceps_overlap,
                overlap.biceps_overlap,
                overlap.grip_overlap,
                overlap.trap_overlap,
                overlap.lower_back_overlap,
                overlap.knee_stress,
                overlap.hip_hinge_overlap,
            ]
        ), f"expected at least one overlap signal for risk pattern on {record.exercise_id}"


def test_advanced_method_compatibility_is_conservative_for_seeded_records() -> None:
    bundle = load_exercise_metadata_v2(REPO_ROOT / "knowledge" / "compiled")
    assert bundle is not None

    for record in bundle.records:
        if record.metadata_v2.provenance.review_status != "seeded":
            continue
        methods = record.metadata_v2.hypertrophy_methods
        assert methods.lengthened_partial_compatible is False
        assert methods.myo_rep_compatible is False
        assert methods.drop_set_compatible is False
        assert methods.rest_pause_compatible is False
        assert methods.cluster_set_compatible is False
        assert methods.static_stretch_compatible is False
        assert methods.feeder_set_compatible is False


def test_restriction_flags_are_normalized_tokens_only() -> None:
    bundle = load_exercise_metadata_v2(REPO_ROOT / "knowledge" / "compiled")
    assert bundle is not None

    for record in bundle.records:
        flags = record.metadata_v2.restrictions.flags
        assert flags == sorted(set(flags))
        for flag in flags:
            assert flag.startswith("avoid_")
            assert " " not in flag


def test_metadata_v2_coverage_is_subset_of_canonical_exercise_library() -> None:
    bundle = load_exercise_metadata_v2(REPO_ROOT / "knowledge" / "compiled")
    exercise_library = load_exercise_library(REPO_ROOT / "knowledge" / "compiled")
    assert bundle is not None

    canonical_ids = {record.exercise_id for record in exercise_library.records}
    metadata_ids = {record.exercise_id for record in bundle.records}

    assert metadata_ids <= canonical_ids
