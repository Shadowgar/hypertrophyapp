from pydantic import BaseModel, Field, field_validator, model_validator
from .adaptive_schema import AuthoredPrescription, SourceRelationship
from core_engine.authored_prescription import uniform_rep_range


class VideoMetadata(BaseModel):
    youtube_url: str | None = None


class CanonicalExercise(BaseModel):
    id: str
    primary_exercise_id: str | None = None
    name: str
    sets: int = Field(ge=1)
    rep_range: list[int] | None
    authored_prescription: AuthoredPrescription | None = None
    source_lineage: dict | None = None
    source_relationships: list[SourceRelationship] = Field(default_factory=list)
    start_weight: float = Field(ge=0)
    priority: str = "standard"
    slot_role: str | None = None
    movement_pattern: str | None = None
    primary_muscles: list[str] = []
    equipment_tags: list[str] = []
    source_approved_alternatives: list[dict] = []
    substitution_candidates: list[str] = []
    substitution_metadata: dict[str, dict[str, object]] = {}
    load_semantics: str | None = None
    execution_modifiers: dict | None = None
    last_set_intensity_technique: str | None = None
    warm_up_sets: str | None = None
    working_sets: str | None = None
    reps: str | None = None
    early_set_rpe: str | None = None
    last_set_rpe: str | None = None
    rest: str | None = None
    tracking_set_1: str | None = None
    tracking_set_2: str | None = None
    tracking_set_3: str | None = None
    tracking_set_4: str | None = None
    substitution_option_1: str | None = None
    substitution_option_2: str | None = None
    demo_url: str | None = None
    video_url: str | None = None
    notes: str | None = None
    video: VideoMetadata | None = None

    @model_validator(mode="after")
    def validate_numeric_compatibility(self):
        if self.authored_prescription is not None:
            if self.rep_range != uniform_rep_range(self.authored_prescription.model_dump()):
                raise ValueError("Numeric compatibility must match every authored set")
            if self.sets != len(self.authored_prescription.sets):
                raise ValueError("Working-set count must match authored prescription")
        elif self.rep_range is None:
            raise ValueError("Legacy/generated exercise requires numeric rep range")
        return self

    @field_validator("rep_range")
    @classmethod
    def validate_rep_range(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        if len(value) != 2:
            raise ValueError("rep_range must contain exactly 2 integers")
        if value[0] > value[1]:
            raise ValueError("rep_range min must be <= max")
        return value


class CanonicalSession(BaseModel):
    name: str
    day_role: str | None = None
    day_offset: int | None = Field(default=None, ge=0, le=6)
    exercises: list[CanonicalExercise]


class CanonicalAuthoredWeek(BaseModel):
    week_index: int = Field(ge=1)
    week_role: str | None = None
    sessions: list[CanonicalSession]


class DeloadConfig(BaseModel):
    trigger_weeks: int = Field(ge=1)
    set_reduction_pct: int = Field(ge=0, le=100)
    load_reduction_pct: int = Field(ge=0, le=100)


class ProgressionConfig(BaseModel):
    mode: str
    increment_kg: float = Field(gt=0)


class CanonicalProgramTemplate(BaseModel):
    id: str
    version: str
    split: str
    days_supported: list[int]
    deload: DeloadConfig
    progression: ProgressionConfig
    sessions: list[CanonicalSession]
    authored_weeks: list[CanonicalAuthoredWeek] = []

    @field_validator("days_supported")
    @classmethod
    def validate_days_supported(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("days_supported cannot be empty")
        if any(day < 2 or day > 7 for day in value):
            raise ValueError("days_supported must be between 2 and 7")
        return value
