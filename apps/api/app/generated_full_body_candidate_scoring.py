from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .generated_assessment_schema import UserAssessment
from .generated_full_body_blueprint_schema import GeneratedFullBodyBlueprintInput
from .generated_full_body_template_draft_schema import (
    ExerciseSelectionTrace,
    ScoredCandidateTrace,
    SelectionMode,
)
from .knowledge_schema import DoctrineBundle, DoctrineRuleStub


SCORING_RULE_ID = "full_body_candidate_scoring_v1"
SCORING_DIMENSIONS = (
    "stimulus_fit",
    "recoverability_fit",
    "complexity_fit",
    "progression_fit",
    "weak_point_alignment",
    "practicality_fit",
    "family_redundancy_penalty",
)
SCORING_MODES = ("required_slot", "weak_point_slot", "optional_fill")
TIE_BREAK_FIELDS = (
    "total_score_desc",
    "stimulus_fit_desc",
    "weak_point_alignment_desc",
    "recoverability_fit_desc",
    "progression_fit_desc",
    "weekly_assignment_count_asc",
    "exercise_id_asc",
)
TARGET_MUSCLES_BY_PATTERN: dict[str, set[str]] = {
    "squat": {"glutes", "quads"},
    "hinge": {"erectors", "glutes", "hamstrings"},
    "horizontal_press": {"chest", "front_delts", "triceps"},
    "horizontal_pull": {"biceps", "lats", "mid_back", "rear_delts", "upper_back"},
    "vertical_pull": {"biceps", "lats"},
    "vertical_press": {"front_delts", "triceps"},
}


@dataclass(frozen=True)
class ScoringContract:
    rule_id: str
    dimension_bands: dict[str, int]
    dimension_weights: dict[str, dict[str, int]]
    minimum_total_score_floor: dict[str, int | None]
    tie_break_order: list[str]


@dataclass(frozen=True)
class CandidateSelectionResult:
    selected_id: str
    selection_trace: ExerciseSelectionTrace
    total_score: int
    score_floor: int | None
    cleared_score_floor: bool


@dataclass(frozen=True)
class _ScoredCandidate:
    exercise_id: str
    total_score: int
    dimension_scores: dict[str, int]
    metadata_defaults_used: list[str]


def _rule_index(bundle: DoctrineBundle) -> dict[str, DoctrineRuleStub]:
    index: dict[str, DoctrineRuleStub] = {}
    for rules in bundle.rules_by_module.values():
        for rule in rules:
            index[rule.rule_id] = rule
    return index


def _scoring_contract(doctrine_bundle: DoctrineBundle) -> ScoringContract:
    rule = _rule_index(doctrine_bundle).get(SCORING_RULE_ID)
    if rule is None or not rule.payload:
        raise ValueError(f"doctrine bundle missing required payload rule: {SCORING_RULE_ID}")

    payload = rule.payload
    bands = payload.get("dimension_bands")
    weights = payload.get("dimension_weights")
    floors = payload.get("minimum_total_score_floor")
    tie_break_order = payload.get("tie_break_order")
    if not isinstance(bands, dict) or not isinstance(weights, dict) or not isinstance(floors, dict) or not isinstance(tie_break_order, list):
        raise ValueError("candidate scoring doctrine payload is malformed")

    expected_band_keys = {"strong_positive", "positive", "neutral", "negative", "strong_negative"}
    if set(bands) != expected_band_keys:
        raise ValueError("candidate scoring doctrine payload missing expected dimension bands")
    if set(weights) != set(SCORING_MODES):
        raise ValueError("candidate scoring doctrine payload missing expected scoring modes")
    if set(floors) != set(SCORING_MODES):
        raise ValueError("candidate scoring doctrine payload missing expected score floors")
    for mode in SCORING_MODES:
        if set(weights[mode]) != set(SCORING_DIMENSIONS):
            raise ValueError(f"candidate scoring doctrine payload missing expected dimensions for {mode}")
    if tuple(tie_break_order) != TIE_BREAK_FIELDS:
        raise ValueError("candidate scoring doctrine payload has unexpected tie-break order")

    return ScoringContract(
        rule_id=rule.rule_id,
        dimension_bands={str(key): int(value) for key, value in bands.items()},
        dimension_weights={
            str(mode): {str(key): int(value) for key, value in profile.items()}
            for mode, profile in weights.items()
        },
        minimum_total_score_floor={
            str(mode): (int(value) if value is not None else None)
            for mode, value in floors.items()
        },
        tie_break_order=[str(item) for item in tie_break_order],
    )


