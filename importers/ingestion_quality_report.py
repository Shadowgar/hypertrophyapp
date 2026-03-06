from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any


_SESSION_META_LABELS = {
    "warm up protocol",
    "weak point table",
    "weak points table",
}

_EXERCISE_META_LABELS = {
    "warm up protocol",
    "weak point table",
    "weak points table",
    "mandatory rest day",
}

_SPLIT_DAY_LABEL_RE = re.compile(r"^(?:full\s*body|upper|lower|push|pull|legs?)\s*#?\s*\d+$", re.IGNORECASE)


@dataclass(frozen=True)
class TemplateQualitySummary:
    template_id: str
    source_file: str
    split: str
    session_count: int
    exercise_count: int
    invalid_session_count: int
    structural_session_count: int
    structural_exercise_count: int
    missing_prescription_count: int
    missing_video_count: int
    normalization_required: bool
    sample_invalid_sessions: list[str]
    sample_missing_prescription_exercises: list[str]
    sample_missing_video_exercises: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "source_file": self.source_file,
            "split": self.split,
            "session_count": self.session_count,
            "exercise_count": self.exercise_count,
            "invalid_session_count": self.invalid_session_count,
            "structural_session_count": self.structural_session_count,
            "structural_exercise_count": self.structural_exercise_count,
            "missing_prescription_count": self.missing_prescription_count,
            "missing_video_count": self.missing_video_count,
            "normalization_required": self.normalization_required,
            "sample_invalid_sessions": self.sample_invalid_sessions,
            "sample_missing_prescription_exercises": self.sample_missing_prescription_exercises,
            "sample_missing_video_exercises": self.sample_missing_video_exercises,
        }


@dataclass(frozen=True)
class NormalizationCandidate:
    template_id: str
    source_file: str
    issue_score: int
    reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "source_file": self.source_file,
            "issue_score": self.issue_score,
            "reasons": self.reasons,
        }


@dataclass(frozen=True)
class SessionQualitySummary:
    session_name: str
    exercise_count: int
    structural_exercise_count: int
    missing_prescription: list[str]
    missing_video: list[str]
    valid_workout_exercise_found: bool


def _normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def _is_structural_session_label(value: str) -> bool:
    normalized = _normalize_label(value)
    if not normalized:
        return True
    if normalized in _SESSION_META_LABELS:
        return True
    return normalized.startswith("week ") or normalized.startswith("block ")


def _is_structural_exercise_label(value: str) -> bool:
    normalized = _normalize_label(value)
    if not normalized:
        return True
    if normalized in _EXERCISE_META_LABELS:
        return True
    if normalized.startswith("week ") or normalized.startswith("block "):
        return True
    if _SPLIT_DAY_LABEL_RE.match(normalized):
        return True
    return False


def _has_valid_sets(exercise: dict[str, Any]) -> bool:
    sets_value = exercise.get("sets")
    return isinstance(sets_value, int) and sets_value >= 1


def _has_valid_rep_range(exercise: dict[str, Any]) -> bool:
    rep_range = exercise.get("rep_range")
    if not isinstance(rep_range, list) or len(rep_range) != 2:
        return False
    if not all(isinstance(item, int) for item in rep_range):
        return False
    return int(rep_range[0]) <= int(rep_range[1])


def _has_video_link(exercise: dict[str, Any]) -> bool:
    video = exercise.get("video")
    if not isinstance(video, dict):
        return False
    youtube = str(video.get("youtube_url") or "").strip()
    return youtube.startswith("http://") or youtube.startswith("https://")


def _exercise_key(exercise: dict[str, Any]) -> str:
    name = str(exercise.get("name") or "").strip()
    if name:
        return name
    return str(exercise.get("id") or "unknown_exercise")


def _analyze_exercise(session_name: str, exercise: Any) -> tuple[int, int, list[str], list[str], bool]:
    if not isinstance(exercise, dict):
        return (0, 0, [f"{session_name}:<non-object-exercise>"], [], False)

    exercise_name = _exercise_key(exercise)
    exercise_is_structural = _is_structural_exercise_label(exercise_name)
    has_prescription = _has_valid_sets(exercise) and _has_valid_rep_range(exercise)
    has_video = _has_video_link(exercise)

    structural_exercise_count = 1 if exercise_is_structural else 0
    missing_prescription = [] if has_prescription else [f"{session_name}:{exercise_name}"]
    missing_video = [] if has_video else [f"{session_name}:{exercise_name}"]
    valid_workout_exercise_found = (not exercise_is_structural) and has_prescription
    return (1, structural_exercise_count, missing_prescription, missing_video, valid_workout_exercise_found)


