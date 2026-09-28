from core_engine.intelligence import resolve_workout_completion_per_exercise


def test_occurrence_counts_actual_slots_and_does_not_infer_missing_or_child_sets():
    logs = [{"exercise_id": "catalog", "exercise_occurrence_id": "slot", "set_index": 3},
            {"exercise_id": "catalog", "exercise_occurrence_id": "slot", "set_index": 3},
            {"exercise_id": "catalog", "exercise_occurrence_id": "slot", "set_index": 2, "parent_set_index": 3},
            {"exercise_id": "catalog", "exercise_occurrence_id": "slot", "set_index": 1, "set_kind": "warmup"},
            {"exercise_id": "catalog", "exercise_occurrence_id": "other-slot", "set_index": 2}]
    assert resolve_workout_completion_per_exercise(performed_logs=logs) == {"slot": 1, "other-slot": 1}
