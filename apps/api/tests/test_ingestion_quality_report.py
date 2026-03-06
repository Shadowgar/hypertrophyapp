import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importers.ingestion_quality_report import build_ingestion_quality_report, markdown_summary


def _write_program(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_ingestion_quality_report_flags_structural_and_missing_fields(tmp_path: Path) -> None:
    _write_program(
        tmp_path / "noisy.json",
        {
            "id": "noisy",
            "split": "full_body",
            "sessions": [
                {
                    "name": "WARM UP PROTOCOL",
                    "exercises": [
                        {
                            "id": "warm_up_protocol",
                            "name": "WARM UP PROTOCOL",
                            "sets": 3,
                            "rep_range": [8, 12],
                            "video": None,
                        }
                    ],
                },
                {
                    "name": "Full Body #1",
                    "exercises": [
                        {
                            "id": "bench",
                            "name": "Bench Press",
                            "sets": 3,
                            "rep_range": [8, 10],
                            "video": {"youtube_url": "https://youtu.be/example"},
                        },
                        {
                            "id": "row",
                            "name": "Row",
                            "sets": 0,
                            "rep_range": [10, 12],
                            "video": None,
                        },
                    ],
                },
            ],
        },
    )

    report = build_ingestion_quality_report(tmp_path)

    assert report["totals"]["template_count"] == 1
    assert report["totals"]["invalid_sessions"] == 1
    assert report["totals"]["missing_reps_sets"] == 1
    assert report["totals"]["missing_video_links"] == 2
    assert report["totals"]["templates_requiring_normalization"] == 1

    template = report["templates"][0]
    assert template["template_id"] == "noisy"
    assert template["normalization_required"] is True
    assert template["structural_session_count"] == 1
    assert template["sample_invalid_sessions"] == ["WARM UP PROTOCOL"]

    candidates = report["normalization_candidates"]
    assert len(candidates) == 1
    assert candidates[0]["template_id"] == "noisy"


def test_ingestion_quality_report_all_clean_template(tmp_path: Path) -> None:
    _write_program(
        tmp_path / "clean.json",
        {
            "id": "clean",
            "split": "full_body",
            "sessions": [
                {
                    "name": "Day 1",
                    "exercises": [
                        {
                            "id": "bench",
                            "name": "Bench Press",
                            "sets": 3,
                            "rep_range": [8, 10],
                            "video": {"youtube_url": "https://youtube.com/watch?v=abc"},
                        },
                        {
                            "id": "row",
                            "name": "Cable Row",
                            "sets": 3,
                            "rep_range": [10, 12],
                            "video": {"youtube_url": "https://youtu.be/xyz"},
                        },
                    ],
                }
            ],
        },
    )

    report = build_ingestion_quality_report(tmp_path)
    assert report["totals"]["invalid_sessions"] == 0
    assert report["totals"]["missing_reps_sets"] == 0
    assert report["totals"]["missing_video_links"] == 0
    assert report["totals"]["templates_requiring_normalization"] == 0
    assert report["normalization_candidates"] == []

    markdown = markdown_summary(report)
    assert "Templates scanned: 1" in markdown
    assert "| `clean` | 0 | 0 | 0 | no |" in markdown
