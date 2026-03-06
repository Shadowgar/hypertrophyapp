#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importers.ingestion_quality_report import build_ingestion_quality_report, markdown_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ingestion quality and template normalization report")
    parser.add_argument(
        "--programs-dir",
        type=Path,
        default=REPO_ROOT / "programs",
        help="Directory containing canonical program JSON templates",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=REPO_ROOT / "docs" / "validation" / "ingestion_quality_report.json",
        help="Output path for JSON report",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=REPO_ROOT / "docs" / "validation" / "ingestion_quality_report.md",
        help="Output path for markdown summary",
    )
    args = parser.parse_args()

    report = build_ingestion_quality_report(args.programs_dir)

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)

    args.json_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    args.markdown_output.write_text(markdown_summary(report), encoding="utf-8")

    print(f"Wrote JSON report: {args.json_output}")
    print(f"Wrote markdown summary: {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
