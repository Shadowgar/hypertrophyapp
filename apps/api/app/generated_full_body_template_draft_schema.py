from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ConstructibilityStatus = Literal["ready", "insufficient"]


class ConstructorTraceRef(BaseModel):
    doctrine_rule_ids: list[str] = Field(default_factory=list)
    policy_ids: list[str] = Field(default_factory=list)
    exercise_ids: list[str] = Field(default_factory=list)
    system_default_ids: list[str] = Field(default_factory=list)


class ConstructibilityIssue(BaseModel):
    issue_id: str = Field(min_length=1)
    issue_type: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    movement_pattern: str | None = None
    slot_role: str | None = None
    trace: ConstructorTraceRef


class GeneratedExerciseDraft(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    movement_pattern: str = Field(min_length=1)
    slot_role: str = Field(min_length=1)
    primary_muscles: list[str] = Field(default_factory=list)
    equipment_tags: list[str] = Field(default_factory=list)
    sets: int = Field(ge=1)
    rep_range: list[int] = Field(default_factory=list)
    start_weight: float = Field(ge=0)
    substitution_candidates: list[str] = Field(default_factory=list)
    field_trace: dict[str, ConstructorTraceRef] = Field(default_factory=dict)


class GeneratedSessionDraft(BaseModel):
    session_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    day_role: str = Field(min_length=1)
    movement_pattern_targets: list[str] = Field(default_factory=list)
    exercises: list[GeneratedExerciseDraft] = Field(default_factory=list)
    field_trace: dict[str, ConstructorTraceRef] = Field(default_factory=dict)


class GeneratedFullBodyTemplateDraft(BaseModel):
    template_draft_id: str = Field(min_length=1)
    target_split: Literal["full_body"] = "full_body"
    assessment_id: str = Field(min_length=1)
    blueprint_input_id: str = Field(min_length=1)
    doctrine_bundle_id: str = Field(min_length=1)
    policy_bundle_id: str = Field(min_length=1)
    exercise_library_bundle_id: str = Field(min_length=1)
    constructibility_status: ConstructibilityStatus
    sessions: list[GeneratedSessionDraft] = Field(default_factory=list)
    insufficiencies: list[ConstructibilityIssue] = Field(default_factory=list)
    field_trace: dict[str, ConstructorTraceRef] = Field(default_factory=dict)
    system_default_ids_used: list[str] = Field(default_factory=list)
