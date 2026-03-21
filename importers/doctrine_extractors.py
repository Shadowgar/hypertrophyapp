#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable

from importers.doctrine_extraction import NormalizedBlock, NormalizedDocument, SourceEnvelope


@dataclass(frozen=True)
class EvidenceFragment:
    fragment_id: str
    source_id: str
    source_family_id: str
    track: str
    extractor_id: str
    block_id: str
    section_ref: str
    excerpt_text: str
    raw_extracted_value: Any
    local_context: dict[str, Any]
    excerpt_quality: float


def _fragment_id(*, extractor_id: str, source_id: str, block_id: str, raw_extracted_value: Any) -> str:
    digest = hashlib.sha256(
        json.dumps(
            {
                "extractor_id": extractor_id,
                "source_id": source_id,
                "block_id": block_id,
                "raw_extracted_value": raw_extracted_value,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:12]
    return f"{extractor_id}:{source_id}:{digest}"


class TableWorkbookExtractor:
    extractor_id = "table_workbook"

    def __init__(
        self,
        *,
        track: str,
        row_selector: Callable[[NormalizedBlock], bool],
        value_builder: Callable[[NormalizedBlock], Any | None],
    ) -> None:
        self.track = track
        self.row_selector = row_selector
        self.value_builder = value_builder

    def extract(
        self,
        *,
        source: SourceEnvelope,
        document: NormalizedDocument,
    ) -> list[EvidenceFragment]:
        fragments: list[EvidenceFragment] = []
        for block in document.blocks:
            if block.content_type != "row_group":
                continue
            if not self.row_selector(block):
                continue
            raw_extracted_value = self.value_builder(block)
            if raw_extracted_value is None:
                continue
            fragments.append(
                EvidenceFragment(
                    fragment_id=_fragment_id(
                        extractor_id=self.extractor_id,
                        source_id=source.source_id,
                        block_id=block.block_id,
                        raw_extracted_value=raw_extracted_value,
                    ),
                    source_id=source.source_id,
                    source_family_id=source.source_family_id,
                    track=self.track,
                    extractor_id=self.extractor_id,
                    block_id=block.block_id,
                    section_ref=block.section_ref,
                    excerpt_text=block.raw_text,
                    raw_extracted_value=raw_extracted_value,
                    local_context={
                        **dict(block.structured_fields),
                        "source_authority_weight": source.authority_weight,
                        "source_classification_confidence": source.classification_confidence,
                    },
                    excerpt_quality=1.0,
                )
            )
        return fragments


class StructureHeadingExtractor:
    extractor_id = "structure_heading"

    def __init__(
        self,
        *,
        track: str,
        heading_selector: Callable[[NormalizedBlock], bool],
        value_builder: Callable[[NormalizedBlock, list[NormalizedBlock]], Any | None],
    ) -> None:
        self.track = track
        self.heading_selector = heading_selector
        self.value_builder = value_builder

    def _collect_direct_descendants(
        self,
        *,
        heading: NormalizedBlock,
        document: NormalizedDocument,
    ) -> list[NormalizedBlock]:
        return [block for block in document.blocks if block.parent_block_id == heading.block_id]

    def extract(
        self,
        *,
        source: SourceEnvelope,
        document: NormalizedDocument,
    ) -> list[EvidenceFragment]:
        fragments: list[EvidenceFragment] = []
        for block in document.blocks:
            if block.content_type != "heading":
                continue
            if not self.heading_selector(block):
                continue
            descendants = self._collect_direct_descendants(heading=block, document=document)
            raw_extracted_value = self.value_builder(block, descendants)
            if raw_extracted_value is None:
                continue
            fragments.append(
                EvidenceFragment(
                    fragment_id=_fragment_id(
                        extractor_id=self.extractor_id,
                        source_id=source.source_id,
                        block_id=block.block_id,
                        raw_extracted_value=raw_extracted_value,
                    ),
                    source_id=source.source_id,
                    source_family_id=source.source_family_id,
                    track=self.track,
                    extractor_id=self.extractor_id,
                    block_id=block.block_id,
                    section_ref=block.section_ref,
                    excerpt_text=block.raw_text,
                    raw_extracted_value=raw_extracted_value,
                    local_context={
                        **dict(block.structured_fields),
                        "descendant_block_ids": [item.block_id for item in descendants],
                        "source_authority_weight": source.authority_weight,
                        "source_classification_confidence": source.classification_confidence,
                    },
                    excerpt_quality=0.9,
                )
            )
        return fragments
