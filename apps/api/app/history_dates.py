"""Read-only history dates; immutable occurrence placement owns dated receipts.

Policy occurrence-performed-date-v1: an owner-bound occurrence's scheduled_date
is the performed date. Null/legacy or foreign-owner references retain the audit
timestamp's calendar date. Audit timestamps and amendment lineage never change.
"""
from copy import deepcopy
from datetime import date

from sqlalchemy import Date, and_, func
from sqlalchemy.orm import Session

from .models import WorkoutOccurrence, WorkoutSetLog
from .workout_history import effective_set_logs


def performed_log_query(db: Session, *, user_id: str, start_date: date | None = None,
    end_date: date | None = None, exercise_id: str | None = None):
    performed_date = func.coalesce(WorkoutOccurrence.scheduled_date,
        func.date(WorkoutSetLog.created_at, type_=Date), type_=Date)
    query = (effective_set_logs(db).outerjoin(WorkoutOccurrence, and_(
        WorkoutOccurrence.id == WorkoutSetLog.workout_occurrence_id,
        WorkoutOccurrence.user_id == WorkoutSetLog.user_id))
        .filter(WorkoutSetLog.user_id == user_id)
        .add_columns(performed_date.label('performed_date')))
    if start_date is not None:
        query = query.filter(performed_date >= start_date)
    if end_date is not None:
        query = query.filter(performed_date <= end_date)
    if exercise_id is not None:
        query = query.filter(WorkoutSetLog.exercise_id == exercise_id)
    return query


def performed_log_rows(db: Session, *, user_id: str, start_date: date | None = None,
    end_date: date | None = None, exercise_id: str | None = None,
    limit: int | None = None, descending: bool = False) -> list[dict]:
    """Filter in SQL, then detach every receipt field plus its explicit date."""
    query = performed_log_query(db, user_id=user_id, start_date=start_date,
        end_date=end_date, exercise_id=exercise_id)
    timestamp_order = WorkoutSetLog.created_at.desc() if descending else WorkoutSetLog.created_at.asc()
    query = query.order_by(timestamp_order, WorkoutSetLog.set_index.asc(), WorkoutSetLog.id.asc())
    if limit is not None:
        query = query.limit(limit)
    return [{**{column.key: deepcopy(getattr(log, column.key)) for column in WorkoutSetLog.__table__.columns},
        'performed_date': performed_date} for log, performed_date in query.all()]
