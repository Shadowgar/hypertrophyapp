from math import floor


def _round_to_increment(value: float, increment: float) -> float:
    if increment <= 0:
        return value
    return round(value / increment) * increment


def compute_warmups(
    working_weight: float,
    warmup_count: int = 3,
    rounding_rules: dict[str, float] | None = None,
) -> list[float]:
    """
    Compute warm-up weights from planned working weight only.

    Ladders (percent of working weight):
    - 1 set: [0.60]
    - 2 sets: [0.50, 0.70]
    - 3 sets: [0.45, 0.65, 0.85]
    """
    if warmup_count <= 0 or working_weight <= 0:
        return []

    rounding_rules = rounding_rules or {"increment": 0.5, "minimum": 2.0}
    increment = rounding_rules.get("increment", 0.5)
    minimum = rounding_rules.get("minimum", 2.0)

    if warmup_count == 1:
        steps = [0.60]
    elif warmup_count == 2:
        steps = [0.50, 0.70]
    else:
        # Phase 1 doctrine uses at most 3 warm-ups; for higher counts,
        # repeat the 3-set ladder.
        steps = [0.45, 0.65, 0.85][: warmup_count]

    warmups: list[float] = []
    for pct in steps:
        raw = max(minimum, floor(working_weight * pct))
        warmups.append(max(minimum, _round_to_increment(raw, increment)))

    return warmups
