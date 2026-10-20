# Independent exercise variant ontology — C2

**CANDIDATE FOR EXPERT REVIEW / NONPRESCRIPTIVE.** Engineering/source-consistency qualified; anatomical, technique and real equipment qualification **pending**. Every exercise retains `metadata_qualified=False`. No ranking or frozen metadata-v2 scoring is activated.

## Interpretation and admission limits

Each row is an original local description anchored to a public exercise source. Source matching confirms a descriptive movement anchor, not optimality, safety, clinical eligibility or exact muscle contributions. All primary/secondary assignments are proposed anatomical interpretations, including rows whose movement itself matches a source. `source_anchor_plus_declared_variant_inference_review_required` additionally identifies an adapted variant; it is not represented as independently studied.

`review_catalog` rejects mismatched content/action/source hashes. Its whitelist and local hash provide consistency, not secure admission or reviewer authentication: someone controlling the record can rehash it. `SourceRef.sha256` binds the original local descriptive metadata with sources omitted, URL, action, description and qualification; it is **not a hash of remote page bytes**. No source page or paid program table is copied. Source descriptions and bibliography were read, not a new licensing or physiology audit.

Every exercise requires its implement **and floor space**. Named stations and bench must be supplied explicitly. Supply/setup ranges are synthetic: 30–60 seconds per exercise; 60–120 seconds transitions are separately injected by the candidate standard. Ordinary work takes 45–60 seconds per set; single-arm supported row takes 90–130 seconds for **both sides and side change**. These estimates require human observation before real use.

The finite synthetic external-load inventory is 2, 4, 6, 8, 10, 15, 20, 25, 30 kg in the exact recorded basis. It is not a verified gym inventory or an increment recommendation; a large next step is informational only. Machine stacks use distinct synthetic equipment identities, never equivalent kg across machines. Bodyweight crunch has no external inventory and external-load calibration is unsupported.

Restrictions currently map explicit action avoidance (`avoid_<action>`); unmapped health restrictions abstain. Support preference is separate from skill. Every row has unknown `regional_distribution_unquantified`: no numerical muscle-head partition, secondary-to-direct multiplier or biological dose is calculated.

## Variant inventory