def _analyze_session(session: Any) -> tuple[SessionQualitySummary, bool, bool]:
    if not isinstance(session, dict):
        fallback = SessionQualitySummary(
            session_name="<non-object-session>",
            exercise_count=0,
            structural_exercise_count=0,
            missing_prescription=[],
            missing_video=[],
            valid_workout_exercise_found=False,
        )
        return (fallback, False, True)

    session_name = str(session.get("name") or "").strip() or "<unnamed-session>"
    session_is_structural = _is_structural_session_label(session_name)

    exercises_raw = session.get("exercises")
    exercises = exercises_raw if isinstance(exercises_raw, list) else []
    if not exercises:
        empty_summary = SessionQualitySummary(
            session_name=session_name,
            exercise_count=0,
            structural_exercise_count=0,
            missing_prescription=[],
            missing_video=[],
            valid_workout_exercise_found=False,
        )
        return (empty_summary, session_is_structural, True)

    exercise_count = 0
    structural_exercise_count = 0
    missing_prescription: list[str] = []
    missing_video: list[str] = []
    valid_workout_exercise_found = False

    for exercise in exercises:
        analyzed = _analyze_exercise(session_name, exercise)
        exercise_count += analyzed[0]
        structural_exercise_count += analyzed[1]
        missing_prescription.extend(analyzed[2])
        missing_video.extend(analyzed[3])
        valid_workout_exercise_found = valid_workout_exercise_found or analyzed[4]

    summary = SessionQualitySummary(
        session_name=session_name,
        exercise_count=exercise_count,
        structural_exercise_count=structural_exercise_count,
        missing_prescription=missing_prescription,
        missing_video=missing_video,
        valid_workout_exercise_found=valid_workout_exercise_found,
    )
    invalid_session = session_is_structural or (not valid_workout_exercise_found)
    return (summary, session_is_structural, invalid_session)


def _template_summary(path: Path, payload: dict[str, Any]) -> TemplateQualitySummary:
    template_id = str(payload.get("id") or path.stem)
    split = str(payload.get("split") or "unknown")

    sessions_raw = payload.get("sessions")
    sessions = sessions_raw if isinstance(sessions_raw, list) else []

    invalid_sessions: list[str] = []
    missing_prescription: list[str] = []
    missing_video: list[str] = []

    structural_session_count = 0
    structural_exercise_count = 0
    exercise_count = 0

    for session in sessions:
        summary, session_is_structural, invalid_session = _analyze_session(session)
        exercise_count += summary.exercise_count
        structural_exercise_count += summary.structural_exercise_count
        missing_prescription.extend(summary.missing_prescription)
        missing_video.extend(summary.missing_video)
        if session_is_structural:
            structural_session_count += 1
        if invalid_session:
            invalid_sessions.append(summary.session_name)

    invalid_session_count = len(invalid_sessions)
    missing_prescription_count = len(missing_prescription)
    missing_video_count = len(missing_video)
    normalization_required = any(
        [
            invalid_session_count > 0,
            structural_session_count > 0,
            structural_exercise_count > 0,
            missing_prescription_count > 0,
        ]
    )

    return TemplateQualitySummary(
        template_id=template_id,
        source_file=path.name,
        split=split,
        session_count=len(sessions),
        exercise_count=exercise_count,
        invalid_session_count=invalid_session_count,
        structural_session_count=structural_session_count,
        structural_exercise_count=structural_exercise_count,
        missing_prescription_count=missing_prescription_count,
        missing_video_count=missing_video_count,
        normalization_required=normalization_required,
        sample_invalid_sessions=sorted(invalid_sessions)[:5],
        sample_missing_prescription_exercises=sorted(missing_prescription)[:5],
        sample_missing_video_exercises=sorted(missing_video)[:5],
    )


