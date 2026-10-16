"""Versioned, immutable inputs to the isolated Customized planning pilot.

All dose, effort, timing and calibration numbers are supplied by a separately
versioned policy or descriptive catalog. This package ships no science policy.
The caller must normalize onboarding and resolve effective history beforehand.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import math
from typing import Literal


SCHEMA_VERSION = "c1-schema-v1"
SKILLS = ("basic", "intermediate", "advanced")


def finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


@dataclass(frozen=True)
class SourceRef:
    reference: str
    version: str
    sha256: str

    def __post_init__(self):
        if (not self.reference or not self.version or len(self.sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.sha256)):
            raise ValueError("Source reference requires version and lowercase SHA-256")


@dataclass(frozen=True)
class DurationRange:
    low: float
    high: float

    def __post_init__(self):
        if not finite(self.low) or not finite(self.high) or not 0 <= self.low <= self.high:
            raise ValueError("Duration bounds must be finite, ordered and nonnegative")


@dataclass(frozen=True)
class LoadIdentity:
    variant_id: str
    implement: str
    equipment_key: str
    rom: str
    setup: str
    unit: Literal["kg", "lb"]
    basis: Literal["per_hand", "total_external", "machine_stack", "assistance", "bodyweight", "unknown"]


@dataclass(frozen=True)
class Exercise:
    variant_id: str
    name: str
    action: str
    required_equipment: tuple[str, ...]
    restriction_tags: tuple[str, ...]
    stability: str
    skill: str
    load_identity: LoadIdentity
    attainable_loads: tuple[float, ...]
    primary_regions: tuple[str, ...]
    secondary_regions: tuple[str, ...]
    unknown_regions: tuple[str, ...]
    setup_seconds: DurationRange
    work_seconds_per_set: DurationRange
    sources: tuple[SourceRef, ...]
    metadata_qualified: bool


@dataclass(frozen=True)
class ExerciseCatalog:
    version: str
    exercises: tuple[Exercise, ...]
    sources: tuple[SourceRef, ...]


@dataclass(frozen=True)
class CustomizedProfile:
    version: str
    mode: str
    consent_reference: str
    goal: str
    training_status: str
    selected_dates: tuple[date, ...]
    timezone: str
    session_cap_minutes: float
    cap_kind: Literal["hard", "flexible"]
    confirmed_equipment: tuple[str, ...]
    max_skill: str
    restrictions: tuple[str, ...]
    excluded_variants: tuple[str, ...]
    preferred_variants: tuple[str, ...]
    preferred_stability: str | None
    origins: tuple[tuple[str, str], ...]
    unsupported_controls: tuple[str, ...]


@dataclass(frozen=True)
class PlanningContext:
    version: str
    planning_instant: datetime
    week_start: date
    previous_training_date: date | None
    next_training_date: date | None


@dataclass(frozen=True)
class ActionDose:
    action: str
    sets: int
    emphasis_sets: int
    reps_min: int
    reps_max: int
    effort_kind: Literal["rir", "rpe10"]
    effort_min: float
    effort_max: float
    rest_seconds: DurationRange


@dataclass(frozen=True)
class CalibrationPolicy:
    history_max_age_days: int
    self_report_max_age_days: int
    minimum_completed_sets: int
    underchallenge_rir: float
    underchallenge_rpe: float


@dataclass(frozen=True)
class PolicyApproval:
    """Content binding supplied by a future trusted review boundary, not consent.

    C1 cannot authenticate a reviewer and cannot activate even approved inputs.
    """
    policy_hash: str
    reviewer_reference: str
    decision_reference: str


@dataclass(frozen=True)
class SciencePolicy:
    version: str
    status: Literal["provisional", "approved", "disabled"]
    goal: str
    training_status: str
    doses: tuple[ActionDose, ...]
    warmup_seconds: DurationRange
    transition_seconds: DurationRange
    margin_seconds: DurationRange
    minimum_gap_days: int
    calibration: CalibrationPolicy
    sources: tuple[SourceRef, ...]
    approval: PolicyApproval | None


@dataclass(frozen=True)
class DecisionTrace:
    schema_version: str
    owner: str
    rules_hash: str
    input_hash: str
    profile_hash: str
    catalog_hash: str
    policy_hash: str
    context_hash: str
    evidence_hash: str
    sources: tuple[SourceRef, ...]
    facts: tuple[str, ...]


@dataclass(frozen=True)
class RejectedCandidate:
    variant_id: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Selection:
    group: str
    selected_variant_id: str | None
    eligible_variants: tuple[str, ...]
    rejected: tuple[RejectedCandidate, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PlannedExercise:
    exercise: Exercise
    sets: int
    reps_min: int
    reps_max: int
    effort_kind: str
    effort_min: float
    effort_max: float
    rest_seconds: DurationRange
    reasons: tuple[str, ...]
    calibration: CalibrationDecision | None = None


@dataclass(frozen=True)
class TimeBudget:
    warmup_seconds: DurationRange
    work_seconds: DurationRange
    rest_seconds: DurationRange
    setup_seconds: DurationRange
    transition_seconds: DurationRange
    margin_seconds: DurationRange
    total_seconds: DurationRange
    status: str


@dataclass(frozen=True)
class DraftSession:
    session_id: str
    local_date: date
    emphasis: str
    exercises: tuple[PlannedExercise, ...]
    duration: TimeBudget


@dataclass(frozen=True)
class ExposureLedgerRow:
    session_id: str
    variant_id: str
    region: str
    involvement: Literal["primary", "secondary", "unknown"]
    sets: int
    evidence_kind: Literal["planned"] = "planned"


@dataclass(frozen=True)
class PlanPreview:
    version: str
    status: str
    policy_status: str
    sessions: tuple[DraftSession, ...]
    selections: tuple[Selection, ...]
    exposure_ledger: tuple[ExposureLedgerRow, ...]
    reasons: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    trace: DecisionTrace
    prescriptive: bool = False
    can_activate: bool = False


@dataclass(frozen=True)
class ExposureTarget:
    reps_min: int
    reps_max: int
    effort_kind: str
    effort_min: float
    effort_max: float


@dataclass(frozen=True)
class CompletedSet:
    record_id: str
    logical_set_id: str
    set_index: int
    revision: int
    state: Literal["completed", "incomplete", "voided"]
    set_kind: str
    parent_set_id: str | None
    actual_load: float | None
    performed_reps: int | None
    effort_kind: str | None
    actual_effort: float | None
    technique: Literal["acceptable", "poor", "unknown"]
    pain: bool | None
    load_identity: LoadIdentity | None
    planned_load: float | None = None


@dataclass(frozen=True)
class CompletedExposure:
    version: str
    workout_occurrence_id: str
    exercise_occurrence_id: str
    performed_on: date
    identity: LoadIdentity
    target: ExposureTarget
    required_set_indices: tuple[int, ...]
    finalized: bool
    records: tuple[CompletedSet, ...]
    provenance_reference: str


@dataclass(frozen=True)
class StrengthReport:
    report_id: str
    kind: Literal["1rm", "e1rm"]
    identity: LoadIdentity
    observed_on: date
    load: float
    credible: bool
    provenance_reference: str
    method_reference: str | None


@dataclass(frozen=True)
class EvidenceAssessment:
    workout_occurrence_id: str
    exercise_occurrence_id: str
    comparable: bool
    effective_records: tuple[CompletedSet, ...]
    excluded_ids: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CalibrationDecision:
    version: str
    policy_status: Literal["approved", "not_approved"]
    status: Literal["known_working_load", "requires_calibration", "insufficient_history", "unsupported_variant", "policy_not_approved", "invalid_input"]
    working_load: float | None
    known_baseline: float | None
    unit: str
    basis: str
    origin: str
    possibly_underchallenging: bool
    attainable_next_load: float | None
    evidence_ids: tuple[str, ...]
    excluded_ids: tuple[str, ...]
    completed_sets: int
    comparison_key: str
    evidence_hash: str
    policy_hash: str
    reasons: tuple[str, ...]
    next_steps: tuple[str, ...]
    strength_information: tuple[StrengthReport, ...]
    assessments: tuple[EvidenceAssessment, ...]
    prescriptive: bool = False
