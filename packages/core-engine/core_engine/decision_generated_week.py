from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from .decision_frequency_adaptation import apply_active_frequency_adaptation_runtime
from .decision_weekly_review import apply_weekly_review_adjustments_to_plan
from .scheduler import generate_week_plan


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def summarize_generation_template_viability(
    *,
    template: dict[str, Any],
    days_available: int,
    split_preference: str,
    nutrition_phase: str,
    available_equipment: list[str],
) -> dict[str, int]:
    preview = generate_week_plan(
        user_profile={"name": "preview"},
        days_available=days_available,
        split_preference=split_preference,
        program_template=template,
        history=[],
        phase=nutrition_phase,
        available_equipment=available_equipment,
    )
    sessions = preview.get("sessions") or []
    return {
        "session_count": len(sessions),
        "exercise_count": sum(len(session.get("exercises") or []) for session in sessions),
    }


def _template_summary_rank(
    summary: dict[str, Any],
    *,
    split_preference: str,
    days_available: int,
) -> tuple[int, int, int, str]:
    split_rank = 0 if str(summary.get("split") or "") == split_preference else 1
    session_count = int(summary.get("session_count") or 0)
    adaptation_rank = 0 if 2 <= days_available <= 4 and session_count >= 5 else 1
    return (split_rank, adaptation_rank, -session_count, str(summary.get("id") or ""))


def _append_ordered_candidate_ids(
    *,
    ordered: list[str],
    candidate_summaries: list[dict[str, Any]],
    predicate,
) -> None:
    for summary in candidate_summaries:
        template_id = str(summary.get("id") or "")
        if not template_id or template_id in ordered:
            continue
        if predicate(summary):
            ordered.append(template_id)


def _ordered_generation_candidate_ids(
    *,
    preferred_template_id: str | None,
    split_preference: str,
    days_available: int,
    candidate_summaries: list[dict[str, Any]],
) -> list[str]:
    sorted_summaries = sorted(
        candidate_summaries,
        key=lambda summary: _template_summary_rank(
            summary,
            split_preference=split_preference,
            days_available=days_available,
        ),
    )
    ordered: list[str] = []

    preferred_id = str(preferred_template_id or "")
    if preferred_id:
        ordered.append(preferred_id)

    _append_ordered_candidate_ids(
        ordered=ordered,
        candidate_summaries=sorted_summaries,
        predicate=lambda summary: (
            summary.get("split") == split_preference and days_available in (summary.get("days_supported") or [])
        ),
    )
    _append_ordered_candidate_ids(
        ordered=ordered,
        candidate_summaries=sorted_summaries,
        predicate=lambda summary: days_available in (summary.get("days_supported") or []),
    )

    if "full_body_v1" not in ordered:
        ordered.append("full_body_v1")
    return ordered


def order_generation_template_candidates(
    *,
    preferred_template_id: str | None,
    split_preference: str,
    days_available: int,
    candidate_summaries: list[dict[str, Any]],
) -> list[str]:
    return _ordered_generation_candidate_ids(
        preferred_template_id=preferred_template_id,
        split_preference=split_preference,
        days_available=days_available,
        candidate_summaries=candidate_summaries,
    )


def _generation_selection_trace(
    *,
    reason: str,
    explicit_template_id: str,
    profile_template_id: str | None,
    split_preference: str,
    days_available: int,
    ordered_candidate_ids: list[str],
    evaluations: list[dict[str, Any]],
    selected_template_id: str,
) -> dict[str, Any]:
    return {
        "interpreter": "recommend_generation_template_selection",
        "owner_family": "generated_week",
        "reason": reason,
        "explicit_template_id": explicit_template_id,
        "profile_template_id": str(profile_template_id or ""),
        "split_preference": split_preference,
        "days_available": int(days_available),
        "ordered_candidate_ids": ordered_candidate_ids,
        "evaluations": evaluations,
        "selected_template_id": selected_template_id,
    }


def _summarize_generation_evaluation(template_id: str, evaluation: dict[str, Any] | None) -> dict[str, Any]:
    if evaluation is None:
        return {"template_id": template_id, "status": "not_evaluated"}

    status = str(evaluation.get("status") or "unknown")
    session_count = int(evaluation.get("session_count") or 0)
    exercise_count = int(evaluation.get("exercise_count") or 0)
    return {
        "template_id": template_id,
        "status": status,
        "session_count": session_count,
        "exercise_count": exercise_count,
        "viable": status == "loaded" and session_count > 0 and exercise_count > 0,
    }


