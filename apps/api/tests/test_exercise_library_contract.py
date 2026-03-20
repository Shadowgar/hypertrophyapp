from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importers.exercise_library_foundation import build_exercise_library_foundation


def test_exercise_library_foundation_builds_from_onboarding_packages_and_skips_placeholders() -> None:
    onboarding_dir = REPO_ROOT / "programs" / "gold"

    bundle, warnings = build_exercise_library_foundation(onboarding_dir=onboarding_dir)

    assert bundle.bundle_id == "exercise_library_foundation"
    assert bundle.schema_version == "knowledge-1"
    assert bundle.records
    assert warnings
    assert any("weak_point_exercise" in warning for warning in warnings)
    assert all(not record.exercise_id.startswith("weak_point_exercise") for record in bundle.records)
    assert any(len(record.source_program_ids) > 1 for record in bundle.records)
    assert all(record.curation_status == "seeded" for record in bundle.records)
