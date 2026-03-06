#!/usr/bin/env python3
"""Deterministic build-time ingestion pipeline for /reference assets.

Outputs:
- docs/guides/asset_catalog.json
- docs/guides/provenance_index.json
- docs/guides/generated/*.md

Runtime services must never parse raw PDFs/XLSX/EPUB. This script is build-time only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, cast
import zipfile
from xml.etree import ElementTree as ET


SUPPORTED_EXTENSIONS = {".pdf", ".epub", ".xlsx"}
NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
}

PAIRING_TOKEN_STOPWORDS = {
    "a",
    "and",
    "copy",
    "ebook",
    "guide",
    "jeff",
    "lib",
    "library",
    "nippard",
    "of",
    "org",
    "pdf",
    "sk",
    "the",
    "workbook",
    "xlsx",
    "z",
    "zlibrary",
}

PAIRING_TOKEN_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "ppl": ("push", "pull", "legs"),
    "fb": ("full", "body"),
    "ul": ("upper", "lower"),
}

# Deterministic alias rules for known workbook naming variants in /reference.
WORKBOOK_PAIR_OVERRIDES: dict[str, tuple[str, ...]] = {
    "my-new-program": ("pure", "bodybuilding", "full", "body"),
    "my_new_program": ("pure", "bodybuilding", "full", "body"),
}


@dataclass(slots=True)
class ExtractionResult:
    text: str
    method: str


def sha256_bytes(data: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(data)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "asset"


def normalize_text(value: str) -> str:
    compact = re.sub(r"\s+", " ", value)
    return compact.strip()


def _resolve_epub_text(path: Path) -> ExtractionResult:
    text_chunks: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = sorted(
            name
            for name in archive.namelist()
            if name.lower().endswith((".xhtml", ".html", ".htm"))
        )
        for name in names:
            raw = archive.read(name)
            html = raw.decode("utf-8", errors="ignore")
            stripped = re.sub(r"<[^>]+>", " ", html)
            stripped = normalize_text(stripped)
            if stripped:
                text_chunks.append(stripped)

    return ExtractionResult(text="\n".join(text_chunks), method="epub_zip_html")


def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []

    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    shared_strings: list[str] = []
    for item in root.findall("a:si", NS):
        tokens = [node.text or "" for node in item.findall(".//a:t", NS)]
        shared_strings.append("".join(tokens))
    return shared_strings


def _xlsx_sheet_paths(archive: zipfile.ZipFile) -> list[str]:
    return sorted(
        name
        for name in archive.namelist()
        if name.startswith("xl/worksheets/") and name.endswith(".xml")
    )


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    inline = cell.find("a:is/a:t", NS)
    if inline is not None:
        return inline.text or ""

    value_node = cell.find("a:v", NS)
    if value_node is None:
        return ""

    raw = value_node.text or ""
    if cell.attrib.get("t") == "s" and raw.isdigit():
        idx = int(raw)
        if 0 <= idx < len(shared_strings):
            return shared_strings[idx]
    return raw


def _resolve_xlsx_text(path: Path) -> ExtractionResult:
    rows: list[str] = []
    with zipfile.ZipFile(path) as archive:
        shared_strings = _read_shared_strings(archive)
        for sheet_path in _xlsx_sheet_paths(archive):
            root = ET.fromstring(archive.read(sheet_path))
            for row in root.findall("a:sheetData/a:row", NS):
                values = [
                    _cell_value(cell, shared_strings).strip()
                    for cell in row.findall("a:c", NS)
                ]
                values = [value for value in values if value]
                if values:
                    rows.append(" | ".join(values))

    return ExtractionResult(text="\n".join(rows), method="xlsx_zip_xml")


def _resolve_pdf_text(path: Path) -> ExtractionResult:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ExtractionResult(text="", method="pdf_unavailable")

    chunks: list[str] = []
    try:
        reader = PdfReader(str(path))
        for page in reader.pages:
            extracted = page.extract_text() or ""
            normalized = normalize_text(extracted)
            if normalized:
                chunks.append(normalized)
    except Exception:
        return ExtractionResult(text="", method="pdf_parse_failed")

    return ExtractionResult(text="\n".join(chunks), method="pdf_pypdf")


def extract_asset_text(path: Path, *, metadata_only: bool = False) -> ExtractionResult:
    if metadata_only:
        asset_type = path.suffix.lower().lstrip(".") or "asset"
        return ExtractionResult(text="", method=f"{asset_type}_metadata_only")

    extension = path.suffix.lower()
    if extension == ".xlsx":
        return _resolve_xlsx_text(path)
    if extension == ".epub":
        return _resolve_epub_text(path)
    if extension == ".pdf":
        return _resolve_pdf_text(path)
    return ExtractionResult(text="", method="unsupported")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _asset_rank(path: Path, project_root: Path) -> tuple[int, int, str]:
    rel = safe_relative(path, project_root).lower()
    noisy_markers = ("copy of", "z-library", "z-lib", "(1)")
    noisy_penalty = 1 if any(marker in rel for marker in noisy_markers) else 0
    return (noisy_penalty, len(rel), rel)


def _canonical_asset_path(paths: list[Path], project_root: Path) -> Path:
    return min(paths, key=lambda path: _asset_rank(path, project_root))


def _existing_paths(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.exists() and path.is_file()]


def _pairing_tokens(asset_path: str) -> set[str]:
    stem = Path(asset_path).stem.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", stem)
    tokens: set[str] = set()
    for raw in normalized.split():
        token = raw.strip()
        if not token or token in PAIRING_TOKEN_STOPWORDS:
            continue
        tokens.add(token)
        tokens.update(PAIRING_TOKEN_EXPANSIONS.get(token, ()))

        # Handle collapsed compound words from source file naming variants.
        if "bodybuilding" in token:
            tokens.add("bodybuilding")
        if token.startswith("pure"):
            tokens.add("pure")
        if "powerbuilding" in token:
            tokens.add("powerbuilding")

    return tokens


def _workbook_pdf_match_score(
    workbook_path: str,
    workbook_tokens: set[str],
    pdf_path: str,
    pdf_tokens: set[str],
) -> int:
    workbook_slug = slugify(Path(workbook_path).stem)
    pdf_slug = slugify(Path(pdf_path).stem)
    overlap = len(workbook_tokens.intersection(pdf_tokens))
    score = overlap

    if workbook_slug and workbook_slug in pdf_slug:
        score += 2
    if pdf_slug and pdf_slug in workbook_slug:
        score += 2

    workbook_override = set(WORKBOOK_PAIR_OVERRIDES.get(workbook_slug, ()))
    if workbook_override and workbook_override.issubset(pdf_tokens):
        score += 100

    return score


def _best_pdf_guide_for_workbook(
    workbook_path: str,
    workbook_tokens: set[str],
    pdf_index: list[tuple[dict[str, object], set[str]]],
) -> tuple[dict[str, object] | None, int]:
    best_candidate: dict[str, object] | None = None
    best_score = -1
    for guide, guide_tokens in pdf_index:
        score = _workbook_pdf_match_score(
            workbook_path,
            workbook_tokens,
            str(guide.get("asset_path") or ""),
            guide_tokens,
        )
        if score > best_score:
            best_score = score
            best_candidate = guide
    return best_candidate, best_score


def _raise_missing_workbook_pairs(missing: list[str]) -> None:
    if not missing:
        return
    missing_list = ", ".join(sorted(missing))
    raise ValueError(
        "Workbook/PDF pairing enforcement failed; missing guide pairing for: "
        f"{missing_list}"
    )


def _resolve_workbook_pdf_pairs(asset_catalog: list[dict[str, object]]) -> list[dict[str, object]]:
    workbooks = [item for item in asset_catalog if str(item.get("asset_type")) == "xlsx"]
    pdf_guides = [item for item in asset_catalog if str(item.get("asset_type")) == "pdf"]
    pdf_index = [(item, _pairing_tokens(str(item.get("asset_path") or ""))) for item in pdf_guides]

    pairs: list[dict[str, object]] = []
    missing: list[str] = []
    for workbook in workbooks:
        workbook_path = str(workbook.get("asset_path") or "")
        workbook_tokens = _pairing_tokens(workbook_path)
        best_candidate, best_score = _best_pdf_guide_for_workbook(workbook_path, workbook_tokens, pdf_index)

        # Require at least modest lexical overlap unless an override boosted score.
        if best_candidate is None or best_score < 2:
            missing.append(workbook_path)
            continue

        pairs.append(
            {
                "workbook_asset_path": workbook_path,
                "workbook_asset_sha256": str(workbook.get("asset_sha256") or ""),
                "guide_asset_path": str(best_candidate.get("asset_path") or ""),
                "guide_asset_sha256": str(best_candidate.get("asset_sha256") or ""),
                "match_score": best_score,
            }
        )

    _raise_missing_workbook_pairs(missing)
    pairs.sort(key=lambda item: str(item["workbook_asset_path"]))
    return pairs


def build_reference_catalog(
    reference_dir: Path,
    guides_dir: Path,
    *,
    metadata_only: bool = False,
) -> dict[str, Any]:
    project_root = reference_dir.parent
    assets = sorted(
        (path for path in reference_dir.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS),
        key=lambda item: item.name.lower(),
    )

    generated_dir = guides_dir / "generated"
    asset_catalog: list[dict[str, object]] = []
    provenance_index: list[dict[str, object]] = []
    duplicate_assets: list[dict[str, object]] = []

    assets_by_sha: dict[str, list[Path]] = {}
    for asset_path in assets:
        try:
            checksum = sha256_file(asset_path)
        except FileNotFoundError:
            # Asset disappeared mid-run; skip instead of failing whole deterministic build.
            continue
        assets_by_sha.setdefault(checksum, []).append(asset_path)

    ordered_checksums = sorted(
        assets_by_sha,
        key=lambda checksum: safe_relative(
            _canonical_asset_path(assets_by_sha[checksum], project_root),
            project_root,
        ),
    )

    for checksum in ordered_checksums:
        grouped_paths = sorted(_existing_paths(assets_by_sha[checksum]), key=lambda path: path.name.lower())
        if not grouped_paths:
            continue
        canonical_path = _canonical_asset_path(grouped_paths, project_root)
        try:
            raw_bytes = canonical_path.read_bytes()
        except FileNotFoundError:
            continue
        relative = safe_relative(canonical_path, project_root)
        extraction = extract_asset_text(canonical_path, metadata_only=metadata_only)
        normalized = normalize_text(extraction.text)
        excerpt = normalized[:2000]

        source_asset_paths = sorted(safe_relative(path, project_root) for path in grouped_paths)
        duplicate_asset_paths = [path for path in source_asset_paths if path != relative]
        if duplicate_asset_paths:
            duplicate_assets.append(
                {
                    "asset_sha256": checksum,
                    "canonical_asset_path": relative,
                    "duplicate_asset_paths": duplicate_asset_paths,
                }
            )

        slug = slugify(canonical_path.stem)
        markdown_name = f"{slug}-{checksum[:8]}.md"
        markdown_path = generated_dir / markdown_name
        derived_rel = safe_relative(markdown_path, project_root)

        md_lines = [
            "# Normalized Reference Guide",
            "",
            f"- Asset: {relative}",
            f"- SHA256: {checksum}",
            f"- Type: {canonical_path.suffix.lower().lstrip('.')}",
            f"- Extraction Method: {extraction.method}",
            f"- Extracted Characters: {len(normalized)}",
            "",
            "## Excerpt",
            "",
            excerpt if excerpt else "(No text extracted)",
            "",
        ]
        write_markdown(markdown_path, "\n".join(md_lines))

        asset_catalog.append(
            {
                "asset_path": relative,
                "asset_sha256": checksum,
                "asset_type": canonical_path.suffix.lower().lstrip("."),
                "bytes": len(raw_bytes),
                "derived_doc": derived_rel,
                "extraction_method": extraction.method,
                "text_sha256": sha256_bytes(normalized.encode("utf-8")),
                "extracted_characters": len(normalized),
                "source_asset_paths": source_asset_paths,
                "duplicate_asset_paths": duplicate_asset_paths,
            }
        )

        provenance_index.append(
            {
                "asset": relative,
                "asset_sha256": checksum,
                "derived_entities": [
                    {
                        "type": "normalized_guide_doc",
                        "path": derived_rel,
                        "text_sha256": sha256_bytes(normalized.encode("utf-8")),
                    }
                ],
                "source_assets": source_asset_paths,
            }
        )

    workbook_pdf_pairs = _resolve_workbook_pdf_pairs(asset_catalog)

    aggregate_signature_input = "\n".join(str(item["asset_sha256"]) for item in asset_catalog)
    aggregate_signature = sha256_bytes(aggregate_signature_input.encode("utf-8"))

    asset_catalog_payload = {
        "version": 2,
        "asset_count": len(asset_catalog),
        "source_asset_count": len(assets),
        "duplicate_asset_count": sum(len(item["duplicate_asset_paths"]) for item in duplicate_assets),
        "aggregate_signature": aggregate_signature,
        "duplicate_assets": duplicate_assets,
        "workbook_pdf_pair_count": len(workbook_pdf_pairs),
        "workbook_pdf_pairs": workbook_pdf_pairs,
        "assets": asset_catalog,
    }
    provenance_payload = {
        "version": 2,
        "asset_count": len(provenance_index),
        "source_asset_count": len(assets),
        "aggregate_signature": aggregate_signature,
        "workbook_pdf_pairs": workbook_pdf_pairs,
        "provenance": provenance_index,
    }

    write_json(guides_dir / "asset_catalog.json", asset_catalog_payload)
    write_json(guides_dir / "provenance_index.json", provenance_payload)

    return {
        "asset_catalog": asset_catalog_payload,
        "provenance_index": provenance_payload,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministically ingest /reference corpus")
    parser.add_argument("--reference-dir", default="reference", help="Directory containing source assets")
    parser.add_argument("--guides-dir", default="docs/guides", help="Output directory for generated guides and indexes")
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Skip text extraction and emit metadata-only artifacts for fast validation runs",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    reference_dir = (repo_root / args.reference_dir).resolve()
    guides_dir = (repo_root / args.guides_dir).resolve()

    if not reference_dir.exists() or not reference_dir.is_dir():
        raise SystemExit(f"Reference directory not found: {reference_dir}")

    result = cast(
        dict[str, Any],
        build_reference_catalog(
            reference_dir,
            guides_dir,
            metadata_only=bool(args.metadata_only),
        ),
    )
    catalog = cast(dict[str, Any], result["asset_catalog"])
    assets = cast(list[dict[str, Any]], catalog.get("assets", []))
    pdf_unavailable_assets = [
        str(item.get("asset_path"))
        for item in assets
        if str(item.get("asset_type")) == "pdf" and str(item.get("extraction_method")) == "pdf_unavailable"
    ]
    if pdf_unavailable_assets:
        raise SystemExit(
            "PDF extraction is unavailable. Install pypdf and rerun ingestion. "
            f"Missing parser for {len(pdf_unavailable_assets)} PDF assets."
        )

    print(
        json.dumps(
            {
                "asset_count": catalog["asset_count"],
                "mode": "metadata_only" if args.metadata_only else "full_extraction",
                "aggregate_signature": catalog["aggregate_signature"],
                "asset_catalog": safe_relative(guides_dir / "asset_catalog.json", repo_root),
                "provenance_index": safe_relative(guides_dir / "provenance_index.json", repo_root),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
