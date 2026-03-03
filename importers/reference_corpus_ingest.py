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


def extract_asset_text(path: Path) -> ExtractionResult:
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


def build_reference_catalog(reference_dir: Path, guides_dir: Path) -> dict[str, Any]:
    project_root = reference_dir.parent
    assets = sorted(
        (path for path in reference_dir.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS),
        key=lambda item: item.name.lower(),
    )

    generated_dir = guides_dir / "generated"
    asset_catalog: list[dict[str, object]] = []
    provenance_index: list[dict[str, object]] = []

    for asset_path in assets:
        raw_bytes = asset_path.read_bytes()
        relative = safe_relative(asset_path, project_root)
        checksum = sha256_bytes(raw_bytes)
        extraction = extract_asset_text(asset_path)
        normalized = normalize_text(extraction.text)
        excerpt = normalized[:2000]

        slug = slugify(asset_path.stem)
        markdown_name = f"{slug}-{checksum[:8]}.md"
        markdown_path = generated_dir / markdown_name
        derived_rel = safe_relative(markdown_path, project_root)

        md_lines = [
            "# Normalized Reference Guide",
            "",
            f"- Asset: {relative}",
            f"- SHA256: {checksum}",
            f"- Type: {asset_path.suffix.lower().lstrip('.')}",
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
                "asset_type": asset_path.suffix.lower().lstrip("."),
                "bytes": len(raw_bytes),
                "derived_doc": derived_rel,
                "extraction_method": extraction.method,
                "text_sha256": sha256_bytes(normalized.encode("utf-8")),
                "extracted_characters": len(normalized),
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
            }
        )

    aggregate_signature_input = "\n".join(str(item["asset_sha256"]) for item in asset_catalog)
    aggregate_signature = sha256_bytes(aggregate_signature_input.encode("utf-8"))

    asset_catalog_payload = {
        "version": 1,
        "asset_count": len(asset_catalog),
        "aggregate_signature": aggregate_signature,
        "assets": asset_catalog,
    }
    provenance_payload = {
        "version": 1,
        "asset_count": len(provenance_index),
        "aggregate_signature": aggregate_signature,
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    reference_dir = (repo_root / args.reference_dir).resolve()
    guides_dir = (repo_root / args.guides_dir).resolve()

    if not reference_dir.exists() or not reference_dir.is_dir():
        raise SystemExit(f"Reference directory not found: {reference_dir}")

    result = cast(dict[str, Any], build_reference_catalog(reference_dir, guides_dir))
    catalog = cast(dict[str, Any], result["asset_catalog"])
    print(
        json.dumps(
            {
                "asset_count": catalog["asset_count"],
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
