from pydantic import BaseModel, Field, field_validator


class VideoMetadata(BaseModel):
    youtube_url: str | None = None


class CanonicalExercise(BaseModel):
    id: str
    primary_exercise_id: str | None = None
    name: str
    sets: int = Field(ge=1)
    rep_range: list[int]
    start_weight: float = Field(ge=0)
    priority: str = "standard"
    slot_role: str | None = None
    movement_pattern: str | None = None
    primary_muscles: list[str] = []
    equipment_tags: list[str] = []
    substitution_candidates: list[str] = []
    substitution_metadata: dict[str, dict[str, object]] = {}
    notes: str | None = None
    video: VideoMetadata | None = None

    @field_validator("rep_range")
    @classmethod
    def validate_rep_range(cls, value: list[int]) -> list[int]:
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
