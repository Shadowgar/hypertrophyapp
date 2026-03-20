from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_runtime_code_does_not_read_raw_reference_or_guide_artifacts() -> None:
    runtime_dirs = [
        _repo_root() / "apps" / "api" / "app",
        _repo_root() / "packages" / "core-engine" / "core_engine",
    ]
    forbidden_tokens = (
        "reference/",
        "docs/guides/generated",
        "asset_catalog.json",
        "provenance_index.json",
        "reference_corpus_ingest",
        "source_to_knowledge_pipeline",
    )

    for runtime_dir in runtime_dirs:
        for path in runtime_dir.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for token in forbidden_tokens:
                assert token not in source, f"{path} unexpectedly references forbidden runtime token: {token}"


def test_web_client_has_no_reference_pair_runtime_contract() -> None:
    api_client = _repo_root() / "apps" / "web" / "lib" / "api.ts"
    source = api_client.read_text(encoding="utf-8")

    assert "listReferencePairs" not in source
    assert "ReferenceWorkbookGuidePair" not in source