def _normalization_candidates(summaries: list[TemplateQualitySummary]) -> list[NormalizationCandidate]:
    candidates: list[NormalizationCandidate] = []
    for summary in summaries:
        reasons: list[str] = []
        if summary.invalid_session_count > 0:
            reasons.append(f"invalid_sessions={summary.invalid_session_count}")
        if summary.structural_session_count > 0:
            reasons.append(f"structural_sessions={summary.structural_session_count}")
        if summary.structural_exercise_count > 0:
            reasons.append(f"structural_exercises={summary.structural_exercise_count}")
        if summary.missing_prescription_count > 0:
            reasons.append(f"missing_prescription={summary.missing_prescription_count}")

        if not reasons:
            continue

        issue_score = (
            summary.invalid_session_count * 5
            + summary.structural_session_count * 3
            + summary.structural_exercise_count * 2
            + summary.missing_prescription_count * 2
        )
        candidates.append(
            NormalizationCandidate(
                template_id=summary.template_id,
                source_file=summary.source_file,
                issue_score=issue_score,
                reasons=reasons,
            )
        )

    return sorted(
        candidates,
        key=lambda item: (-item.issue_score, item.template_id, item.source_file),
    )


def build_ingestion_quality_report(programs_dir: Path) -> dict[str, Any]:
    programs = sorted(programs_dir.glob("*.json"))
    summaries: list[TemplateQualitySummary] = []
    parse_failures: list[dict[str, str]] = []

    for path in programs:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            parse_failures.append({"source_file": path.name, "error": str(exc)})
            continue

        if not isinstance(payload, dict):
            parse_failures.append({"source_file": path.name, "error": "template root is not an object"})
            continue

        summaries.append(_template_summary(path, payload))

    candidates = _normalization_candidates(summaries)

    template_count = len(summaries)
    exercise_total = sum(item.exercise_count for item in summaries)
    invalid_sessions_total = sum(item.invalid_session_count for item in summaries)
    missing_prescription_total = sum(item.missing_prescription_count for item in summaries)
    missing_video_total = sum(item.missing_video_count for item in summaries)
    normalization_required_count = sum(1 for item in summaries if item.normalization_required)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "programs_dir": str(programs_dir.resolve()),
        "totals": {
            "template_count": template_count,
            "exercise_count": exercise_total,
            "invalid_sessions": invalid_sessions_total,
            "missing_reps_sets": missing_prescription_total,
            "missing_video_links": missing_video_total,
            "templates_requiring_normalization": normalization_required_count,
        },
        "templates": [item.as_dict() for item in summaries],
        "normalization_candidates": [item.as_dict() for item in candidates],
        "parse_failures": parse_failures,
    }
    return report


def markdown_summary(report: dict[str, Any]) -> str:
    totals = report.get("totals", {})
    templates = report.get("templates", [])
    candidates = report.get("normalization_candidates", [])

    lines = [
        "# Ingestion Quality Report",
        "",
        f"Generated: {report.get('generated_at', '')}",
        f"Programs Dir: `{report.get('programs_dir', '')}`",
        "",
        "## Totals",
        "",
        f"- Templates scanned: {totals.get('template_count', 0)}",
        f"- Exercises scanned: {totals.get('exercise_count', 0)}",
        f"- Invalid sessions: {totals.get('invalid_sessions', 0)}",
        f"- Missing reps/sets: {totals.get('missing_reps_sets', 0)}",
        f"- Missing video links: {totals.get('missing_video_links', 0)}",
        f"- Templates requiring normalization: {totals.get('templates_requiring_normalization', 0)}",
        "",
        "## Top Normalization Candidates",
        "",
    ]

    if candidates:
        for item in candidates[:10]:
            reasons = ", ".join(item.get("reasons", []))
            lines.append(
                f"- `{item.get('template_id', '')}` ({item.get('source_file', '')}): score={item.get('issue_score', 0)}; {reasons}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Template Snapshot", "", "| Template | Invalid Sessions | Missing Reps/Sets | Missing Video | Normalize? |", "| --- | ---: | ---: | ---: | --- |"])

    for item in templates:
        lines.append(
            f"| `{item.get('template_id', '')}` | {item.get('invalid_session_count', 0)} | {item.get('missing_prescription_count', 0)} | {item.get('missing_video_count', 0)} | {'yes' if item.get('normalization_required') else 'no'} |"
        )

    return "\n".join(lines) + "\n"
