"""Read-only C3B1 scheduling port; does not implement or import #83 routing.

The future adapter must resolve account-owned effective occurrences, revisions,
corrections and both adjacent weeks from authoritative scheduling state. Local
hashes and synthetic test receipts explicitly do not verify that source.
"""
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

from core_engine.customized.audit import canonical, content_hash
from core_engine.customized.models import PlanningContext
from .customized_lifecycle_models import LifecycleError


@dataclass(frozen=True)
class ScheduleOccurrence:
    occurrence_id: str
    local_date: date
    status: Literal["planned", "started", "completed", "cancelled", "partial"]
    mode: Literal["authored", "customized"]
    prescription_hash: str
    source_slot_ids: tuple[str, ...]


@dataclass(frozen=True)
class ScheduleSnapshot:
    subject: str
    timezone: str
    revision: str
    context: PlanningContext
    occurrences: tuple[ScheduleOccurrence, ...]
    complete: bool
    source_kind: Literal["synthetic", "unverified", "source_verified"]
    source_reference: str
    contract_version: str = "customized-schedule-port-c3b1-v1"
    source_evidence: str | None = None

    def document(self) -> dict:
        try:
            zone = ZoneInfo(self.timezone)
            week = self.context.week_start
            if (not self.subject or not self.revision or not self.source_reference or week.weekday()!=0
                    or self.context.planning_instant.tzinfo is None
                    or (self.context.planning_instant.astimezone(zone).date()-week).days not in range(7)):
                raise ValueError("Invalid schedule context")
            start, end = week-timedelta(days=7), week+timedelta(days=13)
            ids = [o.occurrence_id for o in self.occurrences]
            if len(ids)!=len(set(ids)) or any(not o.occurrence_id or not o.prescription_hash
                or not start<=o.local_date<=end for o in self.occurrences):
                raise ValueError("Invalid occurrence context")
        except (ValueError, KeyError):
            raise LifecycleError("invalid_schedule_context") from None
        result=canonical(self)
        result.update(window_start=start.isoformat(),window_end=end.isoformat())
        return result

    def planning_context(self) -> PlanningContext:
        """Pass known neighboring dates into C1; never shift selected local dates."""
        week=self.context.week_start
        previous=[o.local_date for o in self.occurrences if o.status!="cancelled" and o.local_date<week]
        following=[o.local_date for o in self.occurrences if o.status!="cancelled" and o.local_date>=week+timedelta(days=7)]
        if self.context.previous_training_date is not None:
            previous.append(self.context.previous_training_date)
        if self.context.next_training_date is not None:
            following.append(self.context.next_training_date)
        return replace(self.context, previous_training_date=max(previous,default=None), next_training_date=min(following,default=None))

    def freshness_hash(self) -> str:
        document=self.document()
        # Clock advances alone do not invalidate context. Exact planning instant
        # remains in the immutable proposal; source/effective revisions must match.
        document["context"].pop("planning_instant")
        return content_hash(document)


class SchedulePort(Protocol):
    def resolve(self, subject: str, timezone: str) -> ScheduleSnapshot | None: ...
