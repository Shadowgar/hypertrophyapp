"""Original descriptive exercise records, source checked; human review pending.

Source hashes bind the locally authored description/metadata, not remote HTML.
External sources establish movement anchors, never a universal efficacy ranking.
Inventories and duration ranges are synthetic scenarios, not a claim about a gym.
"""
from dataclasses import dataclass, replace

from core_engine.customized.audit import content_hash
from core_engine.customized.models import DurationRange, Exercise, ExerciseCatalog, LoadIdentity, SourceRef

ACE = "https://www.acefitness.org/resources/everyone/exercise-library/"
NASM = "https://www.nasm.org/resource-center/exercise-library/"
SHOULDER = "https://www.acefitness.org/certifiednews/images/article/pdfs/ACEShoulderStudy.pdf"


@dataclass(frozen=True)
class CheckedExercise:
    exercise: Exercise
    source_url: str
    source_action: str
    checked_description: str
    provenance_hash: str
    qualification: str


def _payload(record):
    return (replace(record.exercise, sources=()), record.source_url, record.source_action,
            record.checked_description, record.qualification)


def _record(key, name, action, implement, extra, basis, primary, secondary, rom, setup, skill, source,
            description, *, adaptation=False, work=(45, 60)):
    equipment_key = f"synthetic-{key}-equipment-v1"
    identity = LoadIdentity(key, implement, equipment_key, rom, setup, "kg", basis)
    e = Exercise(key, name, action, (implement, "floor", *extra),
        (f"avoid_{action}",), "supported" if implement == "machine" or "bench" in extra else "unsupported",
        skill, identity, () if basis == "bodyweight" else (2.0, 4.0, 6.0, 8.0, 10.0, 15.0, 20.0, 25.0, 30.0),
        primary, secondary, ("regional_distribution_unquantified",), DurationRange(30, 60), DurationRange(*work), (), False)
    qualification = "source_anchor_plus_declared_variant_inference_review_required" if adaptation else "source_description_checked_human_review_required"
    record = CheckedExercise(e, source, action, description, "", qualification)
    digest = content_hash(_payload(record))
    ref = SourceRef(source, "original-description-checked-2026-10-16", digest)
    return replace(record, exercise=replace(e, sources=(ref,)), provenance_hash=digest)


