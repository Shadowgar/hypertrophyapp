"""Offline C2 review contracts. No trusted approval or activation capability."""
from dataclasses import dataclass
from typing import Literal

from .models import PlanPreview, SciencePolicy


@dataclass(frozen=True)
class ProgramSlot:
    action: str
    emphasized: bool = False
    variant_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SessionDesign:
    key: str
    slots: tuple[ProgramSlot, ...]


@dataclass(frozen=True)
class PilotDesign:
    version: str
    sessions: tuple[SessionDesign, ...]
    desired_actions: tuple[str, ...]
    desired_regions: tuple[str, ...]


@dataclass(frozen=True)
class DirectRegionBand:
    region: str
    minimum: int
    maximum: int


@dataclass(frozen=True)
class PilotStandard:
    version: str
    science: SciencePolicy
    direct_region_bands: tuple[DirectRegionBand, ...]
    review_status: Literal["review_required"]
    scientific_reviewer: str | None
    owner_approval: str | None


@dataclass(frozen=True)
class CoverageOmission:
    kind: Literal["action", "region", "dose"]
    name: str
    reason: str
    confirmation_reference: str


@dataclass(frozen=True)
class RegionTotals:
    region: str
    primary_sets: int
    secondary_sets: int
    unknown_sets: int


@dataclass(frozen=True)
class PilotPreview:
    plan: PlanPreview
    coverage_status: str
    missing_actions: tuple[str, ...]
    missing_regions: tuple[str, ...]
    region_totals: tuple[RegionTotals, ...]
    dose_conflicts: tuple[str, ...]
    standard_hash: str
    design_hash: str
    accepted_omissions: tuple[CoverageOmission, ...]
