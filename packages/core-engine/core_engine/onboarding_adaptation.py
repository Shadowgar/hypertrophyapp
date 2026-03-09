from __future__ import annotations

from collections import Counter
from typing import Any


_ROLE_SCORE = {
    "primary_compound": 100,
    "secondary_compound": 80,
    "weak_point": 90,
    "accessory": 50,
    "isolation": 40,
}


def _anchor_indexes(total_days: int, target_days: int) -> list[int]:
    if target_days >= total_days:
        return list(range(total_days))
    if target_days <= 1:
        return [0]

    indexes: list[int] = []
    for step in range(target_days):
        position = round(step * (total_days - 1) / (target_days - 1))
        if position not in indexes:
            indexes.append(position)

    fallback = 0
    while len(indexes) < target_days:
        if fallback not in indexes:
            indexes.append(fallback)
        fallback += 1

    return sorted(indexes)


def _closest_anchor(index: int, anchors: list[int]) -> int:
    return min(anchors, key=lambda item: (abs(item - index), item))


def _slot_score(
    slot: dict[str, Any],
    weak_areas: set[str],
    weak_area_bonus_by_muscle: dict[str, int],
    default_weak_area_bonus_slots: int,
) -> int:
    score = _ROLE_SCORE.get(str(slot.get("slot_role") or "accessory"), 30)
    muscles = {str(m).strip().lower() for m in slot.get("primary_muscles") or [] if str(m).strip()}
    overlapping = muscles.intersection(weak_areas)
    if overlapping:
        overlap_bonus_slots = max(
            max(default_weak_area_bonus_slots, 0),
            max((weak_area_bonus_by_muscle.get(muscle, default_weak_area_bonus_slots) for muscle in overlapping), default=0),
        )
        score += 35 + (max(overlap_bonus_slots, 0) * 10)
    return score


def _count_coverage(days: list[dict[str, Any]]) -> dict[str, int]:
    coverage: Counter[str] = Counter()
    for day in days:
        for slot in day.get("slots") or []:
            for muscle in slot.get("primary_muscles") or []:
                normalized = str(muscle).strip().lower()
                if normalized:
                    coverage[normalized] += 1
    return dict(coverage)