def catalog_records():
    return (
        _record("gym_leg_press", "Seated leg press", "knee_extension", "machine", ("leg_press_station",), "machine_stack",
            ("quadriceps", "glutes"), ("hamstrings",), "recorded-controlled-knee-depth-v1", "seat/back/foot placement recorded", "basic",
            NASM + "leg-press", "Seated guided knee/hip extension; preserve seat and depth, no hamstring knee-flexion credit."),
        _record("gym_chest_press", "Seated chest press", "horizontal_press", "machine", ("chest_press_station",), "machine_stack",
            ("chest",), ("triceps", "anterior_deltoid"), "handles-at-chest-to-controlled-extension-v1", "recorded seat and grip", "basic",
            ACE + "188/seated-chest-press/", "Seated backed horizontal press with fixed grip and chest-height handles."),
        _record("gym_high_row", "Chest-supported machine row", "horizontal_pull", "machine", ("row_station",), "machine_stack",
            ("upper_back",), ("lats", "elbow_flexors", "posterior_deltoid"), "extended-arms-to-controlled-high-row-v1", "chest pad, seat and high handle grip recorded", "basic",
            ACE + "169/seated-high-back-rows/", "Chest pad supported bilateral high row; rear shoulder involvement separate from direct fly work."),
        _record("gym_leg_curl", "Seated leg curl", "knee_flexion", "machine", ("leg_curl_station",), "machine_stack",
            ("hamstrings",), ("calves",), "controlled-knee-flexion-with-hip-fixed-v1", "seat, thigh restraint and ankle pad recorded", "basic",
            NASM + "seated-leg-curl", "Seated resisted knee flexion with pelvis supported; exact machine lever remains distinct."),
        _record("gym_pulldown", "Seated front lat pulldown", "vertical_pull", "machine", ("pulldown_station",), "machine_stack",
            ("lats",), ("upper_back", "elbow_flexors"), "overhead-to-front-upper-chest-v1", "thigh pad and pronated grip width recorded", "basic",
            ACE + "158/seated-lat-pulldown/", "Front-of-body vertical pull with supported thighs, no behind-neck variant pooling."),
        _record("gym_calf", "Machine calf raise", "plantar_flexion", "machine", ("calf_station",), "machine_stack",
            ("calves",), (), "controlled-ankle-range-on-fixed-platform-v1", "pad height, knee posture and platform recorded", "basic",
            ACE + "294/calf-raise/", "Machine-resisted ankle plantar flexion; individual calf-region distribution unquantified."),
        _record("db_goblet", "Dumbbell goblet squat", "knee_extension", "dumbbell", (), "total_external",
            ("quadriceps", "glutes"), ("trunk", "hamstrings"), "recorded-controlled-squat-depth-v1", "one dumbbell held at chest", "intermediate",
            NASM + "goblet-squat", "One dumbbell in both hands; load is its total mass, not per hand."),
        _record("db_rdl", "Dumbbell Romanian deadlift", "hip_extension", "dumbbell", (), "per_hand",
            ("hamstrings", "glutes"), ("trunk",), "hip-hinge-with-recorded-depth-and-soft-knees-v1", "bilateral matched dumbbells, neutral grip", "intermediate",
            NASM + "dumbbell-romanian-deadlift", "Bilateral dumbbell hip hinge; preserve knee posture and lumbar control; not a knee curl."),
        _record("db_floor_press", "Dumbbell floor press", "horizontal_press", "dumbbell", (), "per_hand",
            ("chest",), ("triceps", "anterior_deltoid"), "floor-limited-upper-arm-depth-v1", "supine floor, neutral grip, matched dumbbells", "intermediate",
            ACE + "19/chest-press/", "Explicit floor-limited adaptation of the dumbbell bench press; no inheritance of bench-press weight.", adaptation=True),
        _record("db_bench_press", "Dumbbell bench press", "horizontal_press", "dumbbell", ("bench",), "per_hand",
            ("chest",), ("triceps", "anterior_deltoid"), "recorded-bench-press-depth-v1", "flat bench, neutral wrists, matched dumbbells", "intermediate",
            ACE + "19/chest-press/", "Flat-bench bilateral dumbbell press; a bench must actually be confirmed."),
        _record("db_row", "Bilateral dumbbell bent row", "horizontal_pull", "dumbbell", (), "per_hand",
            ("upper_back", "lats"), ("elbow_flexors", "posterior_deltoid", "trunk"), "recorded-hinge-and-elbow-travel-v1", "unsupported bilateral hinge, neutral grip", "intermediate",
            ACE + "126/single-arm-row/", "Bilateral unsupported adaptation of bench-supported row mechanics; different setup and timing, no automatic load transfer.", adaptation=True),
        _record("db_supported_row", "Bench-supported single-arm row", "horizontal_pull", "dumbbell", ("bench",), "per_hand",
            ("lats", "upper_back"), ("elbow_flexors", "posterior_deltoid"), "controlled-full-arm-row-v1", "one hand/knee on bench, both sides per set", "intermediate",
            ACE + "126/single-arm-row/", "One side at a time with bench support; one prescribed set includes both sides and the side change.", work=(90, 130)),
        _record("db_press", "Standing dumbbell shoulder press", "vertical_press", "dumbbell", (), "per_hand",
            ("anterior_deltoid",), ("triceps", "lateral_deltoid", "trunk"), "shoulder-height-to-controlled-overhead-v1", "standing bilateral, no leg drive", "intermediate",
            SHOULDER, "Standing bilateral shoulder press; source supplies movement description, EMG rankings are not used."),
        _record("db_lateral", "Bent-arm dumbbell lateral raise", "shoulder_abduction", "dumbbell", (), "per_hand",
            ("lateral_deltoid",), (), "controlled-abduction-to-shoulder-height-v1", "standing fixed elbow bend, no swing", "basic",
            SHOULDER, "Bent-arm lateral raise action identified in the source; exact standing ROM/setup is an anatomical candidate for review.", adaptation=True),
        _record("db_rear_fly", "Seated rear lateral raise", "shoulder_horizontal_abduction", "dumbbell", ("bench",), "per_hand",
            ("posterior_deltoid",), ("upper_back",), "fixed-elbow-rear-lateral-arc-v1", "bench edge, torso supported on thighs", "basic",
            SHOULDER, "Seated supported torso, fixed-elbow outward arc; no claim of universal best rear-deltoid exercise."),
        _record("db_rear_floor", "Standing bent-over reverse fly", "shoulder_horizontal_abduction", "dumbbell", (), "per_hand",
            ("posterior_deltoid",), ("upper_back", "trunk"), "recorded-hinge-and-reverse-fly-arc-v1", "unsupported standing hinge, fixed elbow bend", "intermediate",
            ACE + "34/incline-reverse-fly/", "Unsupported hinge adaptation of reverse-fly action; bench support is not assumed.", adaptation=True),
        _record("db_curl", "Dumbbell hammer curl", "elbow_flexion", "dumbbell", (), "per_hand",
            ("elbow_flexors",), (), "controlled-elbow-flexion-neutral-grip-v1", "standing bilateral matched dumbbells", "intermediate",
            ACE + "10/hammer-curl/", "Neutral-grip elbow flexion; biceps/brachialis/brachioradialis distribution not numerically inferred."),
        _record("db_triceps", "Two-hand dumbbell overhead extension", "elbow_extension", "dumbbell", (), "total_external",
            ("triceps",), ("trunk",), "controlled-overhead-elbow-flexion-extension-v1", "one secured dumbbell held with both hands", "intermediate",
            ACE + "74/triceps-extension/", "One dumbbell shared by two hands in an overhead elbow extension; total external load."),
        _record("db_calf", "Dumbbell calf raise from floor", "plantar_flexion", "dumbbell", (), "per_hand",
            ("calves",), (), "floor-limited-ankle-range-v1", "bilateral stance, matched dumbbells, no platform", "intermediate",
            ACE + "294/calf-raise/", "Floor-based dumbbell adaptation of plantar flexion; reduced ankle range disclosed, no machine load transfer.", adaptation=True),
        _record("floor_crunch", "Controlled floor crunch", "trunk_flexion", "bodyweight", (), "bodyweight",
            ("trunk",), (), "upper-back-curl-with-pelvis-supported-v1", "supine on floor, hands beside head, no added load", "basic",
            ACE + "52/crunch/", "Controlled trunk flexion on the floor; external working-load calibration is unsupported."),
    )


def review_catalog(*, records=None):
    records = catalog_records() if records is None else records
    known_sources = {r.source_url for r in catalog_records()}
    for record in records:
        if (record.source_url not in known_sources or record.source_action != record.exercise.action
                or content_hash(_payload(record)) != record.provenance_hash
                or record.exercise.sources != (SourceRef(record.source_url, "original-description-checked-2026-10-16", record.provenance_hash),)):
            raise ValueError("Exercise content/action provenance mismatch")
    return ExerciseCatalog("c2-descriptive-catalog-v1-review-required", tuple(r.exercise for r in records),
        tuple(r.exercise.sources[0] for r in records))
