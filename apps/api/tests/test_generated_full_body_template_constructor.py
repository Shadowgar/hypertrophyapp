from inspect import signature
import json
from pathlib import Path
import sys
from copy import deepcopy


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
CORE_ENGINE_ROOT = Path(__file__).resolve().parents[3] / "packages" / "core-engine"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
if str(CORE_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ENGINE_ROOT))

from app.generated_assessment_builder import build_user_assessment
from app.generated_assessment_schema import ProfileAssessmentInput
from app.generated_full_body_blueprint_builder import BLUEPRINT_SYSTEM_DEFAULTS, build_generated_full_body_blueprint_input
from app import generated_full_body_runtime_adapter as runtime_adapter
from app.generated_full_body_template_constructor import CONSTRUCTOR_SYSTEM_DEFAULTS, build_generated_full_body_template_draft
from app.generated_full_body_template_draft_schema import (
    GeneratedExerciseDraft,
    GeneratedFullBodyTemplateDraft,
    GeneratedSessionDraft,
)
from app.knowledge_loader import load_doctrine_bundle, load_exercise_library, load_policy_bundle
from app.program_loader import load_program_template
from core_engine.scheduler import generate_week_plan
from tests.fixtures.generated_full_body_archetypes import get_generated_full_body_archetypes


REQUIRED_CONSTRUCTOR_RULE_IDS = {
    "full_body_session_topology_by_session_count_v1",
    "full_body_day_role_sequence_by_session_count_v1",
    "full_body_movement_pattern_distribution_v1",
    "full_body_session_fill_target_by_volume_tier_v1",
    "full_body_initial_sets_by_slot_role_and_volume_tier_v1",
    "full_body_set_adjustments_by_user_state_v1",
    "full_body_day_role_prescription_emphasis_v1",
    "full_body_candidate_scoring_v1",
    "full_body_optional_fill_pattern_priority_by_complexity_ceiling_v1",
    "full_body_slot_role_sequence_v1",
    "full_body_exercise_reuse_limits_v1",
    "full_body_weak_point_slot_insertion_v1",
    "full_body_initial_rep_ranges_by_slot_role_and_pattern_v1",
    "full_body_rep_adjustments_by_exercise_demand_v1",
    "full_body_start_weight_initialization_v1",
}

WEEKLY_BALANCE_CATEGORY_TO_PATTERNS = {
    "horizontal_push": {"horizontal_press"},
    "vertical_push": {"vertical_press"},
    "horizontal_pull": {"horizontal_pull"},
    "vertical_pull": {"vertical_pull"},
    "knee_dominant_lower": {"squat", "knee_extension"},
    "hip_dominant_lower": {"hinge", "leg_curl"},
    "core": {"core"},
}


def _collect_doctrine_ids(draft) -> set[str]:
    ids = set()
    for trace in draft.field_trace.values():
        ids.update(trace.doctrine_rule_ids)
    for issue in draft.insufficiencies:
        ids.update(issue.trace.doctrine_rule_ids)
    for session in draft.sessions:
        for trace in session.field_trace.values():
            ids.update(trace.doctrine_rule_ids)
        for exercise in session.exercises:
            for trace in exercise.field_trace.values():
                ids.update(trace.doctrine_rule_ids)
    return ids


def _collect_policy_ids(draft) -> set[str]:
    ids = set()
    for trace in draft.field_trace.values():
        ids.update(trace.policy_ids)
    for issue in draft.insufficiencies:
        ids.update(issue.trace.policy_ids)
    for session in draft.sessions:
        for trace in session.field_trace.values():
            ids.update(trace.policy_ids)
        for exercise in session.exercises:
            for trace in exercise.field_trace.values():
                ids.update(trace.policy_ids)
    return ids


def _policy_ids(bundle) -> set[str]:
    return (
        {item.constraint_id for item in bundle.hard_constraints}
        | {item.preference_id for item in bundle.soft_preferences}
        | {
            bundle.constraint_resolution_policy.policy_id,
            bundle.minimum_viable_program_policy.policy_id,
            bundle.anti_overadaptation_policy.policy_id,
            bundle.data_sufficiency_policy.policy_id,
        }
    )


def _collect_system_default_ids(draft) -> set[str]:
    ids = set()
    for trace in draft.field_trace.values():
        ids.update(trace.system_default_ids)
    for issue in draft.insufficiencies:
        ids.update(issue.trace.system_default_ids)
    for session in draft.sessions:
        for trace in session.field_trace.values():
            ids.update(trace.system_default_ids)
        for exercise in session.exercises:
            for trace in exercise.field_trace.values():
                ids.update(trace.system_default_ids)
    return ids


def _assert_trace_map(trace_map, expected_fields: set[str], label: str) -> None:
    assert set(trace_map) == expected_fields, label
    for field_name, trace in trace_map.items():
        assert (
            trace.doctrine_rule_ids
            or trace.policy_ids
            or trace.exercise_ids
            or trace.system_default_ids
        ), f"{label}: missing trace payload for {field_name}"


