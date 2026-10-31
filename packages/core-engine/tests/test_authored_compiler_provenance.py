"""Committed compiler/artifact parity; no licensed workbook is required."""
import json
from pathlib import Path

import pytest

from importers.authored_lineage import artifact_sha256, compiler_sha256

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('phase', [1, 2])
def test_committed_authored_artifacts_match_the_current_compiler(phase):
    name = f'pure_bodybuilding_phase_{phase}_full_body'
    canonical = json.loads((ROOT / 'programs/gold' / f'{name}.json').read_text())
    onboarding = json.loads((ROOT / 'programs/gold' / f'{name}.onboarding.json').read_text())
    current = compiler_sha256()
    assert canonical['source_provenance']['importer_sha256'] == current
    assert onboarding['source_provenance']['importer_sha256'] == current
    assert artifact_sha256(canonical) == canonical['source_provenance']['artifact_sha256']
    assert artifact_sha256(onboarding) == onboarding['source_provenance']['artifact_sha256']
    assert onboarding['source_provenance']['canonical_artifact_sha256'] == canonical['source_provenance']['artifact_sha256']
