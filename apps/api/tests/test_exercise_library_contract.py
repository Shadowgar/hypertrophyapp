from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.knowledge_schema import ExerciseLibraryOverrideBundle
from app.knowledge_loader import load_source_registry
from importers.exercise_library_foundation import build_exercise_library_foundation


def test_exercise_library_foundation_builds_from_onboarding_packages_skips_placeholders_and_applies_bounded_overrides() -> None:
    onboarding_dir = REPO_ROOT / "programs" / "gold"
    override_path = REPO_ROOT / "knowledge" / "curation" / "exercise_library_overrides.json"

    bundle, warnings = build_exercise_library_foundation(
        onboarding_dir=onboarding_dir,
        source_registry_bundle=load_source_registry(),
        override_path=override_path,
        extraction_resolutions_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.resolutions.json",
        extraction_unresolved_output_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.unresolved.json",
    )
    override_bundle = ExerciseLibraryOverrideBundle.model_validate_json(override_path.read_text(encoding="utf-8"))
    overridden_ids = {record.exercise_id for record in override_bundle.records}
    records_by_id = {record.exercise_id: record for record in bundle.records}

    assert bundle.bundle_id == "exercise_library_foundation"
    assert bundle.schema_version == "knowledge-1"
    assert bundle.records
    assert warnings
    assert any("weak_point_exercise" in warning for warning in warnings)
    assert all(not record.exercise_id.startswith("weak_point_exercise") for record in bundle.records)
    assert any(len(record.source_program_ids) > 1 for record in bundle.records)
    assert overridden_ids
    assert all(set(item.model_dump(mode="json")) <= {"exercise_id", "fatigue_cost", "skill_demand", "stability_demand", "progression_compatibility"} for item in override_bundle.records)
    assert all(len(item.progression_compatibility) <= 1 for item in override_bundle.records)
    for exercise_id in overridden_ids:
        record = records_by_id[exercise_id]
        assert record.curation_status == "curated"
        assert any(ref.source_id == "curated-exercise-library-override-v1" for ref in record.provenance)
        assert any(ref.curation_status == "curated" for ref in record.provenance if ref.source_id == "curated-exercise-library-override-v1")
    barbell_rdl = records_by_id["barbell_rdl"]
    extracted_notes = [
        ref.note
        for ref in barbell_rdl.provenance
        if ref.section_ref == "exercise_intelligence_extraction:barbell_rdl:fatigue_cost"
    ]
    assert extracted_notes
    assert any("field=fatigue_cost" in note for note in extracted_notes if note is not None)
    assert any("source_program_id=pure_bodybuilding_phase_2_full_body" in note for note in extracted_notes if note is not None)
    low_incline_press = records_by_id["bottom_half_low_incline_db_press"]
    assert low_incline_press.stability_demand == "moderate"
    assert any(
        ref.section_ref == "exercise_intelligence_extraction:bottom_half_low_incline_db_press:stability_demand"
        for ref in low_incline_press.provenance
    )
    belt_squat = records_by_id["belt_squat"]
    assert belt_squat.skill_demand == "moderate"
    assert belt_squat.stability_demand == "moderate"
    assert any(
        ref.section_ref == "exercise_intelligence_extraction:belt_squat:skill_demand"
        and ref.note is not None
        and "rule=skill_moderate_compound_role_fallback" in ref.note
        for ref in belt_squat.provenance
    )
    bent_over_cable_pec_flye = records_by_id["bent_over_cable_pec_flye"]
    assert bent_over_cable_pec_flye.skill_demand == "moderate"
    assert bent_over_cable_pec_flye.stability_demand == "moderate"
    assert any(
        ref.section_ref == "exercise_intelligence_extraction:bent_over_cable_pec_flye:stability_demand"
        and ref.note is not None
        and "rule=stability_moderate_unilateral_or_unsupported_accessory_regex" in ref.note
        for ref in bent_over_cable_pec_flye.provenance
    )
    preacher_curl = records_by_id["bottom_half_ez_bar_preacher_curl"]
    assert preacher_curl.skill_demand == "low"
    assert preacher_curl.stability_demand == "low"
    assert any(
        ref.section_ref == "exercise_intelligence_extraction:bottom_half_ez_bar_preacher_curl:skill_demand"
        and ref.note is not None
        and (
            "rule=skill_low_supported_accessory_regex" in ref.note
            or "rule=skill_low_supported_accessory_or_isolation_local" in ref.note
        )
        for ref in preacher_curl.provenance
    )
    for exercise_id, record in records_by_id.items():
        if exercise_id not in overridden_ids:
            assert all(ref.source_id != "curated-exercise-library-override-v1" for ref in record.provenance)


def test_exercise_library_override_validation_rejects_unknown_fields_and_multiple_progression_tags(tmp_path: Path) -> None:
    onboarding_dir = REPO_ROOT / "programs" / "gold"
    invalid_override_path = tmp_path / "exercise_library_overrides.json"
    invalid_override_path.write_text(
        """
        {
          "schema_version": "knowledge-1",
          "bundle_id": "exercise_library_overrides",
          "bundle_version": "0.1.0",
          "records": [
            {
              "exercise_id": "flat_machine_chest_press",
              "fatigue_cost": "low",
              "progression_compatibility": ["high", "moderate"],
              "note": "not allowed"
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    with pytest.raises((ValidationError, ValueError)):
        build_exercise_library_foundation(
            onboarding_dir=onboarding_dir,
            source_registry_bundle=load_source_registry(),
            override_path=invalid_override_path,
            extraction_resolutions_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.resolutions.json",
            extraction_unresolved_output_path=REPO_ROOT / "knowledge" / "curation" / "exercise_library_extraction.unresolved.json",
        )
