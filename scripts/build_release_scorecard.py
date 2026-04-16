#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _score_quality(report: dict[str, Any]) -> dict[str, Any]:
    progression = float(report.get("progression_quality", 0))
    fatigue = float(report.get("fatigue_stability", 0))
    adherence = float(report.get("adherence_retention", 0))
    weak_spot = float(report.get("weak_spot_improvement", 0))
    safety_violations = int(report.get("safety_violations", 0))
    aggregate = round((progression + fatigue + adherence + weak_spot) / 4, 3)
    status = "pass" if aggregate >= 0.75 and safety_violations == 0 else "fail"
    return {
        "aggregate_score": aggregate,
        "status": status,
        "gate": {
            "minimum_quality_score": 0.75,
            "required_safety_violations": 0,
            "safety_violations": safety_violations,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build release scorecard from benchmark output JSON.")
    parser.add_argument("--input", type=Path, required=True, help="Benchmark report JSON path")
    parser.add_argument("--output", type=Path, required=True, help="Scorecard output JSON path")
    args = parser.parse_args()

    report = _load_json(args.input)
    scored = _score_quality(report)
    output = {
        "benchmark_report_path": str(args.input),
        "scorecard": scored,
        "metrics": {
            "progression_quality": report.get("progression_quality"),
            "fatigue_stability": report.get("fatigue_stability"),
            "adherence_retention": report.get("adherence_retention"),
            "weak_spot_improvement": report.get("weak_spot_improvement"),
            "safety_violations": report.get("safety_violations"),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Scorecard written to {args.output}")


if __name__ == "__main__":
    main()

