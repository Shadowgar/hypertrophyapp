from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_runtime_api_does_not_read_guide_artifacts() -> None:
    plan_router = _repo_root() / "apps" / "api" / "app" / "routers" / "plan.py"
    source = plan_router.read_text(encoding="utf-8")

    forbidden_tokens = (
        "docs/guides",
        "asset_catalog.json",
        "provenance_index.json",
        "reference-pairs",
    )

    for token in forbidden_tokens:
        assert token not in source


def test_web_client_has_no_reference_pair_runtime_contract() -> None:
    api_client = _repo_root() / "apps" / "web" / "lib" / "api.ts"
    source = api_client.read_text(encoding="utf-8")

    assert "listReferencePairs" not in source
    assert "ReferenceWorkbookGuidePair" not in source
