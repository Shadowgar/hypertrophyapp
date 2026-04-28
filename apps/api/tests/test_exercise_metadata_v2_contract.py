import json
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.knowledge_loader import load_exercise_library, load_exercise_metadata_v2
from app.knowledge_schema import CanonicalExerciseRecord, ExerciseMetadataV2Bundle


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_metadata_v2_curated_and_compiled_artifacts_validate() -> None:
    curated_path = REPO_ROOT / "knowledge" / "curation" / "exercise_metadata.v2.json"
    compiled_path = REPO_ROOT / "knowledge" / "compiled" / "exercise_library.metadata.v2.json"

    curated_bundle = ExerciseMetadataV2Bundle.model_validate(_load_json(curated_path))
    compiled_bundle = ExerciseMetadataV2Bundle.model_validate(_load_json(compiled_path))

    assert curated_bundle.records
    assert compiled_bundle.records
    assert curated_bundle.schema_version == "knowledge-2"
    assert compiled_bundle.schema_version == "knowledge-2"


def test_metadata_v2_compiled_artifact_loads() -> None:
    bundle = load_exercise_metadata_v2()

    assert bundle is not None
    assert bundle.bundle_id == "exercise_library_metadata_v2"
    assert len(bundle.records) >= 7


def test_missing_metadata_v2_artifact_is_tolerated(tmp_path: Path) -> None:
    compiled_dir = tmp_path / "knowledge" / "compiled"
    compiled_dir.mkdir(parents=True)

    foundation_src = REPO_ROOT / "knowledge" / "compiled" / "exercise_library.foundation.v1.json"
    (compiled_dir / "exercise_library.foundation.v1.json").write_text(foundation_src.read_text(encoding="utf-8"), encoding="utf-8")

    bundle = load_exercise_metadata_v2(compiled_dir)
    exercise_library = load_exercise_library(compiled_dir)

    assert bundle is None
    assert exercise_library.records


def test_metadata_v2_exercise_ids_exist_in_canonical_library() -> None:
    bundle = load_exercise_metadata_v2()
    assert bundle is not None
    canonical_ids = {record.exercise_id for record in load_exercise_library().records}

    for record in bundle.records:
        assert record.exercise_id in canonical_ids


def test_metadata_v2_enum_constraints_reject_invalid_values() -> None:
    payload = _load_json(REPO_ROOT / "knowledge" / "compiled" / "exercise_library.metadata.v2.json")
    payload["records"][0]["metadata_v2"]["movement"]["primary_pattern"] = "bad_pattern"

    with pytest.raises(ValidationError):
        ExerciseMetadataV2Bundle.model_validate(payload)


def test_restriction_flags_are_normalized_and_not_free_text() -> None:
    bundle = load_exercise_metadata_v2()
    assert bundle is not None

    for record in bundle.records:
        flags = record.metadata_v2.restrictions.flags
        for flag in flags:
            assert flag == flag.strip()
            assert " " not in flag
            assert flag.startswith("avoid_")


def test_canonical_exercise_record_backward_compatible_without_metadata_v2() -> None:
    payload = {
        "exercise_id": "compat_test",
        "canonical_name": "Compatibility Test Exercise",
        "family_id": "compat_family",
        "confidence": 0.5,
    }

    record = CanonicalExerciseRecord.model_validate(payload)

    assert record.metadata_v2 is None
