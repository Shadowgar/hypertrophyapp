"""Customized execution projections using the shared occurrence/receipt store.

No Authored rules or generic per-set progression runs for this program. Actual
loads remain user calibrated; unknown effort/setup never becomes history evidence.
"""
from copy import deepcopy
from fastapi import HTTPException
from .models import WorkoutSetLog, WorkoutLogCommand
from .schemas import WorkoutSetLogResponse
from .workout_history import effective_set_logs

OWNER='api.workout_customized-v1'


def feedback(db,record):
    e=record.replay_context['planned_exercise']
    rows=effective_set_logs(db).filter_by(user_id=record.user_id,workout_occurrence_id=record.workout_occurrence_id,
        exercise_occurrence_id=record.exercise_occurrence_id).all()
    work=[r for r in rows if (r.set_kind or 'work')=='work' and r.parent_set_index is None]
    count=len({r.set_index for r in work})
    live=dict(completed_sets=count,remaining_sets=max(0,e['sets']-count),recommended_reps_min=e['rep_range'][0],
        recommended_reps_max=e['rep_range'][1],recommended_weight=None,
        guidance='Record a comfortable, exercise-specific load and actual effort. No automatic progression is inferred.',
        guidance_rationale='customized_calibration_required',decision_trace=dict(owner=OWNER,
            target=e['customized'],actual_rpe_known=any(r.rpe is not None for r in work),prescription_mutation=False))
    return dict(customized_receipts=receipts(rows),live_recommendation=live,exercise_state=None,session_state=dict(completed_sets=count,
        remaining_sets=live['remaining_sets'],total_logged_reps=sum(r.reps for r in work),
        total_logged_weight=sum(r.weight for r in work)),decision_trace=live['decision_trace'])


def log_set(db,*,user,occurrence,exercise,payload,command_id,digest):
    if (payload.set_kind or 'work')!='work' or payload.parent_set_index is not None or payload.set_index>exercise['sets']:
        raise HTTPException(422,'Log one of the prescribed working sets; no extra technique sets are prescribed')
    if effective_set_logs(db).filter_by(user_id=user.id,workout_occurrence_id=occurrence.id,
        exercise_occurrence_id=exercise['exercise_occurrence_id'],set_index=payload.set_index).first():
        raise HTTPException(409,'Logical set already logged; correct or undo the existing receipt')
    db.add(occurrence);db.flush()
    record=WorkoutSetLog(user_id=user.id,workout_id=occurrence.workout_id,workout_occurrence_id=occurrence.id,
        exercise_occurrence_id=exercise['exercise_occurrence_id'],primary_exercise_id=exercise['id'],exercise_id=exercise['id'],
        set_index=payload.set_index,reps=payload.reps,weight=payload.weight,rpe=payload.rpe,set_kind='work',
        command_id=command_id,request_digest=digest,technique=deepcopy(payload.technique),
        replay_context=dict(version=3,owner=OWNER,planned_exercise=deepcopy(exercise),
            load_context=payload.load_context.model_dump(mode='json') if payload.load_context else None,
            actual_effort_kind='rpe10' if payload.rpe is not None else None))
    db.add(record);db.flush()
    live=feedback(db,record)['live_recommendation']
    response=WorkoutSetLogResponse(id=record.id,workout_occurrence_id=occurrence.id,
        exercise_occurrence_id=exercise['exercise_occurrence_id'],command_id=command_id,
        primary_exercise_id=exercise['id'],exercise_id=exercise['id'],set_index=payload.set_index,
        reps=payload.reps,weight=payload.weight,rpe=payload.rpe,set_kind='work',
        planned_reps_min=exercise['rep_range'][0],planned_reps_max=exercise['rep_range'][1],planned_weight=None,
        rep_delta=None,weight_delta=None,next_working_weight=None,guidance=live['guidance'],
        guidance_rationale=live['guidance_rationale'],decision_trace=live['decision_trace'],live_recommendation=live,created_at=record.created_at,customized_receipts=receipts(effective_set_logs(db).filter_by(user_id=user.id,workout_occurrence_id=occurrence.id,exercise_occurrence_id=exercise['exercise_occurrence_id']).all()))
    db.add(WorkoutLogCommand(user_id=user.id,command_id=command_id,request_digest=digest,
        workout_occurrence_id=occurrence.id,exercise_occurrence_id=exercise['exercise_occurrence_id'],response=response.model_dump(mode='json')))
    db.commit()
    return response


def today(db,user,session):
    result=deepcopy(session)
    rows=effective_set_logs(db).filter_by(user_id=user.id,workout_occurrence_id=session['workout_occurrence_id']).all()
    for e in result['exercises']:
        own=[r for r in rows if r.exercise_occurrence_id==e['exercise_occurrence_id']]
        e['customized_receipts']=receipts(own)
        e['completed_sets']=len({r.set_index for r in own})
        # No generic 20/25/40kg seed or Authored warm-up ladder is applicable.
        e['recommended_working_weight']=None;e['warmups']=[]
        e['starting_load_quality_source']='exercise_specific_calibration_required'
        if own:e['live_recommendation']=feedback(db,own[0])['live_recommendation']
    result['resume']=bool(rows)
    result['total_sets']=sum(e['sets'] for e in result['exercises'])
    result['planned_total']=result['total_sets']
    return result


def summary(db,user,occurrence,session):
    rows=effective_set_logs(db).filter_by(user_id=user.id,workout_occurrence_id=occurrence.id).all()
    exercises=[]
    for e in session['exercises']:
        own=[r for r in rows if r.exercise_occurrence_id==e['exercise_occurrence_id'] and (r.set_kind or 'work')=='work' and r.parent_set_index is None]
        count=len({r.set_index for r in own})
        exercises.append(dict(exercise_id=e['id'],exercise_occurrence_id=e['exercise_occurrence_id'],primary_exercise_id=e['id'],
            name=e['name'],planned_sets=e['sets'],planned_reps_min=e['rep_range'][0],planned_reps_max=e['rep_range'][1],
            planned_weight=None,performed_sets=count,average_performed_reps=sum(r.reps for r in own)/len(own) if own else 0,
            average_performed_weight=sum(r.weight for r in own)/len(own) if own else 0,completion_pct=round(100*count/e['sets']),
            rep_delta=None,weight_delta=0,next_working_weight=None,load_recommendation_available=False,load_semantics=e['load_semantics'],
            guidance='Actual work retained. Calibrate the next exercise setup; no automatic load increase is inferred.',
            guidance_rationale='customized_calibration_required',decision_trace=dict(owner=OWNER,unknown_effort_not_inferred=True)))
    planned=sum(e['sets'] for e in session['exercises']);completed=sum(e['performed_sets'] for e in exercises)
    return dict(workout_id=occurrence.workout_id,workout_occurrence_id=occurrence.id,completed_total=completed,planned_total=planned,
        percent_complete=round(100*completed/planned),overall_guidance='Workout complete' if completed==planned else 'Workout partially logged',
        overall_rationale='Completion describes logged working sets, not hypertrophy or a mandate to train through pain.',
        decision_trace=dict(owner=OWNER),exercises=exercises)


def receipts(rows):
    return [dict(id=r.id,command_id=r.command_id,set_index=r.set_index,reps=r.reps,weight=r.weight,rpe=r.rpe,
        set_kind=r.set_kind,parent_set_index=r.parent_set_index,technique=r.technique,created_at=r.created_at.isoformat())
        for r in sorted(rows,key=lambda r:(r.set_index,r.id))]
