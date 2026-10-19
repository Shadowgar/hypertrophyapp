"""Finite attainable loads from explicitly declared equipment, in canonical kg.

No catalog defaults, plate sizes or stack increments are inferred. These limits
bound computation/input size; they are not training recommendations.
"""
from decimal import Decimal, localcontext
import math


KG_PER_LB = Decimal("0.45359237")
MAX_ATTAINABLE_LOADS = 1024
MAX_PLATES = 128
MAX_DECLARED_WEIGHT = 1_000_000


def _number(value, *, positive=False):
    if (type(value) not in (int, float) or (type(value) is float and not math.isfinite(value))
            or value < 0 or value > MAX_DECLARED_WEIGHT or (positive and value == 0)):
        raise ValueError("Inventory weights must be finite nonnegative bounded numbers")
    return Decimal(str(value))


def _count(value):
    if type(value) is not int or not 1 <= value <= MAX_PLATES:
        raise ValueError("Inventory counts must be positive bounded integers")
    return value


def _items(rows):
    if not isinstance(rows, list) or len(rows) > MAX_ATTAINABLE_LOADS:
        raise ValueError("Inventory requires a bounded list of weight/count entries")
    counts = {}
    for row in rows:
        if not isinstance(row, dict) or "weight" not in row or "count" not in row:
            raise ValueError("Inventory entries require explicit weight and count")
        weight, count = _number(row["weight"], positive=True), _count(row["count"])
        counts[weight] = counts.get(weight, 0) + count
        if counts[weight] > MAX_PLATES:
            raise ValueError("Combined inventory count exceeds the input bound")
    return counts


def attainable_loads(setup: dict, *, required_count: int = 1) -> tuple[float, ...]:
    """Enumerate declared loads; dumbbell results remain individual weights.

    ``required_count=2`` requires a matching pair. A caller using total-external
    semantics must explicitly convert those individual weights into that basis.
    Barbell plates are counted across both sleeves and used only in equal pairs.
    Machine labels are actual weights, not percentages or assumed increments.
    ``min_load``/``max_load`` and all input weights use the declared kg/lb unit.
    """
    if not isinstance(setup, dict) or type(setup.get("unit")) is not str or setup.get("unit") not in {"kg", "lb"}:
        raise ValueError("Equipment setup requires an explicit kg/lb unit")
    _count(required_count)
    # Float input can include subnormal values; sufficient precision retains all
    # declared decimal places through pair sums and exact lb conversion.
    with localcontext() as context:
        context.prec = 400
        minimum = _number(setup["min_load"]) if "min_load" in setup else Decimal(0)
        maximum = _number(setup["max_load"]) if "max_load" in setup else Decimal(MAX_DECLARED_WEIGHT)
        if minimum > maximum:
            raise ValueError("Inventory minimum exceeds maximum")
        kind = setup.get("kind")
        if type(kind) is not str:raise ValueError("Equipment kind must be a string")
        if kind == "bodyweight":
            return ()
        if kind in {"dumbbell", "machine_stack"}:
            if kind == "machine_stack" and "stack" in setup:
                if "weights" in setup:
                    raise ValueError("Declare stack labels or a ladder, not both")
                stack = setup["stack"]
                if not isinstance(stack, dict) or any(k not in stack for k in ("minimum", "maximum", "increment")):
                    raise ValueError("Stack ladder requires explicit minimum, maximum and increment")
                low, high = _number(stack["minimum"], positive=True), _number(stack["maximum"], positive=True)
                increment = _number(stack["increment"], positive=True)
                if high < low or (high - low) // increment >= MAX_ATTAINABLE_LOADS:
                    raise ValueError("Stack ladder is reversed or exceeds the enumeration bound")
                loads = {low + i * increment for i in range(int((high - low) // increment) + 1)}
            else:
                loads = {w for w, count in _items(setup.get("weights")).items() if count >= required_count}
        elif kind == "barbell":
            bar = _number(setup.get("bar_weight"))
            counts = _items(setup.get("plates"))
            if sum(counts.values()) > MAX_PLATES:
                raise ValueError("Too many plates to enumerate")
            loads = {bar}
            for weight, count in sorted(counts.items()):
                loads = {base + 2 * weight * pairs for base in loads for pairs in range(count // 2 + 1)}
                if len(loads) > MAX_ATTAINABLE_LOADS:
                    raise ValueError("Plate combinations exceed the enumeration bound")
        else:
            raise ValueError("Unsupported equipment kind")
        factor = KG_PER_LB if setup["unit"] == "lb" else Decimal(1)
        converted = tuple(float(w * factor) for w in sorted(loads) if minimum <= w <= maximum)
        if len(set(converted)) != len(converted) or any(not math.isfinite(w) or w < 0 for w in converted):
            raise ValueError("Inventory cannot be represented as distinct finite kg loads")
        return converted