def _band_score(bands: dict[str, int], name: str) -> int:
    return int(bands[name])


def _first_progression_level(record: dict[str, Any]) -> str | None:
    compatibility = list(record.get("progression_compatibility") or [])
    return str(compatibility[0]) if compatibility else None


def _primary_secondary_alignment(record: dict[str, Any], targets: list[str]) -> str:
    target_set = {item for item in targets if item}
    if not target_set:
        return "none"
    primary = set(record.get("primary_muscles") or [])
    secondary = set(record.get("secondary_muscles") or [])
    if primary.intersection(target_set):
        return "primary"
    if secondary.intersection(target_set):
        return "secondary"
    return "none"


def _pattern_targets(pattern: str | None) -> list[str]:
    if pattern is None:
        return []
    return sorted(TARGET_MUSCLES_BY_PATTERN.get(pattern, set()))


def _stimulus_fit(
    *,
    record: dict[str, Any],
    selection_mode: SelectionMode,
    target_movement_pattern: str | None,
    target_weak_point_muscles: list[str],
    bands: dict[str, int],
) -> int:
    if selection_mode == "required_slot":
        if record.get("movement_pattern") != target_movement_pattern:
            return _band_score(bands, "strong_negative")
        alignment = _primary_secondary_alignment(record, _pattern_targets(target_movement_pattern))
        if alignment == "primary":
            return _band_score(bands, "strong_positive")
        if alignment == "secondary":
            return _band_score(bands, "positive")
        return _band_score(bands, "neutral")
    if selection_mode == "weak_point_slot":
        alignment = _primary_secondary_alignment(record, target_weak_point_muscles)
        if alignment == "primary":
            return _band_score(bands, "strong_positive")
        if alignment == "secondary":
            return _band_score(bands, "positive")
        return _band_score(bands, "neutral")
    return _band_score(bands, "positive")


def _preferred_recoverability_band(
    *,
    assessment: UserAssessment,
    blueprint_input: GeneratedFullBodyBlueprintInput,
    selection_mode: SelectionMode,
    session_exercise_count: int,
    target_exercises_per_session: int,
) -> str:
    if (
        assessment.recovery_profile == "low_recovery"
        or assessment.comeback_flag
        or blueprint_input.volume_tier == "conservative"
        or assessment.schedule_profile == "inconsistent_schedule"
    ):
        return "low"
    if selection_mode == "optional_fill" and (
        assessment.schedule_profile == "low_time"
        or session_exercise_count >= max(1, target_exercises_per_session - 1)
    ):
        return "low"
    return "moderate"


def _band_fit_score(actual: str | None, preferred: str, bands: dict[str, int]) -> int:
    if actual is None:
        return _band_score(bands, "neutral")
    lookup = {
        "low": {
            "low": _band_score(bands, "strong_positive"),
            "moderate": _band_score(bands, "positive"),
            "high": _band_score(bands, "strong_negative"),
        },
        "moderate": {
            "low": _band_score(bands, "positive"),
            "moderate": _band_score(bands, "strong_positive"),
            "high": _band_score(bands, "negative"),
        },
    }
    return int(lookup[preferred][actual])


def _recoverability_fit(
    *,
    record: dict[str, Any],
    assessment: UserAssessment,
    blueprint_input: GeneratedFullBodyBlueprintInput,
    selection_mode: SelectionMode,
    session_exercise_count: int,
    target_exercises_per_session: int,
    bands: dict[str, int],
) -> int:
    preferred = _preferred_recoverability_band(
        assessment=assessment,
        blueprint_input=blueprint_input,
        selection_mode=selection_mode,
        session_exercise_count=session_exercise_count,
        target_exercises_per_session=target_exercises_per_session,
    )
    return _band_fit_score(record.get("fatigue_cost"), preferred, bands)


def _preferred_complexity_band(
    *,
    assessment: UserAssessment,
    blueprint_input: GeneratedFullBodyBlueprintInput,
) -> str:
    if blueprint_input.complexity_ceiling == "simple" or assessment.comeback_flag:
        return "low"
    return "moderate"