def adapt_onboarding_frequency(
    *,
    onboarding_package: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    blueprint = onboarding_package.get("blueprint") or {}
    adaptation_rules = onboarding_package.get("frequency_adaptation_rules") or {}

    default_days = int(blueprint.get("default_training_days") or 5)
    target_days = int(overlay.get("available_training_days") or default_days)
    duration_weeks = int(overlay.get("temporary_duration_weeks") or 1)
    current_week = max(1, int(overlay.get("current_week_index") or 1))

    default_weak_area_bonus_slots = int(adaptation_rules.get("weak_area_bonus_slots") or 1)
    weak_area_bonus_by_muscle: dict[str, int] = {}
    for entry in overlay.get("weak_areas") or []:
        if not isinstance(entry, dict):
            continue
        muscle_group = str(entry.get("muscle_group") or "").strip().lower()
        if not muscle_group:
            continue
        desired_bonus_slots = int(entry.get("desired_extra_slots_per_week") or default_weak_area_bonus_slots)
        weak_area_bonus_by_muscle[muscle_group] = max(0, desired_bonus_slots)
    weak_areas = set(weak_area_bonus_by_muscle.keys())

    week_templates = {
        str(item.get("week_template_id") or ""): item
        for item in blueprint.get("week_templates") or []
        if isinstance(item, dict)
    }
    week_sequence = [str(item) for item in blueprint.get("week_sequence") or [] if str(item)]
    if not week_sequence:
        return {
            "program_id": onboarding_package.get("program_id") or "unknown_program",
            "from_days": default_days,
            "to_days": target_days,
            "duration_weeks": duration_weeks,
            "weak_areas": sorted(weak_areas),
            "weeks": [],
            "rejoin_policy": str(adaptation_rules.get("reintegration_policy") or "Rejoin authored cadence at next week boundary."),
        }

    preserve_roles = {str(role) for role in adaptation_rules.get("preserve_slot_roles") or []}
    reduce_roles_first = {str(role) for role in adaptation_rules.get("reduce_slot_roles_first") or []}
    day_slot_cap = int(adaptation_rules.get("daily_slot_cap_when_compressed") or 8)

    weekly_results: list[dict[str, Any]] = []

    for week_offset in range(duration_weeks):
        week_index = current_week + week_offset
        template_id = week_sequence[(week_index - 1) % len(week_sequence)]
        week_template = week_templates.get(template_id, {"days": []})
        authored_days = list(week_template.get("days") or [])

        if not authored_days:
            continue

        anchors = _anchor_indexes(len(authored_days), target_days)
        adapted_days: list[dict[str, Any]] = []
        day_map: dict[int, int] = {}
        decisions: list[dict[str, Any]] = []

        for adapted_idx, authored_idx in enumerate(anchors):
            authored_day = authored_days[authored_idx]
            adapted_days.append(
                {
                    "day_id": str(authored_day.get("day_id") or f"day_{adapted_idx + 1}"),
                    "source_day_ids": [str(authored_day.get("day_id") or f"day_{adapted_idx + 1}")],
                    "exercise_ids": [str(slot.get("exercise_id")) for slot in authored_day.get("slots") or [] if str(slot.get("exercise_id") or "")],
                    "_slots": list(authored_day.get("slots") or []),
                }
            )
            day_map[authored_idx] = adapted_idx

            for slot in authored_day.get("slots") or []:
                decisions.append(
                    {
                        "action": "preserve",
                        "exercise_id": str(slot.get("exercise_id") or "unknown_exercise"),
                        "source_day_id": str(authored_day.get("day_id") or "unknown_day"),
                        "target_day_id": str(authored_day.get("day_id") or "unknown_day"),
                        "reason": "Selected as anchor day under temporary frequency compression.",
                    }
                )

        for authored_idx, authored_day in enumerate(authored_days):
            if authored_idx in anchors:
                continue

            source_day_id = str(authored_day.get("day_id") or f"day_{authored_idx + 1}")
            anchor_idx = _closest_anchor(authored_idx, anchors)
            target_adapted_idx = day_map[anchor_idx]
            target_day = adapted_days[target_adapted_idx]
            if source_day_id not in target_day["source_day_ids"]:
                target_day["source_day_ids"].append(source_day_id)

            for slot in authored_day.get("slots") or []:
                exercise_id = str(slot.get("exercise_id") or "unknown_exercise")
                slot_role = str(slot.get("slot_role") or "accessory")
                score = _slot_score(
                    slot,
                    weak_areas,
                    weak_area_bonus_by_muscle,
                    default_weak_area_bonus_slots,
                )
                muscles = {str(m).strip().lower() for m in slot.get("primary_muscles") or [] if str(m).strip()}

                if muscles.intersection(weak_areas) or slot_role in preserve_roles or score >= 85:
                    target_day["_slots"].append(slot)
                    target_day["exercise_ids"].append(exercise_id)
                    decisions.append(
                        {
                            "action": "combine",
                            "exercise_id": exercise_id,
                            "source_day_id": source_day_id,
                            "target_day_id": target_day["day_id"],
                            "reason": "Combined into nearest anchor day to preserve core stimulus.",
                        }
                    )
                    continue

                if slot_role in reduce_roles_first and ((week_index + authored_idx) % 2 == 0):
                    decisions.append(
                        {
                            "action": "reduce",
                            "exercise_id": exercise_id,
                            "source_day_id": source_day_id,
                            "target_day_id": target_day["day_id"],
                            "reason": "Reduced first under compression because slot is lower priority.",
                        }
                    )
                else:
                    target_day["_slots"].append(slot)
                    target_day["exercise_ids"].append(exercise_id)
                    decisions.append(
                        {
                            "action": "rotate",
                            "exercise_id": exercise_id,
                            "source_day_id": source_day_id,
                            "target_day_id": target_day["day_id"],
                            "reason": "Rotated into compressed week to keep variation without overloading every week.",
                        }
                    )

        for adapted_day in adapted_days:
            slots_with_scores = sorted(
                [
                    (
                        _slot_score(
                            slot,
                            weak_areas,
                            weak_area_bonus_by_muscle,
                            default_weak_area_bonus_slots,
                        ),
                        slot,
                    )
                    for slot in adapted_day["_slots"]
                ],
                key=lambda item: item[0],
                reverse=True,
            )
            kept_slots = [slot for _, slot in slots_with_scores[:day_slot_cap]]
            dropped_slots = [slot for _, slot in slots_with_scores[day_slot_cap:]]
            adapted_day["_slots"] = kept_slots
            adapted_day["exercise_ids"] = [str(slot.get("exercise_id")) for slot in kept_slots if str(slot.get("exercise_id") or "")]

            for slot in dropped_slots:
                decisions.append(
                    {
                        "action": "reduce",
                        "exercise_id": str(slot.get("exercise_id") or "unknown_exercise"),
                        "source_day_id": adapted_day["day_id"],
                        "target_day_id": adapted_day["day_id"],
                        "reason": "Reduced to respect daily slot cap and avoid unmanageable session length.",
                    }
                )

        coverage_before = _count_coverage(authored_days)
        coverage_after = _count_coverage([{"slots": day["_slots"]} for day in adapted_days])

        weekly_results.append(
            {
                "week_index": week_index,
                "adapted_training_days": target_days,
                "adapted_days": [
                    {
                        "day_id": day["day_id"],
                        "source_day_ids": day["source_day_ids"],
                        "exercise_ids": day["exercise_ids"],
                    }
                    for day in adapted_days
                ],
                "decisions": decisions,
                "coverage_before": coverage_before,
                "coverage_after": coverage_after,
                "rationale": "Compression preserves compounds and weak-area slots, reduces low-priority volume first, and rotates accessories for continuity.",
            }
        )

    return {
        "program_id": onboarding_package.get("program_id") or "unknown_program",
        "from_days": default_days,
        "to_days": target_days,
        "duration_weeks": duration_weeks,
        "weak_areas": sorted(weak_areas),
        "weeks": weekly_results,
        "rejoin_policy": str(adaptation_rules.get("reintegration_policy") or "Rejoin authored cadence at next week boundary."),
    }
