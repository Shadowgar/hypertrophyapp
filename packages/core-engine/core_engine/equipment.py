import re


_FALLBACK_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bD\.?B\.?\b|\bDUMBBELL\b", re.IGNORECASE), "dumbbell"),
    (re.compile(r"\bB\.?B\.?\b|\bBARBELL\b", re.IGNORECASE), "barbell"),
    (re.compile(r"\bCABLE\b", re.IGNORECASE), "cable"),
    (re.compile(r"\bMACHINE\b", re.IGNORECASE), "machine"),
    (re.compile(r"\bBW\b|\bBODYWEIGHT\b", re.IGNORECASE), "bodyweight"),
)


def infer_equipment_tags_from_name(exercise_name: str) -> list[str]:
    tags: list[str] = []
    for pattern, tag in _FALLBACK_RULES:
        if pattern.search(exercise_name) and tag not in tags:
            tags.append(tag)
    return tags


def resolve_equipment_tags(exercise_name: str, explicit_tags: list[str] | None = None) -> list[str]:
    if explicit_tags:
        return list(dict.fromkeys(explicit_tags))
    return infer_equipment_tags_from_name(exercise_name)