| ID / original name | Action | Required supply besides floor | Primary regions | Secondary involvement | Skill / load basis | Public anchor; variant inference |
|---|---|---|---|---|---|---|
| `gym_leg_press` / Seated leg press | knee_extension | machine, leg_press_station | quadriceps, glutes | hamstrings | basic / machine_stack | [source](https://www.nasm.org/resource-center/exercise-library/leg-press); movement description checked; human review pending |
| `gym_chest_press` / Seated chest press | horizontal_press | machine, chest_press_station | chest | triceps, anterior_deltoid | basic / machine_stack | [source](https://www.acefitness.org/resources/everyone/exercise-library/188/seated-chest-press/); movement description checked; human review pending |
| `gym_high_row` / Chest-supported machine row | horizontal_pull | machine, row_station | upper_back | lats, elbow_flexors, posterior_deltoid | basic / machine_stack | [source](https://www.acefitness.org/resources/everyone/exercise-library/169/seated-high-back-rows/); movement description checked; human review pending |
| `gym_leg_curl` / Seated leg curl | knee_flexion | machine, leg_curl_station | hamstrings | calves | basic / machine_stack | [source](https://www.nasm.org/resource-center/exercise-library/seated-leg-curl); movement description checked; human review pending |
| `gym_pulldown` / Seated front lat pulldown | vertical_pull | machine, pulldown_station | lats | upper_back, elbow_flexors | basic / machine_stack | [source](https://www.acefitness.org/resources/everyone/exercise-library/158/seated-lat-pulldown/); movement description checked; human review pending |
| `gym_calf` / Machine calf raise | plantar_flexion | machine, calf_station | calves | none assigned | basic / machine_stack | [source](https://www.acefitness.org/resources/everyone/exercise-library/294/calf-raise/); movement description checked; human review pending |
| `db_goblet` / Dumbbell goblet squat | knee_extension | dumbbell | quadriceps, glutes | trunk, hamstrings | intermediate / total_external | [source](https://www.nasm.org/resource-center/exercise-library/goblet-squat); movement description checked; human review pending |
| `db_rdl` / Dumbbell Romanian deadlift | hip_extension | dumbbell | hamstrings, glutes | trunk | intermediate / per_hand | [source](https://www.nasm.org/resource-center/exercise-library/dumbbell-romanian-deadlift); movement description checked; human review pending |
| `db_floor_press` / Dumbbell floor press | horizontal_press | dumbbell | chest | triceps, anterior_deltoid | intermediate / per_hand | [source](https://www.acefitness.org/resources/everyone/exercise-library/19/chest-press/); adapted variant; review required |
| `db_bench_press` / Dumbbell bench press | horizontal_press | dumbbell, bench | chest | triceps, anterior_deltoid | intermediate / per_hand | [source](https://www.acefitness.org/resources/everyone/exercise-library/19/chest-press/); movement description checked; human review pending |
| `db_row` / Bilateral dumbbell bent row | horizontal_pull | dumbbell | upper_back, lats | elbow_flexors, posterior_deltoid, trunk | intermediate / per_hand | [source](https://www.acefitness.org/resources/everyone/exercise-library/126/single-arm-row/); adapted variant; review required |
| `db_supported_row` / Bench-supported single-arm row | horizontal_pull | dumbbell, bench | lats, upper_back | elbow_flexors, posterior_deltoid | intermediate / per_hand | [source](https://www.acefitness.org/resources/everyone/exercise-library/126/single-arm-row/); movement description checked; human review pending |
| `db_press` / Standing dumbbell shoulder press | vertical_press | dumbbell | anterior_deltoid | triceps, lateral_deltoid, trunk | intermediate / per_hand | [source](https://www.acefitness.org/certifiednews/images/article/pdfs/ACEShoulderStudy.pdf); movement description checked; human review pending |
| `db_lateral` / Bent-arm dumbbell lateral raise | shoulder_abduction | dumbbell | lateral_deltoid | none assigned | basic / per_hand | [source](https://www.acefitness.org/certifiednews/images/article/pdfs/ACEShoulderStudy.pdf); adapted variant; review required |
| `db_rear_fly` / Seated rear lateral raise | shoulder_horizontal_abduction | dumbbell, bench | posterior_deltoid | upper_back | basic / per_hand | [source](https://www.acefitness.org/certifiednews/images/article/pdfs/ACEShoulderStudy.pdf); movement description checked; human review pending |
| `db_rear_floor` / Standing bent-over reverse fly | shoulder_horizontal_abduction | dumbbell | posterior_deltoid | upper_back, trunk | intermediate / per_hand | [source](https://www.acefitness.org/resources/everyone/exercise-library/34/incline-reverse-fly/); adapted variant; review required |
| `db_curl` / Dumbbell hammer curl | elbow_flexion | dumbbell | elbow_flexors | none assigned | intermediate / per_hand | [source](https://www.acefitness.org/resources/everyone/exercise-library/10/hammer-curl/); movement description checked; human review pending |
| `db_triceps` / Two-hand dumbbell overhead extension | elbow_extension | dumbbell | triceps | trunk | intermediate / total_external | [source](https://www.acefitness.org/resources/everyone/exercise-library/74/triceps-extension/); movement description checked; human review pending |
| `db_calf` / Dumbbell calf raise from floor | plantar_flexion | dumbbell | calves | none assigned | intermediate / per_hand | [source](https://www.acefitness.org/resources/everyone/exercise-library/294/calf-raise/); adapted variant; review required |
| `floor_crunch` / Controlled floor crunch | trunk_flexion | bodyweight | trunk | none assigned | basic / bodyweight | [source](https://www.acefitness.org/resources/everyone/exercise-library/52/crunch/); movement description checked; human review pending |

## Exact ROM/setup identities

ROM and setup are comparison boundaries, not claims of a universally optimal joint angle. Changing machine, pad, grip, depth, stance, support or implement needs an appropriate new identity and calibration. Skill labels are proposed admission requirements; they are not inferred from a source marketing safety claim.

| Variant | ROM identity | Setup and original descriptive qualification |
|---|---|---|
| `gym_leg_press` | `recorded-controlled-knee-depth-v1` | seat/back/foot placement recorded. Seated guided knee/hip extension; preserve seat and depth, no hamstring knee-flexion credit. |
| `gym_chest_press` | `handles-at-chest-to-controlled-extension-v1` | recorded seat and grip. Seated backed horizontal press with fixed grip and chest-height handles. |
| `gym_high_row` | `extended-arms-to-controlled-high-row-v1` | chest pad, seat and high handle grip recorded. Chest pad supported bilateral high row; rear shoulder involvement separate from direct fly work. |
| `gym_leg_curl` | `controlled-knee-flexion-with-hip-fixed-v1` | seat, thigh restraint and ankle pad recorded. Seated resisted knee flexion with pelvis supported; exact machine lever remains distinct. |
| `gym_pulldown` | `overhead-to-front-upper-chest-v1` | thigh pad and pronated grip width recorded. Front-of-body vertical pull with supported thighs, no behind-neck variant pooling. |
| `gym_calf` | `controlled-ankle-range-on-fixed-platform-v1` | pad height, knee posture and platform recorded. Machine-resisted ankle plantar flexion; individual calf-region distribution unquantified. |
| `db_goblet` | `recorded-controlled-squat-depth-v1` | one dumbbell held at chest. One dumbbell in both hands; load is its total mass, not per hand. |
| `db_rdl` | `hip-hinge-with-recorded-depth-and-soft-knees-v1` | bilateral matched dumbbells, neutral grip. Bilateral dumbbell hip hinge; preserve knee posture and lumbar control; not a knee curl. |
| `db_floor_press` | `floor-limited-upper-arm-depth-v1` | supine floor, neutral grip, matched dumbbells. Explicit floor-limited adaptation of the dumbbell bench press; no inheritance of bench-press weight. |
| `db_bench_press` | `recorded-bench-press-depth-v1` | flat bench, neutral wrists, matched dumbbells. Flat-bench bilateral dumbbell press; a bench must actually be confirmed. |
| `db_row` | `recorded-hinge-and-elbow-travel-v1` | unsupported bilateral hinge, neutral grip. Bilateral unsupported adaptation of bench-supported row mechanics; different setup and timing, no automatic load transfer. |
| `db_supported_row` | `controlled-full-arm-row-v1` | one hand/knee on bench, both sides per set. One side at a time with bench support; one prescribed set includes both sides and the side change. |
| `db_press` | `shoulder-height-to-controlled-overhead-v1` | standing bilateral, no leg drive. Standing bilateral shoulder press; source supplies movement description, EMG rankings are not used. |
| `db_lateral` | `controlled-abduction-to-shoulder-height-v1` | standing fixed elbow bend, no swing. Bent-arm lateral raise action identified in the source; exact standing ROM/setup is an anatomical candidate for review. |
| `db_rear_fly` | `fixed-elbow-rear-lateral-arc-v1` | bench edge, torso supported on thighs. Seated supported torso, fixed-elbow outward arc; no claim of universal best rear-deltoid exercise. |
| `db_rear_floor` | `recorded-hinge-and-reverse-fly-arc-v1` | unsupported standing hinge, fixed elbow bend. Unsupported hinge adaptation of reverse-fly action; bench support is not assumed. |
| `db_curl` | `controlled-elbow-flexion-neutral-grip-v1` | standing bilateral matched dumbbells. Neutral-grip elbow flexion; biceps/brachialis/brachioradialis distribution not numerically inferred. |
| `db_triceps` | `controlled-overhead-elbow-flexion-extension-v1` | one secured dumbbell held with both hands. One dumbbell shared by two hands in an overhead elbow extension; total external load. |
| `db_calf` | `floor-limited-ankle-range-v1` | bilateral stance, matched dumbbells, no platform. Floor-based dumbbell adaptation of plantar flexion; reduced ankle range disclosed, no machine load transfer. |
| `floor_crunch` | `upper-back-curl-with-pelvis-supported-v1` | supine on floor, hands beside head, no added load. Controlled trunk flexion on the floor; external working-load calibration is unsupported. |

## Selection rationale and explicit limitations

The gym example confirms six separate machines, dumbbells, bench and floor, intermediate skill and explicit synthetic preferences for leg press, chest press, machine row, calf machine and seated rear raise. C1 selection filters equipment/restrictions/skill, honors supplied preference/support, then uses stable variant identity as a deterministic tie-break. That is not an efficacy ranking. Trace records disclose actual filtering/selection inputs; no unsupported causal superiority explanation is added.

A floor press is not the same ROM as a bench press; an unsupported row differs from its supported source anchor; a floor calf raise does not silently assume a platform. A hinge supplies hip extension and hamstring involvement but not knee flexion; a horizontal row does not become a vertical pull. The reduced dumbbell design must show missing actions and a hamstring dose shortfall, with explicit acceptance references before it can be called a limited candidate.

The ACE shoulder PDF describes movements in an acute EMG study of 16 men aged 18–30. This packet uses only movement identification, not EMG rank as chronic hypertrophy evidence. The other ACE/NASM instruction pages provide descriptive anchors, not trial evidence for every anatomical assignment. Floor/unsupported adaptations especially require professional review.

C3 must admit genuine supplied equipment/load inventory, precise individual ROM/setup and qualified metadata through a trusted boundary. This test catalog must never be installed as an approved runtime exercise inventory.