def _complexity_fit(
    *,
    record: dict[str, Any],
    assessment: UserAssessment,
    blueprint_input: GeneratedFullBodyBlueprintInput,
    bands: dict[str, int],
) -> int:
    preferred = _preferred_complexity_band(assessment=assessment, blueprint_input=blueprint_input)
    skill_score = _band_fit_score(record.get("skill_demand"), preferred, bands)
    stability_score = _band_fit_score(record.get("stability_demand"), preferred, bands)
    return min(skill_score, stability_score)


def _progression_fit(*, record: dict[str, Any], bands: dict[str, int]) -> int:
    level = _first_progression_level(record)
    if level is None:
        return _band_score(bands, "neutral")
    if level == "high":
        return _band_score(bands, "strong_positive")
    if level == "moderate":
        return _band_score(bands, "positive")
    return _band_score(bands, "negative")


def _weak_point_alignment(
    *,
    record: dict[str, Any],
    target_weak_point_muscles: list[str],
    bands: dict[str, int],
) -> int:
    alignment = _primary_secondary_alignment(record, target_weak_point_muscles)
    if alignment == "primary":
        return _band_score(bands, "strong_positive")
    if alignment == "secondary":
        return _band_score(bands, "positive")
    return _band_score(bands, "neutral")


def _practicality_fit(
    *,
    record: dict[str, Any],
    assessment: UserAssessment,
    selection_mode: SelectionMode,
    bands: dict[str, int],
) -> int:
    equipment_count = len(record.get("equipment_tags") or [])
    low_time = assessment.schedule_profile == "low_time" or (assessment.session_time_budget_minutes or 0) <= 45
    if equipment_count <= 1:
        return _band_score(bands, "strong_positive" if low_time or selection_mode == "optional_fill" else "positive")
    if equipment_count == 2:
        return _band_score(bands, "neutral")
    return _band_score(bands, "negative")


def _family_redundancy_penalty(
    *,
    record: dict[str, Any],
    assigned_counts: dict[str, int],
    weekly_selected_records: list[dict[str, Any]],
    bands: dict[str, int],
) -> int:
    if assigned_counts.get(record["exercise_id"], 0) > 0:
        return _band_score(bands, "strong_negative")
    family_id = str(record.get("family_id") or "")
    if family_id and any(str(item.get("family_id") or "") == family_id for item in weekly_selected_records):
        return _band_score(bands, "negative")
    return _band_score(bands, "neutral")


def _metadata_defaults_used(record: dict[str, Any]) -> list[str]:
    defaults: list[str] = []
    if record.get("fatigue_cost") is None:
        defaults.append("fatigue_cost")
    if record.get("skill_demand") is None:
        defaults.append("skill_demand")
    if record.get("stability_demand") is None:
        defaults.append("stability_demand")
    if not list(record.get("progression_compatibility") or []):
        defaults.append("progression_compatibility")
    return defaults


def _score_candidate(
    *,
    record: dict[str, Any],
    contract: ScoringContract,
    selection_mode: SelectionMode,
    assessment: UserAssessment,
    blueprint_input: GeneratedFullBodyBlueprintInput,
    target_movement_pattern: str | None,
    target_weak_point_muscles: list[str],
    session_exercise_count: int,
    target_exercises_per_session: int,
    assigned_counts: dict[str, int],
    weekly_selected_records: list[dict[str, Any]],
) -> _ScoredCandidate:
    bands = contract.dimension_bands
    dimension_scores = {
        "stimulus_fit": _stimulus_fit(
            record=record,
            selection_mode=selection_mode,
            target_movement_pattern=target_movement_pattern,
            target_weak_point_muscles=target_weak_point_muscles,
            bands=bands,
        ),
        "recoverability_fit": _recoverability_fit(
            record=record,
            assessment=assessment,
            blueprint_input=blueprint_input,
            selection_mode=selection_mode,
            session_exercise_count=session_exercise_count,
            target_exercises_per_session=target_exercises_per_session,
            bands=bands,
        ),
        "complexity_fit": _complexity_fit(
            record=record,
            assessment=assessment,
            blueprint_input=blueprint_input,
            bands=bands,
        ),
        "progression_fit": _progression_fit(record=record, bands=bands),
        "weak_point_alignment": _weak_point_alignment(
            record=record,
            target_weak_point_muscles=target_weak_point_muscles,
            bands=bands,
        ),
        "practicality_fit": _practicality_fit(
            record=record,
            assessment=assessment,
            selection_mode=selection_mode,
            bands=bands,
        ),
        "family_redundancy_penalty": _family_redundancy_penalty(
            record=record,
            assigned_counts=assigned_counts,
            weekly_selected_records=weekly_selected_records,
            bands=bands,
        ),
    }
    weights = contract.dimension_weights[selection_mode]
    total_score = sum(int(weights[key]) * int(value) for key, value in dimension_scores.items())
    return _ScoredCandidate(
        exercise_id=record["exercise_id"],
        total_score=total_score,
        dimension_scores=dimension_scores,
        metadata_defaults_used=_metadata_defaults_used(record),
    )


