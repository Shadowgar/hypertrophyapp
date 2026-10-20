"""Scoped effective receipt admission into the existing C1 calibration owner."""
from collections import defaultdict
from datetime import timedelta

from core_engine.customized.models import LoadIdentity, ExposureTarget, CompletedExposure, CompletedSet
from core_engine.customized.calibration import recommend_calibrated_load
from core_engine.customized.policies import candidate_standard
from .models import WorkoutOccurrence, WorkoutSetLog
from .customized_inventory import catalog_for_profile,read_profile,strength_reports


def target_for(exercise):
    c=exercise['customized']
    return ExposureTarget(*exercise['rep_range'],c['target_kind'],c['target_min'],c['target_max'])


def exposure_query(db,subject,as_of,variant_ids,*,max_age_days):
    return (db.query(WorkoutSetLog,WorkoutOccurrence)
        .join(WorkoutOccurrence,WorkoutOccurrence.id==WorkoutSetLog.workout_occurrence_id)
        .filter(WorkoutSetLog.user_id==subject,WorkoutOccurrence.user_id==subject,
            WorkoutOccurrence.program_id=='customized_full_body_v1',
            WorkoutOccurrence.scheduled_date>=as_of-timedelta(days=max_age_days),
            WorkoutOccurrence.scheduled_date<=as_of,WorkoutSetLog.exercise_id.in_(tuple(variant_ids)))
        .order_by(WorkoutOccurrence.scheduled_date,WorkoutSetLog.workout_occurrence_id,
            WorkoutSetLog.exercise_occurrence_id,WorkoutSetLog.set_index))


def completed_exposures(db,subject,as_of,variant_ids,*,max_age_days):
    """Range first on authoritative occurrence dates; amendments keep original date.

    Include voids and complete revision chains. No user-lifetime scan or row LIMIT
    that truncates a set/exposure. Repeated occurrences remain distinct.
    """
    rows=exposure_query(db,subject,as_of,variant_ids,max_age_days=max_age_days).all()
    grouped=defaultdict(list)
    for row,occurrence in rows:grouped[(occurrence.id,row.exercise_occurrence_id)].append((row,occurrence))
    result=[]
    for (oid,eid),pairs in grouped.items():
        by_id={r.id:r for r,_ in pairs};first,occurrence=pairs[0]
        e=(first.replay_context or {}).get('planned_exercise') or {}
        if not e.get('customized'):continue  # Uncaptured legacy evidence is never qualified.
        try:identity=LoadIdentity(**e['customized']['identity']);target=target_for(e)
        except (KeyError,TypeError):continue
        records=[]
        for r,_ in pairs:
            current=r;revision=0;seen=set()
            while current.supersedes_id:
                if current.id in seen or current.supersedes_id not in by_id:
                    revision=-1;break
                seen.add(current.id);current=by_id[current.supersedes_id];revision+=1
            replay=r.replay_context or {};stored=replay.get('planned_exercise',{}).get('customized',{}).get('identity')
            try:record_identity=LoadIdentity(**stored) if stored else None
            except TypeError:record_identity=None
            records.append(CompletedSet(r.id,current.id,r.set_index,revision,
                'voided' if r.voided_at else 'completed',r.set_kind or 'work',str(r.parent_set_index) if r.parent_set_index else None,
                r.weight,r.reps,'rir' if replay.get('actual_rir') is not None else 'rpe10' if r.rpe is not None else None,
                replay.get('actual_rir') if replay.get('actual_rir') is not None else r.rpe,
                replay.get('technique_quality') or 'unknown',replay.get('pain'),record_identity))
        result.append(CompletedExposure('c1-exposure-v1',oid,eid,occurrence.scheduled_date,identity,target,
            tuple(range(1,e['sets']+1)),True,tuple(records),'effective_receipt_chain:'+oid+':'+eid))
    return tuple(result)


def calibration_for(db,user_id,exercise,as_of):
    from .customized_application import application_catalog
    profile=read_profile(db,user_id)
    catalog=catalog_for_profile(application_catalog(),profile)
    matches=[e for e in catalog.exercises if e.variant_id==exercise['id'] and
        e.load_identity==LoadIdentity(**exercise['customized']['identity'])]
    if len(matches)!=1:
        return dict(version='customized-bounded-calibration-v1',action='monitor',recommended_weight=None,unit='kg',
            policy_status='provisional',reason_codes=['actual_equipment_setup_unavailable_or_changed'],calibration=None)
    status=exercise['customized'].get('training_status')
    if status not in {'new','returning','current'}:
        return dict(version='customized-bounded-calibration-v1',action='monitor',recommended_weight=None,unit='kg',
            policy_status='provisional',reason_codes=['training_context_missing_reconfirm_before_calibration'],calibration=None)
    policy=candidate_standard(status).science
    exposures=completed_exposures(db,user_id,as_of,[exercise['id']],max_age_days=policy.calibration.history_max_age_days)
    result=recommend_calibrated_load(exercise=matches[0],target=target_for(exercise),policy=policy,as_of=as_of,
        exposures=exposures,strength_reports=strength_reports(profile,catalog,as_of),required_set_indices=tuple(range(1,exercise["sets"]+1)))
    result['inventory_revision']=profile['revision']
    result['attainable_loads']=list(matches[0].attainable_loads)
    result['identity']=vars(matches[0].load_identity)
    return result
