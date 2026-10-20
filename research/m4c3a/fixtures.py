"""Explicit synthetic host setup. No real policy approval or user inventory."""
from app.customized_preview_models import (PreviewServer,PreviewPrincipal,PreviewRequest,SyntheticReviewBundle,OmissionRequest)
from research.m4c2.catalog import review_catalog
from research.m4c2.science import candidate_standard,shorter_gym_standard,gym_design
from research.m4c2.examples import synthetic_profile,explicit_context


def demo_context():
    return explicit_context()


def demo_principal():
    return PreviewPrincipal("synthetic-reviewer",("customized:preview",))


def demo_server():
    return PreviewServer(enabled=True,environment="test",synthetic_enabled=True,allowed_subjects=("synthetic-reviewer",),
        bundles=(SyntheticReviewBundle("longer-current",candidate_standard("current"),review_catalog(),gym_design(),display_name="Longer gym comparison"),
                 SyntheticReviewBundle("shorter-current",shorter_gym_standard(),review_catalog(),gym_design(),display_name="Shorter gym comparison")))


def demo_request(*,short=False,accept_tradeoffs=False):
    p=synthetic_profile(cap=60,cap_kind="hard")
    regions=("lateral_deltoid","posterior_deltoid","elbow_flexors","triceps","calves","trunk")
    omissions=tuple(OmissionRequest(kind="dose",name=r,reason="Explicit synthetic choice of less direct accessory work to fit time",confirmation_reference="synthetic-review-tradeoff") for r in regions) if accept_tradeoffs else ()
    return PreviewRequest(audience="synthetic_review_preview",bundle_id="shorter-current" if short else "longer-current",
        mode="customized",consent=True,consent_reference="synthetic-preview-consent",goal="hypertrophy",
        training_context="current",population="broadly_healthy_adult",selected_dates=p.selected_dates,timezone=p.timezone,
        cap_minutes=60,cap_kind="hard",equipment=p.confirmed_equipment,skill=p.max_skill,restrictions=p.restrictions,
        preferred_variants=p.preferred_variants,preferred_stability=p.preferred_stability,omissions=omissions)
