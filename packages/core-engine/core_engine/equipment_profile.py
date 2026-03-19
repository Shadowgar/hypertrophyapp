from __future__ import annotations

from typing import Iterable


_EQUIPMENT_SYNONYMS = {
    "bar": "barbell",
    "bb": "barbell",
    "db": "dumbbell",
    "bw": "bodyweight",
    "cables": "cable",
    "smith": "smith_machine",
}


def canonicalize_equipment_item(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return None
    return _EQUIPMENT_SYNONYMS.get(normalized, normalized)


def canonicalize_equipment_profile(values: Iterable[str] | None) -> list[str]:
    canonical: list[str] = []
    seen: set[str] = set()
    for item in values or []:
        normalized = canonicalize_equipment_item(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        canonical.append(normalized)
    return canonical
