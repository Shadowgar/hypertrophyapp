from core_engine import compute_warmups


def test_compute_warmups_returns_doctrine_percentages() -> None:
    """Warm-ups follow 60; 50/70; 45/65/85 percent ladders."""
    warmups_1 = compute_warmups(working_weight=100, warmup_count=1)
    warmups_2 = compute_warmups(working_weight=100, warmup_count=2)
    warmups_3 = compute_warmups(working_weight=100, warmup_count=3)

    assert warmups_1 == [60.0]
    assert warmups_2 == [50.0, 70.0]
    assert warmups_3 == [45.0, 65.0, 85.0]


def test_compute_warmups_empty_for_invalid_inputs() -> None:
    assert compute_warmups(0, 3) == []
    assert compute_warmups(100, 0) == []
