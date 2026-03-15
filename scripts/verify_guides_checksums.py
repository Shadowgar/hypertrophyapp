#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_catalog_assets(repo_root: Path) -> tuple[list[dict], list[str]]:
    catalog_path = repo_root / "docs" / "guides" / "asset_catalog.json"
    if not catalog_path.exists():
        return ([], [f"missing catalog: {catalog_path}"])

    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    assets = payload.get("assets")
    if not isinstance(assets, list):
        return ([], ["asset_catalog assets must be a list"])

    rows = [item for item in assets if isinstance(item, dict)]
    failures = ["asset row is not an object" for item in assets if not isinstance(item, dict)]
    return (rows, failures)


def _verify_source_asset(repo_root: Path, item: dict[str, object]) -> list[str]:
    failures: list[str] = []
    asset_path_raw = str(item.get("asset_path") or "")
    asset_sha = str(item.get("asset_sha256") or "")
    asset_path = repo_root / asset_path_raw

    if not asset_path.exists():
        return [f"missing source asset: {asset_path_raw}"]

    computed_sha = sha256_file(asset_path)
    if computed_sha != asset_sha:
        failures.append(f"asset sha mismatch: {asset_path_raw}")
    return failures


def _verify_derived_doc(repo_root: Path, item: dict[str, object], *, require_non_empty: bool) -> list[str]:
    failures: list[str] = []
    derived_doc_raw = str(item.get("derived_doc") or "")
    derived_doc = repo_root / derived_doc_raw

    if not derived_doc.exists():
        return [f"missing derived doc: {derived_doc_raw}"]

    if require_non_empty:
        markdown = derived_doc.read_text(encoding="utf-8")
        if "(No text extracted)" in markdown:
            failures.append(f"empty excerpt marker in: {derived_doc_raw}")
    return failures


def _verify_extraction_quality(item: dict[str, object], *, require_non_empty: bool) -> list[str]:
    if not require_non_empty:
        return []

    failures: list[str] = []
    asset_path_raw = str(item.get("asset_path") or "")
    asset_type = str(item.get("asset_type") or "")
    extraction_method = str(item.get("extraction_method") or "")
    extracted_characters_raw = item.get("extracted_characters")
    if isinstance(extracted_characters_raw, int):
        extracted_characters = extracted_characters_raw
    elif isinstance(extracted_characters_raw, str) and extracted_characters_raw.isdigit():
        extracted_characters = int(extracted_characters_raw)
    else:
        extracted_characters = 0

    if asset_type not in {"pdf", "xlsx", "epub"}:
        return failures
    if extraction_method.endswith("_metadata_only"):
        failures.append(f"metadata-only extraction method for {asset_path_raw}")
    if asset_type == "pdf" and extraction_method == "pdf_unavailable":
        failures.append(f"pdf parser unavailable for {asset_path_raw}")
    if extracted_characters <= 0:
        failures.append(f"zero extracted characters for {asset_path_raw}")
    return failures


def verify_asset_catalog(repo_root: Path, require_non_empty: bool) -> list[str]:
    assets, failures = _read_catalog_assets(repo_root)
    for item in assets:
        failures.extend(_verify_source_asset(repo_root, item))
        failures.extend(_verify_derived_doc(repo_root, item, require_non_empty=require_non_empty))
        failures.extend(_verify_extraction_quality(item, require_non_empty=require_non_empty))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify docs/guides asset checksums and extraction outputs")
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Repository root containing docs/guides and reference",
    )
    parser.add_argument(
        "--require-non-empty",
        action="store_true",
        help="Require non-empty excerpts and full extraction methods for PDF/XLSX/EPUB assets",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    failures = verify_asset_catalog(repo_root, require_non_empty=bool(args.require_non_empty))

    if failures:
        print("[FAIL] guide verification failed")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("[PASS] guide checksum verification succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
