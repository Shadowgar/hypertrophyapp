from core_engine import generate_week_plan


def test_generate_week_plan_respects_days_available() -> None:
    template = {
        "id": "full_body_v1",
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "bench",
                        "name": "Bench Press",
                        "substitution_candidates": ["db_bench", "machine_press"],
                        "notes": "Quick pause on chest",
                    }
                ],
            },
            {"name": "B", "exercises": [{"id": "squat", "name": "Squat"}]},
            {"name": "C", "exercises": [{"id": "row", "name": "Row"}]},
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
    )

    assert len(plan["sessions"]) == 2
    assert plan["split"] == "full_body"
    first_exercise = plan["sessions"][0]["exercises"][0]
    assert first_exercise["primary_exercise_id"] == "bench"
    assert first_exercise["substitution_candidates"] == ["db_bench", "machine_press"]
    assert first_exercise["notes"] == "Quick pause on chest"
    assert first_exercise["equipment_tags"] == []


def test_generate_week_plan_filters_by_available_equipment() -> None:
    template = {
        "id": "equipment_filter_test",
        "sessions": [
            {
                "name": "A",
                "exercises": [
                    {
                        "id": "barbell_row",
                        "name": "Barbell Row",
                        "equipment_tags": ["barbell"],
                        "substitution_candidates": ["Cable Row", "DB Row"],
                    },
                    {
                        "id": "db_press",
                        "name": "DB Shoulder Press",
                        "equipment_tags": ["dumbbell"],
                        "substitution_candidates": ["Machine Shoulder Press", "DB Arnold Press"],
                    },
                ],
            }
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
        available_equipment=["dumbbell"],
    )

    exercises = plan["sessions"][0]["exercises"]
    assert len(exercises) == 2
    assert [exercise["id"] for exercise in exercises] == ["db_row", "db_press"]
    assert exercises[0]["primary_exercise_id"] == "barbell_row"
    assert exercises[0]["substitution_candidates"] == ["DB Row"]
    assert exercises[1]["substitution_candidates"] == ["DB Arnold Press"]


def test_generate_week_plan_compresses_sessions_evenly_for_two_days() -> None:
    template = {
        "id": "compression_two_day",
        "sessions": [
            {"name": "Day A", "exercises": [{"id": "a", "name": "A"}]},
            {"name": "Day B", "exercises": [{"id": "b", "name": "B"}]},
            {"name": "Day C", "exercises": [{"id": "c", "name": "C"}]},
            {"name": "Day D", "exercises": [{"id": "d", "name": "D"}]},
            {"name": "Day E", "exercises": [{"id": "e", "name": "E"}]},
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=2,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
    )

    assert [session["title"] for session in plan["sessions"]] == ["Day A", "Day E"]
    assert [session["session_id"] for session in plan["sessions"]] == [
        "compression_two_day-1",
        "compression_two_day-5",
    ]


def test_generate_week_plan_compresses_sessions_evenly_for_three_days() -> None:
    template = {
        "id": "compression_three_day",
        "sessions": [
            {"name": "Day A", "exercises": [{"id": "a", "name": "A"}]},
            {"name": "Day B", "exercises": [{"id": "b", "name": "B"}]},
            {"name": "Day C", "exercises": [{"id": "c", "name": "C"}]},
            {"name": "Day D", "exercises": [{"id": "d", "name": "D"}]},
            {"name": "Day E", "exercises": [{"id": "e", "name": "E"}]},
        ],
    }

    plan = generate_week_plan(
        user_profile={"name": "Test"},
        days_available=3,
        split_preference="full_body",
        program_template=template,
        history=[],
        phase="maintenance",
    )

    assert [session["title"] for session in plan["sessions"]] == ["Day A", "Day C", "Day E"]