def _tie_break_key(
    *,
    scored_candidate: _ScoredCandidate,
    assigned_counts: dict[str, int],
) -> tuple[Any, ...]:
    return (
        -scored_candidate.total_score,
        -scored_candidate.dimension_scores["stimulus_fit"],
        -scored_candidate.dimension_scores["weak_point_alignment"],
        -scored_candidate.dimension_scores["recoverability_fit"],
        -scored_candidate.dimension_scores["progression_fit"],
        assigned_counts.get(scored_candidate.exercise_id, 0),
        scored_candidate.exercise_id,
    )


def select_scored_candidate(
    *,
    doctrine_bundle: DoctrineBundle,
    selection_mode: SelectionMode,
    candidate_ids: list[str],
    record_by_id: dict[str, dict[str, Any]],
    assessment: UserAssessment,
    blueprint_input: GeneratedFullBodyBlueprintInput,
    assigned_counts: dict[str, int],
    weekly_selected_exercise_ids: list[str],
    session_exercise_count: int,
    target_exercises_per_session: int,
    target_movement_pattern: str | None = None,
    target_weak_point_muscles: list[str] | None = None,
) -> CandidateSelectionResult | None:
    if not candidate_ids:
        return None

    contract = _scoring_contract(doctrine_bundle)
    target_weak_point_muscles = list(target_weak_point_muscles or [])
    weekly_selected_records = [
        record_by_id[exercise_id]
        for exercise_id in weekly_selected_exercise_ids
        if exercise_id in record_by_id
    ]
    scored_candidates = [
        _score_candidate(
            record=record_by_id[candidate_id],
            contract=contract,
            selection_mode=selection_mode,
            assessment=assessment,
            blueprint_input=blueprint_input,
            target_movement_pattern=target_movement_pattern,
            target_weak_point_muscles=target_weak_point_muscles,
            session_exercise_count=session_exercise_count,
            target_exercises_per_session=target_exercises_per_session,
            assigned_counts=assigned_counts,
            weekly_selected_records=weekly_selected_records,
        )
        for candidate_id in candidate_ids
        if candidate_id in record_by_id
    ]
    if not scored_candidates:
        return None

    ranked_candidates = sorted(
        scored_candidates,
        key=lambda item: _tie_break_key(scored_candidate=item, assigned_counts=assigned_counts),
    )
    winner = ranked_candidates[0]
    score_floor = contract.minimum_total_score_floor[selection_mode]
    cleared_score_floor = score_floor is None or winner.total_score >= score_floor
    return CandidateSelectionResult(
        selected_id=winner.exercise_id,
        selection_trace=ExerciseSelectionTrace(
            selection_mode=selection_mode,
            scoring_rule_id=contract.rule_id,
            candidate_pool_ids=list(candidate_ids),
            candidate_count=len(candidate_ids),
            dimension_scores=dict(winner.dimension_scores),
            dimension_weights=dict(contract.dimension_weights[selection_mode]),
            total_score=winner.total_score,
            top_candidates=[
                ScoredCandidateTrace(
                    exercise_id=item.exercise_id,
                    total_score=item.total_score,
                    dimension_scores=dict(item.dimension_scores),
                )
                for item in ranked_candidates[:3]
            ],
            metadata_defaults_used=list(winner.metadata_defaults_used),
        ),
        total_score=winner.total_score,
        score_floor=score_floor,
        cleared_score_floor=cleared_score_floor,
    )