def _build_layers(archetype_fixture: dict):
    compiled_dir = REPO_ROOT / "knowledge" / "compiled"
    doctrine_bundle = load_doctrine_bundle("multi_source_hypertrophy_v1", compiled_dir)
    policy_bundle = load_policy_bundle("system_coaching_policy_v1", compiled_dir)
    exercise_library = load_exercise_library(compiled_dir)
    assessment = build_user_assessment(
        profile_input=ProfileAssessmentInput.model_validate(archetype_fixture["profile_input"]),
        training_state=archetype_fixture["training_state"],
        doctrine_bundle=doctrine_bundle,
        policy_bundle=policy_bundle,
    )
    blueprint = build_generated_full_body_blueprint_input(
        assessment=assessment,
        doctrine_bundle=doctrine_bundle,
        policy_bundle=policy_bundle,
        exercise_library=exercise_library,
    )
    draft = build_generated_full_body_template_draft(
        assessment=assessment,
        blueprint_input=blueprint,
        doctrine_bundle=doctrine_bundle,
        policy_bundle=policy_bundle,
        exercise_library=exercise_library,
    )
    return doctrine_bundle, policy_bundle, exercise_library, assessment, blueprint, draft


def _normal_three_day_fixture_from_low_time() -> dict:
    fixture = deepcopy(get_generated_full_body_archetypes()["low_time_full_body"])
    fixture["profile_input"]["split_preference"] = None
    fixture["profile_input"]["session_time_budget_minutes"] = 60
    fixture["profile_input"]["near_failure_tolerance"] = "moderate"
    fixture["training_state"]["constraint_state"]["split_preference"] = None
    fixture["training_state"]["constraint_state"]["session_time_budget_minutes"] = 60
    fixture["training_state"]["constraint_state"]["near_failure_tolerance"] = "moderate"
    fixture["training_state"]["adherence_state"]["latest_adherence_score"] = 4
    fixture["training_state"]["adherence_state"]["rolling_average_score"] = 4.0
    fixture["training_state"]["adherence_state"]["missed_session_count"] = 0
    fixture["training_state"]["coaching_state"]["adherence"]["latest_adherence_score"] = 4
    fixture["training_state"]["coaching_state"]["adherence"]["rolling_average_score"] = 4.0
    fixture["training_state"]["coaching_state"]["adherence"]["missed_session_count"] = 0
    return fixture


def _arm_delt_weak_point_normal_fixture() -> dict:
    fixture = _normal_three_day_fixture_from_low_time()
    fixture["profile_input"]["weak_areas"] = ["biceps", "side_delts"]
    fixture["training_state"]["constraint_state"]["weak_areas"] = ["biceps", "side_delts"]
    return fixture


def _covered_balance_categories(draft: GeneratedFullBodyTemplateDraft) -> set[str]:
    patterns = {
        str(exercise.movement_pattern)
        for session in draft.sessions
        for exercise in session.exercises
    }
    covered: set[str] = set()
    for category, category_patterns in WEEKLY_BALANCE_CATEGORY_TO_PATTERNS.items():
        if patterns.intersection(category_patterns):
            covered.add(category)
    return covered


def _required_balance_categories(blueprint) -> set[str]:
    required: set[str] = set()
    for category, category_patterns in WEEKLY_BALANCE_CATEGORY_TO_PATTERNS.items():
        if any(blueprint.candidate_exercise_ids_by_pattern.get(pattern) for pattern in category_patterns):
            required.add(category)
    return required


def _record_by_id(exercise_library):
    return {record.exercise_id: record.model_dump(mode="json") for record in exercise_library.records}


def _session_high_fatigue_count(session: GeneratedSessionDraft, record_by_id: dict[str, dict]) -> int:
    return sum(
        1
        for exercise in session.exercises
        if str((record_by_id.get(exercise.id) or {}).get("fatigue_cost") or "") == "high"
    )


def _session_total_sets(session: GeneratedSessionDraft) -> int:
    return sum(int(exercise.sets) for exercise in session.exercises)


def _major_group_weekly_volume(draft: GeneratedFullBodyTemplateDraft) -> dict[str, int]:
    alias = {
        "chest": "chest",
        "lats": "back",
        "upper_back": "back",
        "mid_back": "back",
        "quads": "quads",
        "hamstrings": "hamstrings",
        "front_delts": "delts",
        "side_delts": "delts",
        "rear_delts": "delts",
        "biceps": "arms",
        "triceps": "arms",
        "abs": "core",
    }
    totals = {"chest": 0, "back": 0, "quads": 0, "hamstrings": 0, "delts": 0, "arms": 0, "core": 0}
    for session in draft.sessions:
        for exercise in session.exercises:
            for muscle in exercise.primary_muscles:
                group = alias.get(muscle)
                if group is not None:
                    totals[group] += int(exercise.sets)
    return totals