def _select_viable_generation_candidate(
    *,
    ordered_candidate_ids: list[str],
    evaluation_by_id: dict[str, dict[str, Any]],
) -> tuple[str | None, str | None, list[dict[str, Any]]]:
    fallback_template_id: str | None = None
    evaluation_trace: list[dict[str, Any]] = []

    for template_id in ordered_candidate_ids:
        summary = _summarize_generation_evaluation(template_id, evaluation_by_id.get(template_id))
        evaluation_trace.append(summary)

        if summary["status"] == "loaded" and fallback_template_id is None:
            fallback_template_id = template_id

        if summary["viable"]:
            return template_id, fallback_template_id, evaluation_trace

    return None, fallback_template_id, evaluation_trace


def recommend_generation_template_selection(
    *,
    explicit_template_id: str | None,
    profile_template_id: str | None,
    split_preference: str,
    days_available: int,
    candidate_summaries: list[dict[str, Any]],
    candidate_evaluations: list[dict[str, Any]],
) -> dict[str, Any]:
    explicit_id = str(explicit_template_id or "").strip()
    if explicit_id:
        decision_trace = _generation_selection_trace(
            reason="explicit_template_override",
            explicit_template_id=explicit_id,
            profile_template_id=profile_template_id,
            split_preference=split_preference,
            days_available=days_available,
            ordered_candidate_ids=[explicit_id],
            evaluations=[{"template_id": explicit_id, "status": "explicit_override"}],
            selected_template_id=explicit_id,
        )
        return {
            "selected_template_id": explicit_id,
            "reason": "explicit_template_override",
            "decision_trace": decision_trace,
        }

    ordered_candidate_ids = _ordered_generation_candidate_ids(
        preferred_template_id=profile_template_id,
        split_preference=split_preference,
        days_available=days_available,
        candidate_summaries=candidate_summaries,
    )
    evaluation_by_id = {
        str(item.get("template_id") or ""): item
        for item in candidate_evaluations
        if str(item.get("template_id") or "")
    }

    selected_template_id, fallback_template_id, evaluation_trace = _select_viable_generation_candidate(
        ordered_candidate_ids=ordered_candidate_ids,
        evaluation_by_id=evaluation_by_id,
    )
    if selected_template_id:
        decision_trace = _generation_selection_trace(
            reason="first_viable_candidate",
            explicit_template_id="",
            profile_template_id=profile_template_id,
            split_preference=split_preference,
            days_available=days_available,
            ordered_candidate_ids=ordered_candidate_ids,
            evaluations=evaluation_trace,
            selected_template_id=selected_template_id,
        )
        return {
            "selected_template_id": selected_template_id,
            "reason": "first_viable_candidate",
            "decision_trace": decision_trace,
        }

    if fallback_template_id:
        decision_trace = _generation_selection_trace(
            reason="fallback_loaded_candidate",
            explicit_template_id="",
            profile_template_id=profile_template_id,
            split_preference=split_preference,
            days_available=days_available,
            ordered_candidate_ids=ordered_candidate_ids,
            evaluations=evaluation_trace,
            selected_template_id=fallback_template_id,
        )
        return {
            "selected_template_id": fallback_template_id,
            "reason": "fallback_loaded_candidate",
            "decision_trace": decision_trace,
        }

    raise FileNotFoundError("No valid program templates available for generation")


