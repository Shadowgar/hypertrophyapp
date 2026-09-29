"""Slot-scoped authored feasibility and receipt boundaries; never redesign dose."""
from copy import deepcopy
import re
from .equipment_profile import canonicalize_equipment_profile
from .authored_prescription import (
    requires_receipt_tracking as _receipt, is_bodyweight_authored as _bodyweight,
    typed_tracking_feedback as _feedback,
)


def restriction_conflicts(exercise, restrictions):
    normalize = lambda value: re.sub(r'[^a-z]+', '_', str(value).lower()).strip('_')
    declared = {normalize(value) for value in restrictions or []}
    pattern = normalize(exercise.get('movement_pattern') or '')
    required = {'vertical_press': 'overhead_pressing', 'squat': 'deep_knee_flexion',
        'lunge': 'deep_knee_flexion'}.get(pattern)
    return [required] if required in declared else []


def equipment_conflicts(exercise, equipment):
    available = set(canonicalize_equipment_profile(equipment))
    required = set(canonicalize_equipment_profile(exercise.get('equipment_tags'))) - {'bodyweight'}
    # Empty profiles are unknown, not evidence that every piece is missing.
    return sorted(required - available) if available else []


def annotate_constraints(exercise, *, equipment=None, restrictions=None):
    result = deepcopy(exercise)
    reasons = []
    if restriction_conflicts(exercise, restrictions):
        reasons.append({'kind': 'restriction', 'details': restriction_conflicts(exercise, restrictions)})
    if equipment_conflicts(exercise, equipment):
        reasons.append({'kind': 'equipment', 'details': equipment_conflicts(exercise, equipment)})
    choices = []
    for choice in exercise.get('source_approved_alternatives') or []:
        if equipment and not choice.get('equipment_tags'):
            continue  # Unknown equipment cannot qualify a constrained alternative.
        if restriction_conflicts(choice, restrictions) or equipment_conflicts(choice, equipment):
            continue
        if set(restrictions or []) & {"overhead_pressing", "deep_knee_flexion"} and not choice.get('movement_pattern'):
            continue  # Unknown metadata cannot qualify a restricted movement.
        choices.append(deepcopy(choice))
    result['authored_constraint'] = {'status': ('unresolved' if choices else 'infeasible') if reasons else 'ready',
        'reasons': reasons, 'allowed_alternatives': choices, 'revision': 0}
    result['substitution_candidates'] = []  # No generic automatic/local swap path.
    result['substitution_decision_trace'] = {'owner': 'core_engine.authored_constraints',
        'version': 'v1', 'source_lineage': deepcopy(exercise.get('source_lineage')),
        'inputs': {'equipment': list(equipment or []), 'restrictions': list(restrictions or [])},
        'outcome': {'status': result['authored_constraint']['status'], 'prescription_changed': False,
            'confirmation_required': bool(reasons)}}
    return result


def refresh_constraints(exercise, *, equipment=None, restrictions=None):
    """Current feasibility is separate from frozen substitution consent."""
    old = exercise.get('authored_constraint') or {}
    variant = exercise.get('performed_variant')
    refreshed = annotate_constraints(variant or exercise, equipment=equipment,
        restrictions=restrictions)['authored_constraint']
    reports = deepcopy(old.get('reported_conflicts'))
    if reports is None:
        reports = [deepcopy(reason) for reason in old.get('reasons') or []
            if 'user_reported' in (reason.get('details') or []) and old.get('status') != 'confirmed']
    reasons = [*refreshed['reasons'], *reports]
    status = ('unresolved' if refreshed['allowed_alternatives'] else 'infeasible') if reasons else 'ready'
    if not variant and reasons and old.get('status') == 'declined':
        status = 'declined'
    return {**refreshed, 'revision': int(old.get('revision') or 0), 'reasons': reasons,
        'reported_conflicts': reports, 'status': 'confirmed' if variant else status,
        'execution_status': status}


def project_variant_load(exercise):
    """Presentation only: retain original load context without prescribing it for a variant."""
    result = deepcopy(exercise)
    if result.get('performed_variant'):
        result['source_load_context'] = deepcopy(result.get('source_load_context') or {
            'recommended_working_weight': result.get('recommended_working_weight'),
            'warmups': result.get('warmups') or []})
        result['recommended_working_weight'] = 0.0  # Compatibility DTO, not a starting-load recommendation.
        result['warmups'] = []
        result['load_recommendation_available'] = False
    return result


def requires_receipt_tracking(exercise):
    return bool((exercise or {}).get('performed_variant')) or _receipt(exercise)


def is_bodyweight_authored(exercise):
    variant = (exercise or {}).get('performed_variant')
    return variant.get('load_semantics') == 'bodyweight' if variant else _bodyweight(exercise)


def typed_tracking_feedback(exercise, **kwargs):
    projected = deepcopy(exercise)
    if projected.get('performed_variant'):
        projected['load_semantics'] = projected['performed_variant'].get('load_semantics')
        projected['recommended_working_weight'] = 0.0
    result = _feedback(projected, **kwargs)
    if exercise.get('performed_variant'):
        result['guidance'] = 'Follow the source target and record the actual performed variant load.'
        result['guidance_rationale'] = 'confirmed_variant_receipt_only'
        result['decision_trace'].update(performed_variant=deepcopy(exercise['performed_variant']),
            source_slot=deepcopy(exercise.get('source_lineage')), load_recommendation_available=False)
    return result
