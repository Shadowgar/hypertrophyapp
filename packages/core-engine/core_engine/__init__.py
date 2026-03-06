from .warmups import compute_warmups
from .progression import recommend_working_weight, update_exercise_state_after_workout
from .equipment import infer_equipment_tags_from_name, resolve_equipment_tags
from .scheduler import generate_week_plan
from .intelligence import (
    evaluate_schedule_adaptation,
    recommend_phase_transition,
    recommend_progression_action,
    recommend_specialization_adjustments,
    summarize_program_media_and_warmups,
)
from .onboarding_adaptation import adapt_onboarding_frequency

__all__ = [
    "compute_warmups",
    "recommend_working_weight",
    "update_exercise_state_after_workout",
    "infer_equipment_tags_from_name",
    "resolve_equipment_tags",
    "generate_week_plan",
    "evaluate_schedule_adaptation",
    "recommend_phase_transition",
    "recommend_progression_action",
    "recommend_specialization_adjustments",
    "summarize_program_media_and_warmups",
    "adapt_onboarding_frequency",
]
