from core_engine import compute_warmups


def test_compute_warmups_returns_sorted_positive_values() -> None:
    warmups = compute_warmups(working_weight=100, warmup_count=3)
    assert warmups == sorted(warmups)
    assert len(warmups) >= 1
    assert all(weight > 0 for weight in warmups)


def test_compute_warmups_empty_for_invalid_inputs() -> None:
    assert compute_warmups(0, 3) == []
    assert compute_warmups(100, 0) == []
