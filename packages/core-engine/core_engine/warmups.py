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
    if warmup_count <= 0 or working_weight <= 0:
        return []

    rounding_rules = rounding_rules or {"increment": 0.5, "minimum": 2.0}
    increment = rounding_rules.get("increment", 0.5)
    minimum = rounding_rules.get("minimum", 2.0)

    base_steps = [0.45, 0.65, 0.82, 0.9]
    selected = base_steps[:warmup_count]
    if len(selected) < warmup_count:
        extra = [0.92 + (i * 0.02) for i in range(warmup_count - len(selected))]
        selected.extend(extra)

    warmups: list[float] = []
    for pct in selected:
        raw = max(minimum, floor(working_weight * pct))
        warmups.append(max(minimum, _round_to_increment(raw, increment)))

    return sorted(dict.fromkeys(warmups))
