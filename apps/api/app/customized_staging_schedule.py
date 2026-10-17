"""Read-only #83-shaped revision projection. No ORM/SQL/scheduler imports.

The source implementation at the pinned PR remains unmerged. These envelopes
model its stable account/occurrence/placement fields and effective-history seam;
no live source verification is claimed and no factory can promote them to it.
"""
from dataclasses import dataclass,replace
from datetime import date,timedelta
from typing import Literal,Protocol

from core_engine.customized.audit import canonical,content_hash
from core_engine.customized.models import PlanningContext
from .customized_lifecycle_models import LifecycleError
from .customized_lifecycle_schedule import ScheduleOccurrence,ScheduleSnapshot
import json

SOURCE_CONTRACT='pr83@3f4927b3cdcca1e8655337b30b93894741bfca9c'


@dataclass(frozen=True)
class CalendarOccurrence:
    subject: str
    occurrence_id: str
    plan_id: str
    week_start: date
    scheduled_date: date
    schedule_timezone: str
    placement_revision: int
    status: Literal['planned','started','completed','partial']
    mode: Literal['authored','customized']
    prescription_hash: str
    source_slot_ids: tuple[str,...]
    voided: bool
    history_revision: str


@dataclass(frozen=True)
class CalendarWindow:
    subject: str
    timezone: str
    start: date
    end: date
    source_revision: str
    source_contract: str
    occurrences: tuple[CalendarOccurrence,...]
    complete: bool


class CalendarReadPort(Protocol):
    def read(self,subject: str,timezone: str,start: date,end: date) -> CalendarWindow: ...


class ReadOnlyCalendarAdapter:
    def __init__(self,source: CalendarReadPort,*,context: PlanningContext):self.source,self.context=source,context

    def resolve(self,subject,timezone):
        start=self.context.week_start-timedelta(days=7);end=self.context.week_start+timedelta(days=13)
        window=self.source.read(subject,timezone,start,end)
        def invalid():raise LifecycleError('invalid_calendar_context')
        if (not isinstance(window,CalendarWindow) or window.subject!=subject or window.timezone!=timezone
                or window.start!=start or window.end!=end or not window.source_revision
                or window.source_contract!=SOURCE_CONTRACT or type(window.complete) is not bool):invalid()
        by_id={}
        for row in window.occurrences:
            if (not isinstance(row,CalendarOccurrence) or row.subject!=subject or row.schedule_timezone!=timezone
                    or not row.occurrence_id or not row.plan_id or type(row.scheduled_date) is not date
                    or not start<=row.scheduled_date<=end or type(row.week_start) is not date
                    or row.week_start.weekday()!=0 or not row.week_start<=row.scheduled_date<row.week_start+timedelta(days=7)
                    or row.status not in {'planned','started','completed','partial'} or row.mode not in {'authored','customized'}
                    or type(row.placement_revision) is not int or row.placement_revision<1 or type(row.voided) is not bool
                    or not row.prescription_hash or not row.source_slot_ids or not row.history_revision):invalid()
            by_id.setdefault(row.occurrence_id,[]).append(row)
        effective=[]
        for id,rows in sorted(by_id.items()):
            versions={}
            for row in rows:
                if row.placement_revision in versions and row!=versions[row.placement_revision]:
                    raise LifecycleError('ambiguous_calendar_revision')
                versions[row.placement_revision]=row
            ordered=sorted(versions.values(),key=lambda r:r.placement_revision)
            frozen=next((r for r in ordered if r.status in {'started','completed','partial'}),None)
            latest=ordered[-1]
            if frozen and (latest.voided or latest.status=='planned' or any(
                    (r.scheduled_date,r.prescription_hash,r.source_slot_ids,r.plan_id,r.mode)!=(frozen.scheduled_date,frozen.prescription_hash,frozen.source_slot_ids,frozen.plan_id,frozen.mode)
                    for r in ordered if r.placement_revision>=frozen.placement_revision)):
                raise LifecycleError('frozen_occurrence_changed')
            if not latest.voided:
                effective.append(ScheduleOccurrence(id,latest.scheduled_date,latest.status,latest.mode,latest.prescription_hash,latest.source_slot_ids))
        # Retain every revision, including voids and history/correction revisions,
        # in freshness/audit without turning a cancelled plan into performed work.
        window=replace(window,occurrences=tuple(sorted(set(window.occurrences),key=lambda r:(r.occurrence_id,r.placement_revision,content_hash(r)))))
        source_evidence=json.dumps(canonical(window),sort_keys=True,separators=(',',':'))
        return ScheduleSnapshot(subject,timezone,content_hash(window),self.context,tuple(effective),window.complete,
            'synthetic',SOURCE_CONTRACT,source_evidence=source_evidence)
