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
