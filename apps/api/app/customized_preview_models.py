"""Strict nonproduction preview contract; no client policy/admission material."""
from dataclasses import dataclass
from datetime import date
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator

from core_engine.customized.admission import TrustedPolicyRegistry
from core_engine.customized.models import ExerciseCatalog, CompletedExposure, StrengthReport
from core_engine.customized.pilot_models import PilotStandard, PilotDesign


class StrictPreviewModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class OmissionRequest(StrictPreviewModel):
    kind: Literal["action", "region", "dose"]
    name: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=240)
    confirmation_reference: str = Field(min_length=1, max_length=96)


class PreviewRequest(StrictPreviewModel):
    audience: Literal["synthetic_review_preview", "approved_prescription", "customized_program"]
    bundle_id: str = Field(min_length=1, max_length=96)
    mode: Literal["customized", "authored", "manual", "auto"]
    consent: StrictBool
    consent_reference: str = Field(min_length=1, max_length=96)
    goal: str = Field(min_length=1, max_length=32)
    training_context: Literal["new", "returning", "current", "unknown"]
    population: str = Field(min_length=1, max_length=64)
    selected_dates: tuple[date, ...] = Field(default=(), max_length=3)
    timezone: str = Field(min_length=1, max_length=64)
    cap_minutes: StrictInt = Field(ge=1, le=240)
    cap_kind: Literal["hard", "flexible"]
    equipment: tuple[str, ...] = Field(default=(), max_length=32)
    skill: Literal["basic", "intermediate", "advanced"] | None = None
    restrictions: tuple[str, ...] | None = Field(default=None, max_length=16)
    preferred_variants: tuple[str, ...] = Field(default=(), max_length=32)
    excluded_variants: tuple[str, ...] = Field(default=(), max_length=32)
    preferred_stability: Literal["supported", "unsupported"] | None = None
    omissions: tuple[OmissionRequest, ...] = Field(default=(), max_length=39)
    weakpoints: tuple[str, ...] = Field(default=(), max_length=8)
    recovery: str | None = Field(default=None, max_length=32)

    @field_validator("selected_dates", mode="before")
    @classmethod
    def actual_local_dates(cls, values):
        if not isinstance(values,(tuple,list)) or any(type(v) is not date and
            (not isinstance(v,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",v)) for v in values):
            raise ValueError("Use date-only local values")
        return values

    @field_validator("equipment","restrictions","preferred_variants","excluded_variants","weakpoints")
    @classmethod
    def clean_explicit_tags(cls, values):
        if values is None:
            return None
        if any(not v.strip() or len(v)>96 for v in values):
            raise ValueError("Explicit nonempty bounded tags required")
        return tuple(dict.fromkeys(v.strip() for v in values))


@dataclass(frozen=True)
class PreviewPrincipal:
    subject: str
    scopes: tuple[str, ...]


@dataclass(frozen=True)
class ProgramBundle:
    bundle_id: str
    standard: PilotStandard
    catalog: ExerciseCatalog
    design: PilotDesign
    exposures: tuple[CompletedExposure, ...] = ()
    strength_reports: tuple[StrengthReport, ...] = ()
    display_name: str = "Original candidate"


# Historical C3A import compatibility; runtime hosts supply their own library.
SyntheticReviewBundle = ProgramBundle


@dataclass(frozen=True)
class PreviewServer:
    enabled: bool = False
    environment: Literal["production", "staging", "test", "application"] = "production"
    synthetic_enabled: bool = False
    allowed_subjects: tuple[str, ...] = ()
    bundles: tuple[ProgramBundle, ...] = ()
    registry: TrustedPolicyRegistry = TrustedPolicyRegistry()


class ExercisePreview(StrictPreviewModel):
    variant_id: str
    name: str
    sets: int
    reps_min: int
    reps_max: int
    target_scale: str
    target_min: float
    target_max: float
    observed_effort: tuple[float, ...] = ()
    rest_min_seconds: float
    rest_max_seconds: float
    working_load: float | None
    load_unit: str
    load_basis: str
    calibration_status: str
    calibration_reasons: tuple[str, ...]


class SessionPreview(StrictPreviewModel):
    local_date: date
    design_label: str
    minimum_minutes: float
    maximum_minutes: float
    cap_status: str
    exercises: tuple[ExercisePreview, ...]


class RegionPreview(StrictPreviewModel):
    region: str
    primary_sets: int
    secondary_sets: int
    unknown_sets: int


class PreviewResponse(StrictPreviewModel):
    schema_version: Literal["customized-preview-c3a-v1"] = "customized-preview-c3a-v1"
    audience: Literal["synthetic_review_preview", "approved_prescription", "customized_program"]
    status: str
    message: str
    candidate_name: str = "Policy unavailable"
    can_activate: Literal[False] = False
    prescriptive: Literal[False] = False
    effectiveness: Literal["not_established"] = "not_established"
    coverage_meaning: str = "Nominal declared action/region and candidate dose coverage; not hypertrophy optimality."
    coverage_status: str | None = None
    timezone: str | None = None
    cap_minutes: int | None = None
    cap_kind: str | None = None
    sessions: tuple[SessionPreview, ...] = ()
    regions: tuple[RegionPreview, ...] = ()
    missing_actions: tuple[str, ...] = ()
    missing_regions: tuple[str, ...] = ()
    dose_conflicts: tuple[str, ...] = ()
    accepted_omissions: tuple[OmissionRequest, ...] = ()
    reasons: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()
    tradeoffs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    active_fields: tuple[str, ...] = ()
    trace_only_fields: tuple[str, ...] = ()
    trace: dict[str, str | tuple[str, ...]] = Field(default_factory=dict)