def _muscle_contribution_volume(draft: GeneratedFullBodyTemplateDraft, record_by_id: dict[str, dict]) -> dict[str, int]:
    alias = {
        "chest": "chest",
        "lats": "back",
        "upper_back": "back",
        "mid_back": "back",
        "quads": "quads",
        "hamstrings": "hamstrings",
        "front_delts": "delts",
        "side_delts": "delts",
        "rear_delts": "delts",
        "biceps": "arms",
        "triceps": "arms",
        "abs": "core",
    }
    totals = {"chest": 0, "back": 0, "quads": 0, "hamstrings": 0, "delts": 0, "arms": 0, "core": 0}
    for session in draft.sessions:
        for exercise in session.exercises:
            record = record_by_id.get(exercise.id) or {}
            for muscle in record.get("primary_muscles") or []:
                group = alias.get(str(muscle))
                if group is not None:
                    totals[group] += int(exercise.sets)
            for muscle in record.get("secondary_muscles") or []:
                group = alias.get(str(muscle))
                if group is not None:
                    totals[group] += max(1, int(exercise.sets) // 2)
    return totals


def _build_week_payload_from_draft(*, fixture: dict, draft: GeneratedFullBodyTemplateDraft) -> dict:
    selected_template = load_program_template("full_body_v1")
    adapted_template = runtime_adapter._adapt_draft_to_program_template(
        selected_template_id="full_body_v1",
        selected_template=selected_template,
        draft=draft,
    )
    profile_input = fixture["profile_input"]
    return generate_week_plan(
        user_profile={"name": "Generated Constructor Visible Volume"},
        days_available=int(profile_input.get("days_available") or 3),
        split_preference="full_body",
        program_template=adapted_template,
        history=[],
        phase="hypertrophy",
        available_equipment=list(profile_input.get("equipment_profile") or []),
        session_time_budget_minutes=int(profile_input.get("session_time_budget_minutes") or 60),
        weak_areas=list(profile_input.get("weak_areas") or []),
        progression_state_per_exercise=[],
    )


def _visible_grouped_volume_from_week_payload(payload: dict) -> dict[str, int]:
    weekly_volume = payload.get("weekly_volume_by_muscle") or {}
    grouped = {
        "chest": int(weekly_volume.get("chest") or 0),
        "back": int(weekly_volume.get("back") or 0),
        "quads": int(weekly_volume.get("quads") or 0),
        "hamstrings": int(weekly_volume.get("hamstrings") or 0),
        "delts": int(weekly_volume.get("shoulders") or 0),
        "arms": int(weekly_volume.get("biceps") or 0) + int(weekly_volume.get("triceps") or 0),
        "core": 0,
    }
    for session in payload.get("sessions") or []:
        for exercise in session.get("exercises") or []:
            muscles = [str(item) for item in (exercise.get("primary_muscles") or [])]
            if "abs" in muscles or "core" in muscles:
                grouped["core"] += int(exercise.get("sets") or 0)
    return grouped


def test_generated_full_body_template_constructor_is_deterministic_traceable_and_original() -> None:
    compiled_dir = REPO_ROOT / "knowledge" / "compiled"
    doctrine_bundle = load_doctrine_bundle("multi_source_hypertrophy_v1", compiled_dir)
    policy_bundle = load_policy_bundle("system_coaching_policy_v1", compiled_dir)
    exercise_library = load_exercise_library(compiled_dir)

    valid_doctrine_rule_ids = {rule.rule_id for rules in doctrine_bundle.rules_by_module.values() for rule in rules}
    valid_policy_ids = _policy_ids(policy_bundle)
    valid_exercise_ids = {record.exercise_id for record in exercise_library.records}
    rules = {rule.rule_id: rule for rules in doctrine_bundle.rules_by_module.values() for rule in rules}

    sig = signature(build_generated_full_body_template_draft)
    assert list(sig.parameters) == [
        "assessment",
        "blueprint_input",
        "doctrine_bundle",
        "policy_bundle",
        "exercise_library",
    ]

    for archetype_name, fixture in get_generated_full_body_archetypes().items():
        _, _, _, assessment, blueprint, first = _build_layers(fixture)
        _, _, _, _, _, second = _build_layers(fixture)

        assert first.model_dump(mode="json") == second.model_dump(mode="json"), archetype_name
        assert first.constructibility_status == fixture["expected_template"]["constructibility_status"], archetype_name
        assert len(first.sessions) == fixture["expected_template"]["session_count"], archetype_name
        assert [len(session.exercises) for session in first.sessions] == fixture["expected_template"]["expected_session_exercise_counts"], archetype_name
        if "expected_selected_exercise_ids" in fixture["expected_template"]:
            selected_ids = {exercise.id for session in first.sessions for exercise in session.exercises}
            assert set(fixture["expected_template"]["expected_selected_exercise_ids"]) <= selected_ids, archetype_name

        _assert_trace_map(first.field_trace, set(GeneratedFullBodyTemplateDraft.model_fields), archetype_name)

        expected_day_roles = rules["full_body_day_role_sequence_by_session_count_v1"].payload["day_roles_by_session_count"][
            str(blueprint.session_count)
        ]
        expected_distribution = rules["full_body_movement_pattern_distribution_v1"].payload["distribution_by_session_count"][
            str(blueprint.session_count)
        ]
        assert [session.day_role for session in first.sessions] == expected_day_roles, archetype_name
        assert [session.movement_pattern_targets for session in first.sessions] == [
            item["movement_patterns"] for item in expected_distribution
        ], archetype_name

        for index, session in enumerate(first.sessions, start=1):
            assert session.session_id == f"generated_full_body_session_{index}", archetype_name
            assert session.title == f"Generated Full Body {index}", archetype_name
            assert session.day_role == f"generated_full_body_{index}", archetype_name
            _assert_trace_map(session.field_trace, set(GeneratedSessionDraft.model_fields), f"{archetype_name}:session:{index}")
            assert session.optional_fill_trace is not None, archetype_name
            assert session.optional_fill_trace.stop_reason in {
                "target_reached",
                "candidate_pool_exhausted",
                "score_floor_not_met",
            }, archetype_name
            assert len({exercise.id for exercise in session.exercises}) == len(session.exercises), archetype_name
            for exercise in session.exercises:
                assert exercise.id in valid_exercise_ids, archetype_name
                assert exercise.sets >= 1, archetype_name
                assert len(exercise.rep_range) == 2, archetype_name
                assert exercise.rep_range[0] <= exercise.rep_range[1], archetype_name
                assert exercise.field_trace["sets"].doctrine_rule_ids == [
                    "full_body_initial_sets_by_slot_role_and_volume_tier_v1",
                    "full_body_set_adjustments_by_user_state_v1",
                    "full_body_day_role_prescription_emphasis_v1",
                ], archetype_name
                assert exercise.field_trace["rep_range"].doctrine_rule_ids == [
                    "full_body_initial_rep_ranges_by_slot_role_and_pattern_v1",
                    "full_body_day_role_prescription_emphasis_v1",
                    "full_body_rep_adjustments_by_exercise_demand_v1",
                ], archetype_name
                if exercise.id in fixture["expected_template"].get("expected_start_weight_matches", {}):
                    assert exercise.start_weight == fixture["expected_template"]["expected_start_weight_matches"][exercise.id], archetype_name
                    assert exercise.field_trace["start_weight"].system_default_ids == [], archetype_name
                else:
                    assert exercise.field_trace["start_weight"].doctrine_rule_ids == [
                        "full_body_start_weight_initialization_v1"
                    ], archetype_name
                    assert exercise.field_trace["start_weight"].system_default_ids == [
                        "default_generated_start_weight_v1"
                    ], archetype_name
                assert exercise.substitution_candidates == [], archetype_name
                assert exercise.selection_trace.scoring_rule_id == "full_body_candidate_scoring_v1", archetype_name
                assert exercise.selection_trace.selection_mode in {
                    "required_slot",
                    "weak_point_slot",
                    "optional_fill",
                }, archetype_name
                assert exercise.selection_trace.top_candidates, archetype_name
                _assert_trace_map(
                    exercise.field_trace,
                    set(GeneratedExerciseDraft.model_fields),
                    f"{archetype_name}:exercise:{exercise.id}",
                )

        assert _collect_doctrine_ids(first) <= valid_doctrine_rule_ids, archetype_name
        assert REQUIRED_CONSTRUCTOR_RULE_IDS <= _collect_doctrine_ids(first), archetype_name
        assert _collect_policy_ids(first) <= valid_policy_ids, archetype_name
        assert _collect_system_default_ids(first) <= (set(CONSTRUCTOR_SYSTEM_DEFAULTS) | set(BLUEPRINT_SYSTEM_DEFAULTS)), archetype_name
        assert set(first.system_default_ids_used) <= (set(CONSTRUCTOR_SYSTEM_DEFAULTS) | set(BLUEPRINT_SYSTEM_DEFAULTS)), archetype_name

        assert "do_not_replay_single_authored_layout" in _collect_policy_ids(first), archetype_name
        assert "do_not_replay_single_authored_layout" in first.field_trace["sessions"].policy_ids, archetype_name
        assert "minimum_viable_program_v1" in _collect_policy_ids(first), archetype_name

        serialized = json.dumps(first.model_dump(mode="json"), sort_keys=True)
        assert "week_template_id" not in serialized, archetype_name
        assert "program_id" not in serialized, archetype_name

        if fixture["expected_template"]["expects_insufficiency"]:
            assert first.insufficiencies, archetype_name
            assert first.constructibility_status == "insufficient", archetype_name
            assert any(issue.movement_pattern for issue in first.insufficiencies), archetype_name
            assert len({
                (issue.issue_type, issue.reason, issue.movement_pattern, issue.slot_role)
                for issue in first.insufficiencies
            }) == len(first.insufficiencies), archetype_name
        else:
            assert not first.insufficiencies, archetype_name
            assert all(session.exercises for session in first.sessions), archetype_name

        if archetype_name in {
            "novice_gym_full_body",
            "low_time_full_body",
            "low_recovery_full_body",
            "comeback_full_body",
        }:
            primary_set_signature = [
                max((exercise.sets for exercise in session.exercises if exercise.slot_role == "primary_compound"), default=0)
                for session in first.sessions
            ]
            compound_rep_signature = [
                min(
                    (
                        exercise.rep_range[0]
                        for exercise in session.exercises
                        if exercise.slot_role in {"primary_compound", "secondary_compound"}
                    ),
                    default=99,
                )
                for session in first.sessions
            ]
            assert len(set(primary_set_signature + compound_rep_signature)) > 1, archetype_name

        if archetype_name == "restricted_equipment_full_body":
            expected_patterns = {item.movement_pattern for item in blueprint.pattern_insufficiencies}
            actual_patterns = {item.movement_pattern for item in first.insufficiencies if item.movement_pattern}
            assert expected_patterns <= actual_patterns, archetype_name


def test_generated_week_outputs_preserve_required_movement_balance_categories() -> None:
    archetypes = get_generated_full_body_archetypes()
    for archetype_name in (
        "novice_gym_full_body",
        "low_time_full_body",
        "low_recovery_full_body",
        "inconsistent_schedule_full_body",
        "comeback_full_body",
    ):
        _, _, _, _, blueprint, draft = _build_layers(archetypes[archetype_name])
        covered = _covered_balance_categories(draft)
        required = _required_balance_categories(blueprint)
        missing = sorted(required - covered)
        assert not missing, f"{archetype_name}: missing categories={missing}"


def test_generated_week_outputs_keep_session_set_and_fatigue_distribution_within_band() -> None:
    archetypes = get_generated_full_body_archetypes()
    for archetype_name in (
        "novice_gym_full_body",
        "low_time_full_body",
        "low_recovery_full_body",
        "inconsistent_schedule_full_body",
        "comeback_full_body",
    ):
        _, _, exercise_library, _, _, draft = _build_layers(archetypes[archetype_name])
        record_by_id = _record_by_id(exercise_library)

        set_totals = [_session_total_sets(session) for session in draft.sessions]
        fatigue_high_counts = [_session_high_fatigue_count(session, record_by_id) for session in draft.sessions]

        assert max(set_totals) - min(set_totals) <= 4, f"{archetype_name}: set_totals={set_totals}"
        assert max(fatigue_high_counts) - min(fatigue_high_counts) <= 2, (
            f"{archetype_name}: high_fatigue_counts={fatigue_high_counts}"
        )


def test_generated_week_weak_point_bias_does_not_break_required_movement_balance() -> None:
    archetypes = get_generated_full_body_archetypes()
    _, _, _, assessment, blueprint, draft = _build_layers(archetypes["novice_gym_full_body"])
    weak_point_slots = [
        exercise
        for session in draft.sessions
        for exercise in session.exercises
        if exercise.selection_trace.selection_mode == "weak_point_slot"
    ]
    assert weak_point_slots
    weak_point_targets = {item.muscle_group for item in assessment.weak_point_priorities}
    assert any(set(exercise.primary_muscles).intersection(weak_point_targets) for exercise in weak_point_slots)

    covered = _covered_balance_categories(draft)
    required = _required_balance_categories(blueprint)
    missing = sorted(required - covered)
    assert not missing, f"weak_point_bias_coverage_break: missing={missing}"


def test_v23_generated_sessions_are_materially_fuller_under_normal_budgets() -> None:
    archetypes = get_generated_full_body_archetypes()
    for archetype_name in (
        "novice_gym_full_body",
        "low_time_full_body",
        "low_recovery_full_body",
        "inconsistent_schedule_full_body",
        "comeback_full_body",
    ):
        _, _, _, _, _, draft = _build_layers(archetypes[archetype_name])
        counts = [len(session.exercises) for session in draft.sessions]
        assert min(counts) >= 5, f"{archetype_name}: counts={counts}"


def test_v23_generated_weeks_cover_major_muscle_groups_with_meaningful_presence() -> None:
    major_groups = {
        "chest",
        "lats",
        "upper_back",
        "rear_delts",
        "front_delts",
        "quads",
        "glutes",
        "hamstrings",
        "biceps",
        "triceps",
        "abs",
    }
    archetypes = get_generated_full_body_archetypes()
    minimum_seen_by_archetype = {
        "novice_gym_full_body": 5,
        "low_time_full_body": 5,
        "four_day_full_body": 5,
    }
    for archetype_name in ("novice_gym_full_body", "low_time_full_body", "four_day_full_body"):
        _, _, _, _, _, draft = _build_layers(archetypes[archetype_name])
        seen = {
            muscle
            for session in draft.sessions
            for exercise in session.exercises
            for muscle in exercise.primary_muscles
            if muscle in major_groups
        }
        assert len(seen) >= minimum_seen_by_archetype[archetype_name], f"{archetype_name}: seen={sorted(seen)}"


def test_v23_accessory_and_isolation_fill_expands_sessions_without_breaking_balance() -> None:
    archetypes = get_generated_full_body_archetypes()
    _, _, _, _, blueprint, draft = _build_layers(archetypes["novice_gym_full_body"])
    accessory_like_patterns = {"curl", "triceps_extension", "lateral_raise", "knee_extension", "leg_curl", "core", "chest_fly"}
    accessory_count = sum(
        1
        for session in draft.sessions
        for exercise in session.exercises
        if exercise.slot_role in {"accessory", "weak_point"} or exercise.movement_pattern in accessory_like_patterns
    )
    assert accessory_count >= 4
    covered = _covered_balance_categories(draft)
    required = _required_balance_categories(blueprint)
    assert not (required - covered)


def test_v23_time_budget_scaling_reduces_density_without_reverting_to_skeletons() -> None:
    archetypes = get_generated_full_body_archetypes()
    _, _, _, _, _, low_time = _build_layers(archetypes["low_time_full_body"])
    _, _, _, _, _, novice = _build_layers(archetypes["novice_gym_full_body"])
    low_time_avg = sum(len(session.exercises) for session in low_time.sessions) / len(low_time.sessions)
    novice_avg = sum(len(session.exercises) for session in novice.sessions) / len(novice.sessions)
    assert low_time_avg < novice_avg
    assert low_time_avg >= 5


def test_v23_weak_point_bias_is_present_but_not_dominant() -> None:
    archetypes = get_generated_full_body_archetypes()
    _, _, _, assessment, _, draft = _build_layers(archetypes["novice_gym_full_body"])
    weak_targets = {item.muscle_group for item in assessment.weak_point_priorities}
    weak_hits = 0
    total = 0
    for session in draft.sessions:
        for exercise in session.exercises:
            total += 1
            if set(exercise.primary_muscles).intersection(weak_targets):
                weak_hits += 1
    assert weak_hits >= 1
    assert weak_hits / max(1, total) <= 0.75


def test_v24_role_based_set_assignment_is_not_flat_and_compounds_drive_volume() -> None:
    archetypes = get_generated_full_body_archetypes()
    _, _, _, _, _, draft = _build_layers(archetypes["novice_gym_full_body"])
    role_sets: dict[str, list[int]] = {}
    for session in draft.sessions:
        for exercise in session.exercises:
            role_sets.setdefault(exercise.slot_role, []).append(int(exercise.sets))
    assert role_sets["primary_compound"]
    assert role_sets["secondary_compound"]
    assert sum(role_sets["primary_compound"]) / len(role_sets["primary_compound"]) >= sum(role_sets["accessory"]) / len(
        role_sets["accessory"]
    )
    assert len({item for values in role_sets.values() for item in values}) >= 2


def test_v24_major_muscle_groups_receive_meaningful_weekly_volume() -> None:
    archetypes = get_generated_full_body_archetypes()
    for name in ("novice_gym_full_body", "low_time_full_body"):
        _, _, _, _, _, draft = _build_layers(archetypes[name])
        totals = _major_group_weekly_volume(draft)
        chest_floor = 6 if name == "novice_gym_full_body" else 3
        assert totals["chest"] >= chest_floor, f"{name}: {totals}"
        assert totals["back"] >= 6, f"{name}: {totals}"
        assert totals["quads"] >= 5, f"{name}: {totals}"
        assert totals["hamstrings"] >= 4, f"{name}: {totals}"
        assert totals["delts"] >= 1, f"{name}: {totals}"


def test_v24_compound_vs_isolation_mix_is_balanced() -> None:
    archetypes = get_generated_full_body_archetypes()
    _, _, _, _, _, draft = _build_layers(archetypes["novice_gym_full_body"])
    compound = 0
    isolation_or_accessory = 0
    for session in draft.sessions:
        for exercise in session.exercises:
            if exercise.slot_role in {"primary_compound", "secondary_compound"}:
                compound += 1
            if exercise.slot_role in {"accessory", "weak_point"}:
                isolation_or_accessory += 1
    assert compound >= 6
    assert isolation_or_accessory >= 4
    assert isolation_or_accessory < compound + isolation_or_accessory


def test_v24_session_flow_keeps_high_fatigue_earlier_on_average() -> None:
    archetypes = get_generated_full_body_archetypes()
    _, _, exercise_library, _, _, draft = _build_layers(archetypes["novice_gym_full_body"])
    record_by_id = _record_by_id(exercise_library)
    rank = {"high": 0, "moderate": 1, "low": 2, "": 1}
    violations = 0
    comparisons = 0
    for session in draft.sessions:
        sequence = [rank.get(str((record_by_id.get(exercise.id) or {}).get("fatigue_cost") or ""), 1) for exercise in session.exercises]
        for idx in range(len(sequence) - 1):
            comparisons += 1
            if sequence[idx] > sequence[idx + 1]:
                violations += 1
    assert violations <= max(3, comparisons // 4)


def test_v24_time_budget_scales_total_sets_not_only_exercise_count() -> None:
    archetypes = get_generated_full_body_archetypes()
    _, _, _, _, _, low_time = _build_layers(archetypes["low_time_full_body"])
    _, _, _, _, _, novice = _build_layers(archetypes["novice_gym_full_body"])
    low_time_sets = sum(_session_total_sets(session) for session in low_time.sessions)
    novice_sets = sum(_session_total_sets(session) for session in novice.sessions)
    assert novice_sets > low_time_sets


def test_v25_normal_three_day_density_is_not_underdosed_vs_authored_reference_range() -> None:
    generated_fixture = _normal_three_day_fixture_from_low_time()
    _, _, exercise_library, _, _, generated = _build_layers(generated_fixture)
    generated_record_by_id = _record_by_id(exercise_library)
    generated_exercise_slots = sum(len(session.exercises) for session in generated.sessions)
    generated_weekly_sets = sum(_session_total_sets(session) for session in generated.sessions)
    generated_volume = sum(_muscle_contribution_volume(generated, generated_record_by_id).values())

    authored_slot_totals: list[int] = []
    for template_id in ("pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"):
        authored_template = load_program_template(template_id)
        authored_week = generate_week_plan(
            user_profile={"name": "Reference"},
            days_available=3,
            split_preference="full_body",
            program_template=authored_template,
            history=[],
            phase="hypertrophy",
            available_equipment=["barbell", "bodyweight", "cable", "dumbbell", "machine", "bench"],
            session_time_budget_minutes=60,
            weak_areas=["chest", "lats"],
            progression_state_per_exercise=[],
        )
        authored_slot_totals.append(sum(len(session.get("exercises") or []) for session in authored_week["sessions"]))

    assert generated_exercise_slots >= int(min(authored_slot_totals) * 0.8)
    assert generated_weekly_sets >= 55
    assert generated_volume >= 68


def test_v25b_normal_three_day_major_volume_floors_are_satisfied() -> None:
    fixture = _normal_three_day_fixture_from_low_time()
    _, _, _, _, _, draft = _build_layers(fixture)
    payload = _build_week_payload_from_draft(fixture=fixture, draft=draft)
    totals = _visible_grouped_volume_from_week_payload(payload)
    assert totals["chest"] >= 10, totals
    assert totals["back"] >= 12, totals
    assert totals["quads"] >= 8, totals
    assert totals["hamstrings"] >= 8, totals
    assert totals["core"] >= 3, totals


def test_v25b_non_weak_point_normal_three_day_arm_and_delt_dominance_is_capped() -> None:
    fixture = _normal_three_day_fixture_from_low_time()
    _, _, _, _, _, draft = _build_layers(fixture)
    payload = _build_week_payload_from_draft(fixture=fixture, draft=draft)
    totals = _visible_grouped_volume_from_week_payload(payload)
    total_volume = sum(totals.values())
    assert totals["arms"] > 0, totals
    assert totals["delts"] > 0, totals
    assert totals["arms"] <= 28, totals
    assert totals["delts"] <= 18, totals
    assert (totals["arms"] + totals["delts"]) / max(1, total_volume) <= 0.48, totals


def test_v25b_core_is_non_zero_when_core_candidates_are_viable() -> None:
    fixture = _normal_three_day_fixture_from_low_time()
    _, _, _, _, blueprint, draft = _build_layers(fixture)
    assert blueprint.candidate_exercise_ids_by_pattern.get("core"), "expected viable core pool"
    payload = _build_week_payload_from_draft(fixture=fixture, draft=draft)
    totals = _visible_grouped_volume_from_week_payload(payload)
    assert totals["core"] > 0, totals


def test_v25b_weak_point_arm_delt_bias_is_preserved_but_bounded_and_major_floors_hold() -> None:
    baseline_fixture = _normal_three_day_fixture_from_low_time()
    weak_point_fixture = _arm_delt_weak_point_normal_fixture()
    _, _, _, _, _, baseline = _build_layers(baseline_fixture)
    _, _, _, _, _, weak_point = _build_layers(weak_point_fixture)

    baseline_payload = _build_week_payload_from_draft(fixture=baseline_fixture, draft=baseline)
    weak_point_payload = _build_week_payload_from_draft(fixture=weak_point_fixture, draft=weak_point)
    baseline_totals = _visible_grouped_volume_from_week_payload(baseline_payload)
    weak_point_totals = _visible_grouped_volume_from_week_payload(weak_point_payload)

    baseline_bias = baseline_totals["arms"] + baseline_totals["delts"]
    weak_point_bias = weak_point_totals["arms"] + weak_point_totals["delts"]
    assert weak_point_totals["arms"] > 0, (baseline_totals, weak_point_totals)
    assert weak_point_totals["delts"] > 0, (baseline_totals, weak_point_totals)
    assert weak_point_bias >= baseline_bias, (baseline_totals, weak_point_totals)

    assert weak_point_totals["arms"] <= 32, weak_point_totals
    assert weak_point_totals["delts"] <= 20, weak_point_totals
    assert weak_point_totals["chest"] >= 10, weak_point_totals
    assert weak_point_totals["back"] >= 12, weak_point_totals
    assert weak_point_totals["quads"] >= 8, weak_point_totals
    assert weak_point_totals["hamstrings"] >= 8, weak_point_totals
    assert weak_point_totals["core"] >= 3, weak_point_totals
    total_volume = sum(weak_point_totals.values())
    assert (weak_point_totals["arms"] + weak_point_totals["delts"]) / max(1, total_volume) <= 0.52, weak_point_totals


def test_v25c_arm_delt_restoration_does_not_rely_on_higher_high_fatigue_density() -> None:
    fixture = _normal_three_day_fixture_from_low_time()
    _, _, exercise_library, _, _, draft = _build_layers(fixture)
    record_by_id = _record_by_id(exercise_library)
    high_fatigue_counts = [_session_high_fatigue_count(session, record_by_id) for session in draft.sessions]
    assert max(high_fatigue_counts) <= 2, high_fatigue_counts
    assert sum(high_fatigue_counts) <= 5, high_fatigue_counts


def test_v25_low_time_three_day_is_smaller_than_normal_but_not_skeletal() -> None:
    archetypes = get_generated_full_body_archetypes()
    _, _, _, _, _, low_time = _build_layers(archetypes["low_time_full_body"])
    _, _, _, _, _, normal = _build_layers(_normal_three_day_fixture_from_low_time())

    low_time_slots = [len(session.exercises) for session in low_time.sessions]
    normal_slots = [len(session.exercises) for session in normal.sessions]
    low_time_weekly_sets = sum(_session_total_sets(session) for session in low_time.sessions)

    assert sum(low_time_slots) < sum(normal_slots)
    assert min(low_time_slots) >= 6
    assert low_time_weekly_sets >= 42


def test_v25_three_day_volume_scales_with_time_and_recovery() -> None:
    archetypes = get_generated_full_body_archetypes()
    _, _, _, _, _, high_time_normal = _build_layers(archetypes["novice_gym_full_body"])
    _, _, _, _, _, normal = _build_layers(_normal_three_day_fixture_from_low_time())
    _, _, _, _, _, low_recovery = _build_layers(archetypes["low_recovery_full_body"])

    high_time_sets = sum(_session_total_sets(session) for session in high_time_normal.sessions)
    normal_sets = sum(_session_total_sets(session) for session in normal.sessions)
    low_recovery_sets = sum(_session_total_sets(session) for session in low_recovery.sessions)

    assert high_time_sets > normal_sets > low_recovery_sets


def test_v25b_visible_grouped_low_time_and_low_recovery_major_floors_hold() -> None:
    archetypes = get_generated_full_body_archetypes()
    low_time_fixture = archetypes["low_time_full_body"]
    low_recovery_fixture = archetypes["low_recovery_full_body"]
    _, _, _, _, _, low_time_draft = _build_layers(low_time_fixture)
    _, _, _, _, _, low_recovery_draft = _build_layers(low_recovery_fixture)
    low_time_totals = _visible_grouped_volume_from_week_payload(
        _build_week_payload_from_draft(fixture=low_time_fixture, draft=low_time_draft)
    )
    low_recovery_totals = _visible_grouped_volume_from_week_payload(
        _build_week_payload_from_draft(fixture=low_recovery_fixture, draft=low_recovery_draft)
    )
    for totals in (low_time_totals, low_recovery_totals):
        assert totals["chest"] >= 7, totals
        assert totals["back"] >= 8, totals
        assert totals["quads"] >= 6, totals
        assert totals["hamstrings"] >= 6, totals
        assert totals["core"] >= 2, totals


def test_v25_generated_constructor_does_not_mutate_authored_program_templates() -> None:
    phase1_before = load_program_template("pure_bodybuilding_phase_1_full_body")
    phase2_before = load_program_template("pure_bodybuilding_phase_2_full_body")

    archetypes = get_generated_full_body_archetypes()
    _build_layers(archetypes["novice_gym_full_body"])
    _build_layers(archetypes["low_time_full_body"])

    phase1_after = load_program_template("pure_bodybuilding_phase_1_full_body")
    phase2_after = load_program_template("pure_bodybuilding_phase_2_full_body")

    assert phase1_before == phase1_after
    assert phase2_before == phase2_after
