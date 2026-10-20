"""PROVISIONAL versioned policies for the original Customized pilot.

Runtime admission is controlled by the application host. These exact
choices are not physiological optima or evidence of professional approval.
See docs/research/m4c2/training-science-standard-v1.md for every decision.
"""
from core_engine.customized.audit import content_hash
from core_engine.customized.models import ActionDose, DurationRange, CalibrationPolicy, SciencePolicy, SourceRef
from core_engine.customized.pilot import ACTIONS, REGIONS
from core_engine.customized.pilot_models import PilotStandard, DirectRegionBand, PilotDesign, SessionDesign, ProgramSlot


EVIDENCE = tuple(SourceRef(f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", "c2-original-decision-summary-v1",
    content_hash((pmid, meaning))) for pmid, meaning in (
        ("41343037", "Volume matters with diminishing returns; fractional modeling is not a universal biological coefficient."),
        ("41843416", "Healthy-adult overview; population-level volume comparisons do not fix personal starting doses."),
        ("39205815", "Rest synthesis supports avoiding excessively short recovery, not an exact optimum."),
        ("38595233", "No universal volume-equated split advantage established."),
        ("38393985", "Small trained-limb trial supports a nonfailure option under its tested conditions."),
        ("40249908", "Single-set failure trial has modest local signals; conflicting nuance retained."),
        ("36199287", "Rep or load progression can express performance progress; calendar-forced increases not required."),
    ))


def candidate_standard(training_status):
    if training_status not in {"new", "returning", "current"}:
        raise ValueError("Unknown training status: obtain current training context; no numerical default")
    base, focus, rir = {"new": (1, 1, (3, 4)), "returning": (1, 2, (3, 4)), "current": (2, 3, (1, 3))}[training_status]
    compounds = {"knee_extension", "hip_extension", "horizontal_press", "horizontal_pull", "vertical_press", "vertical_pull"}
    doses = []
    for action in ACTIONS:
        low, high = (8, 12) if action in compounds else (10, 15) if action in {"knee_flexion", "elbow_flexion", "elbow_extension"} else (12, 20)
        rest = DurationRange(120, 180) if action in compounds else DurationRange(60, 90)
        doses.append(ActionDose(action, base, focus if action in compounds else base, low, high, "rir", *rir, rest))
    science = SciencePolicy(f"tss-v1-{training_status}-candidate-2026-10-16", "provisional", "hypertrophy", training_status,
        tuple(doses), DurationRange(480, 720), DurationRange(60, 120), DurationRange(180, 300), 2,
        CalibrationPolicy(28, 14, 1, 5, 5), EVIDENCE, None)
    # Bands are direct planned work under THIS ontology, not weighted biological
    # dose or thresholds derived from pooled fractional-set models.
    proposed = {
        "current": {"quadriceps": (6, 9), "glutes": (6, 12), "hamstrings": (5, 9), "chest": (4, 8),
            "upper_back": (4, 8), "lats": (2, 6), "anterior_deltoid": (2, 4), "lateral_deltoid": (4, 6),
            "posterior_deltoid": (2, 4), "elbow_flexors": (2, 4), "triceps": (2, 4), "calves": (4, 6), "trunk": (4, 6)},
        "returning": {"quadriceps": (3, 6), "glutes": (4, 8), "hamstrings": (3, 6), "chest": (2, 5),
            "upper_back": (2, 5), "lats": (1, 3), "anterior_deltoid": (1, 3), "lateral_deltoid": (2, 4),
            "posterior_deltoid": (1, 3), "elbow_flexors": (1, 3), "triceps": (1, 3), "calves": (2, 4), "trunk": (2, 4)},
        "new": {"quadriceps": (3, 5), "glutes": (3, 6), "hamstrings": (3, 5), "chest": (2, 4),
            "upper_back": (2, 4), "lats": (1, 3), "anterior_deltoid": (1, 3), "lateral_deltoid": (2, 4),
            "posterior_deltoid": (1, 3), "elbow_flexors": (1, 3), "triceps": (1, 3), "calves": (2, 4), "trunk": (2, 4)},
    }[training_status]
    return PilotStandard(f"training-science-standard-v1-{training_status}-review-required", science,
        tuple(DirectRegionBand(r, *proposed[r]) for r in REGIONS), "review_required", None, None)


def gym_design():
    def s(action, emphasis=False, *variants):
        return ProgramSlot(action, emphasis, variants)
    return PilotDesign("original-three-day-full-body-v1", (
        SessionDesign("A-knee-anchor", (s("knee_extension", True), s("horizontal_press"), s("horizontal_pull"),
            s("knee_flexion"), s("shoulder_abduction"), s("plantar_flexion"), s("trunk_flexion"))),
        SessionDesign("B-hinge-and-vertical", (s("hip_extension", True), s("vertical_pull"), s("vertical_press"),
            s("knee_extension"), s("elbow_flexion"), s("elbow_extension"), s("shoulder_horizontal_abduction"))),
        SessionDesign("C-press-anchor", (s("horizontal_press", True), s("knee_extension"), s("horizontal_pull"),
            s("knee_flexion"), s("shoulder_abduction"), s("plantar_flexion"), s("trunk_flexion"))),
    ), ACTIONS, REGIONS)


def dumbbell_design():
    """Explicit reduced-action option, never mislabeled as the complete gym week."""
    from dataclasses import replace
    design = gym_design()
    sessions = []
    for session in design.sessions:
        slots = []
        for slot in session.slots:
            if slot.action == "knee_flexion":
                continue
            if slot.action == "vertical_pull":
                slot = ProgramSlot("horizontal_pull")
            slots.append(slot)
        sessions.append(replace(session, slots=tuple(slots)))
    return replace(design, version="original-db-limited-option-v1", sessions=tuple(sessions))


def shorter_gym_standard():
    """Explicit time/dose comparator, not an equally effective optimization.

    Preserve bands so six reduced accessory doses fail their original floors.
    Callers must explicitly accept each visible dose tradeoff for a limited
    candidate; no acceptance, human qualification or activation is implicit.
    """
    from dataclasses import replace
    original = candidate_standard("current")
    two_set_actions = {"knee_extension", "hip_extension", "knee_flexion", "horizontal_press",
                       "horizontal_pull", "vertical_press", "vertical_pull"}
    doses = tuple(replace(d, sets=2 if d.action in two_set_actions else 1,
        emphasis_sets=2 if d.action in two_set_actions else 1) for d in original.science.doses)
    return replace(original, version="training-science-standard-v1-current-short-gym-review-required",
        science=replace(original.science, version="tss-v1-current-short-gym-candidate-2026-10-16", doses=doses))