def resolve_generation_template_choice(
    *,
    explicit_template_id: str | None,
    explicit_template: dict[str, Any] | None,
    profile_template_id: str | None,
    split_preference: str,
    days_available: int,
    nutrition_phase: str,
    available_equipment: list[str],
    candidate_summaries: list[dict[str, Any]],
    loaded_candidate_templates: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if explicit_template_id:
        if explicit_template is None:
            raise FileNotFoundError("No valid program templates available for generation")
        selection = recommend_generation_template_selection(
            explicit_template_id=explicit_template_id,
            profile_template_id=profile_template_id,
            split_preference=split_preference,
            days_available=days_available,
            candidate_summaries=[],
            candidate_evaluations=[],
        )
        return {
            "selected_template_id": explicit_template_id,
            "selected_template": explicit_template,
            "decision_trace": dict(selection["decision_trace"]),
        }

    ordered_candidates = order_generation_template_candidates(
        preferred_template_id=profile_template_id,
        split_preference=split_preference,
        days_available=days_available,
        candidate_summaries=candidate_summaries,
    )

    candidate_evaluations: list[dict[str, Any]] = []
    templates_by_id: dict[str, dict[str, Any]] = {}
    for candidate_id in ordered_candidates:
        candidate_template = loaded_candidate_templates.get(candidate_id)
        if not isinstance(candidate_template, dict):
            candidate_evaluations.append({"template_id": candidate_id, "status": "unavailable"})
            continue
        templates_by_id[candidate_id] = candidate_template
        viability = summarize_generation_template_viability(
            template=candidate_template,
            days_available=days_available,
            split_preference=split_preference,
            nutrition_phase=nutrition_phase,
            available_equipment=available_equipment,
        )
        candidate_evaluations.append(
            {
                "template_id": candidate_id,
                "status": "loaded",
                **viability,
            }
        )

    selection = recommend_generation_template_selection(
        explicit_template_id=None,
        profile_template_id=profile_template_id,
        split_preference=split_preference,
        days_available=days_available,
        candidate_summaries=candidate_summaries,
        candidate_evaluations=candidate_evaluations,
    )
    selected_template_id = str(selection["selected_template_id"])
    selected_template = templates_by_id.get(selected_template_id)
    if selected_template is None:
        raise FileNotFoundError("No valid program templates available for generation")

    return {
        "selected_template_id": selected_template_id,
        "selected_template": selected_template,
        "decision_trace": dict(selection["decision_trace"]),
    }


def _generation_reason_summary(
    *,
    final_plan: dict[str, Any],
    selected_template_id: str,
    template_selection_trace: dict[str, Any],
    generation_runtime_trace: dict[str, Any],
) -> str:
    selection_reason = str(template_selection_trace.get("reason") or "").strip()
    runtime_outcome = _coerce_dict(generation_runtime_trace.get("outcome"))
    effective_days = runtime_outcome.get("effective_days_available") or _coerce_dict(final_plan.get("user")).get(
        "days_available"
    )
    session_count = len(final_plan.get("sessions") or [])

    if selection_reason == "explicit_template_override":
        prefix = f"Selected {selected_template_id} because the request explicitly overrode template selection."
    elif selection_reason == "first_viable_candidate":
        prefix = f"Selected {selected_template_id} as the first viable template for the current generation inputs."
    elif selection_reason == "fallback_loaded_candidate":
        prefix = f"Selected {selected_template_id} as the fallback loaded template after higher-ranked candidates failed viability."
    else:
        prefix = f"Generated the week from template {selected_template_id} using the current canonical generation inputs."

    details: list[str] = []
    if effective_days is not None:
        details.append(f"Built {session_count} sessions for {effective_days} effective training days.")
    else:
        details.append(f"Built {session_count} sessions for the current training week.")
    if bool(_coerce_dict(final_plan.get("deload")).get("active")):
        details.append("The resulting week is in deload posture.")
    if final_plan.get("adaptive_review"):
        details.append("Weekly-review adjustments were applied.")
    if final_plan.get("applied_frequency_adaptation"):
        details.append("Active frequency adaptation was applied.")
    return " ".join([prefix, *details]).strip()


def _generated_week_alternative_resolution(template_selection_trace: dict[str, Any]) -> dict[str, Any]:
    evaluations = [
        evaluation
        for evaluation in list(template_selection_trace.get("evaluations") or [])
        if isinstance(evaluation, dict)
    ]
    selected_template_id = str(template_selection_trace.get("selected_template_id") or "").strip()
    rejected_candidates = [
        {
            "template_id": str(evaluation.get("template_id") or ""),
            "status": str(evaluation.get("status") or ""),
            "viable": bool(evaluation.get("viable")),
        }
        for evaluation in evaluations
        if str(evaluation.get("template_id") or "").strip()
        and str(evaluation.get("template_id") or "").strip() != selected_template_id
    ]
    return {
        "status": "candidates_considered",
        "selected_template_id": selected_template_id,
        "ordered_candidate_ids": _coerce_string_list(template_selection_trace.get("ordered_candidate_ids")),
        "rejected_candidates": rejected_candidates,
    }


def _generated_week_decision_trace(
    *,
    final_plan: dict[str, Any],
    selected_template_id: str,
    template_selection_trace: dict[str, Any],
    generation_runtime_trace: dict[str, Any],
    review_overlay_trace: dict[str, Any] | None,
    adaptation_runtime: dict[str, Any],
) -> dict[str, Any]:
    runtime_outcome = _coerce_dict(generation_runtime_trace.get("outcome"))
    adaptation_trace = _coerce_dict(_coerce_dict(final_plan.get("applied_frequency_adaptation")).get("decision_trace"))
    review_trace = _coerce_dict(review_overlay_trace)
    review_outcome = _coerce_dict(review_trace.get("outcome"))
    return {
        "interpreter": "recommend_generated_week",
        "version": "v1",
        "owner_family": "generated_week",
        "trust_scope": "bounded_generation",
        "canonical_inputs": {
            "selected_template_id": selected_template_id,
            "split_preference": str(final_plan.get("split") or ""),
            "nutrition_phase": str(final_plan.get("phase") or ""),
            "effective_days_available": runtime_outcome.get("effective_days_available"),
            "prior_generated_weeks": runtime_outcome.get("prior_generated_weeks"),
            "latest_adherence_score": runtime_outcome.get("latest_adherence_score"),
            "severe_soreness_count": runtime_outcome.get("severe_soreness_count"),
            "stimulus_fatigue_response": deepcopy(runtime_outcome.get("stimulus_fatigue_response")),
        },
        "policy_basis": {
            "template_selection": {
                "reason": str(template_selection_trace.get("interpreter") or ""),
                "selection_outcome": str(template_selection_trace.get("reason") or ""),
            },
            "week_generation": {
                "reason": "scheduler.generate_week_plan",
                "deload_active": bool(_coerce_dict(final_plan.get("deload")).get("active")),
            },
            "review_overlay": {
                "reason": str(review_trace.get("interpreter") or ""),
                "review_available": bool(review_outcome.get("review_available")),
            },
            "frequency_adaptation": {
                "reason": str(adaptation_trace.get("interpreter") or ""),
                "active": bool(final_plan.get("applied_frequency_adaptation")),
            },
        },
        "execution_steps": [
            {
                "step": "template_selection",
                "result": deepcopy(template_selection_trace),
            },
            {
                "step": "week_generation",
                "result": {
                    "session_count": len(final_plan.get("sessions") or []),
                    "week_start": final_plan.get("week_start"),
                    "deload_active": bool(_coerce_dict(final_plan.get("deload")).get("active")),
                },
            },
            {
                "step": "review_overlay",
                "result": deepcopy(review_trace),
            },
            {
                "step": "frequency_adaptation",
                "result": deepcopy(adaptation_trace),
            },
        ],
        "outcome": {
            "program_template_id": str(final_plan.get("program_template_id") or ""),
            "week_start": str(final_plan.get("week_start") or ""),
            "session_count": len(final_plan.get("sessions") or []),
            "deload_active": bool(_coerce_dict(final_plan.get("deload")).get("active")),
            "review_applied": bool(final_plan.get("adaptive_review")),
            "frequency_adaptation_applied": bool(final_plan.get("applied_frequency_adaptation")),
            "state_updated": bool(adaptation_runtime.get("state_updated")),
        },
        "reason_summary": _generation_reason_summary(
            final_plan=final_plan,
            selected_template_id=selected_template_id,
            template_selection_trace=template_selection_trace,
            generation_runtime_trace=generation_runtime_trace,
        ),
        "alternative_resolution": _generated_week_alternative_resolution(template_selection_trace),
    }


def build_generated_week_plan_payload(
    *,
    base_plan: dict[str, Any],
    template_selection_trace: dict[str, Any],
    generation_runtime_trace: dict[str, Any],
    selected_template_id: str,
    active_frequency_adaptation: dict[str, Any] | None,
    review_adjustments: dict[str, Any] | None = None,
    review_context: dict[str, Any] | None = None,
    review_overlay_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = deepcopy(base_plan)
    plan["template_selection_trace"] = deepcopy(template_selection_trace)
    plan["generation_runtime_trace"] = deepcopy(generation_runtime_trace)

    if review_adjustments is not None:
        plan = apply_weekly_review_adjustments_to_plan(
            plan_payload=plan,
            review_adjustments=review_adjustments,
            review_context=review_context,
        )

    adaptation_runtime = apply_active_frequency_adaptation_runtime(
        plan=plan,
        selected_template_id=selected_template_id,
        active_frequency_adaptation=active_frequency_adaptation,
    )
    finalized_plan = cast(dict[str, Any], adaptation_runtime["plan"])
    finalized_plan["decision_trace"] = _generated_week_decision_trace(
        final_plan=finalized_plan,
        selected_template_id=selected_template_id,
        template_selection_trace=template_selection_trace,
        generation_runtime_trace=generation_runtime_trace,
        review_overlay_trace=review_overlay_trace,
        adaptation_runtime=adaptation_runtime,
    )
    return {
        "plan": finalized_plan,
        "adaptation_runtime": adaptation_runtime,
    }
