# Training Science Standard v1 — candidate decision matrix

**CANDIDATE FOR EXPERT REVIEW / NONPRESCRIPTIVE. Every numerical row below is `review_required`.** Professional reviewer **pending/unassigned**; scientific and owner approval **pending**. Exact values live in [science.py](../../../research/m4c2/science.py); none is a runtime default.

## Bounded population and missing inputs

Initial scope: broadly healthy consenting adults whose primary goal is hypertrophy and who can confirm equipment, skill, available time and three actual training dates. `new`, `returning` and `current` describe current training context, not age or a diagnosis. New means learning or without an established current routine; returning means previously trained but not reliably tolerating the former routine; current means a presently tolerated resistance-training routine. There is no validated inactivity-day cutoff: uncertain status requires clarification, not a hidden numerical assignment. The synthetic fixture confirms intermediate skill independently of status; a new/returning label does not grant hinge/overhead competence.

Youth, pregnancy/postpartum, rehabilitation, active injury/pain, major health restrictions and special clinical/athletic goals are outside this initial autonomous candidate. Appropriate qualified supervision/medical clearance and a separate accepted policy may be needed. No injury probability or personal recovery estimate is inferred. A caller with unknown status, unmapped restrictions, unconfirmed skill, unavailable inventory or insufficient scheduling information receives clarification/calibration/infeasibility, not invented doses or weights. These population exclusions are review requirements, not a completed medical screening interface.

## Source-specific evidence register

These summaries reuse M4-R B04–B07; selected metadata/abstract checks do not upgrade its recorded access level. Evidence confidence concerns applicability, not a numeric certainty score. Exact operating numbers remain local proposals.

| Key and article | Evidence/population | Applicable finding and important limit/conflict |
|---|---|---|
| V: Pelland 2026, [PMID 41343037](https://pubmed.ncbi.nlm.nih.gov/41343037/), DOI `10.1007/s40279-025-02344-w` | Meta-regression: 67 studies/2058 overall; hypertrophy subset 35 studies/220 effects/1032; mostly young, 79% men overall | Greater volume with diminishing returns; hypertrophy model explains 22.3% of variance. Fractional 0/0.5/1 indirect coding and four-set detection threshold are model conventions, not universal biology, personal minimum or guaranteed response. |
| A: ACSM 2026, [PMID 41843416](https://pubmed.ncbi.nlm.nih.gov/41843416/), DOI `10.1249/MSS.0000000000003897` | Overview of 137 reviews, >30,000 healthy adults; search through October 2024 | Higher-volume comparisons, including ≥10 weekly sets, support hypertrophy on average. They do not prove each muscle/person requires ten starting sets. This candidate's lower direct doses trade exposure for tolerability/time; maximal gain is unproven. |
| R: Singer 2024, [PMID 39205815](https://pubmed.ncbi.nlm.nih.gov/39205815/), DOI `10.3389/fspor.2024.1429789` | Rest meta-analysis, nine studies/19 measures | Some support for >60 seconds, uncertainty about additional benefit. Does not establish 90 seconds or three minutes as a universal optimum. |
| S: Ramos-Campo 2024, [PMID 38595233](https://pubmed.ncbi.nlm.nih.gov/38595233/), DOI `10.1519/JSC.0000000000004774` | Split vs Full Body, 14 studies/392 adults, volume equated | No clear pooled superiority. This permits an original schedule choice, not equivalence for every user or proof of three-day optimality. |
| F: Refalo 2024, [PMID 38393985](https://pubmed.ncbi.nlm.nih.gov/38393985/), DOI `10.1080/02640414.2024.2321021` | 18 trained adults, eight-week within-person lower-body study | Similar quadriceps growth at tested failure vs 2/1 RIR, more acute fatigue with failure. Small, local protocol; no universal failure ban. |
| H: Hermann 2025, [PMID 40249908](https://pubmed.ncbi.nlm.nih.gov/40249908/), DOI `10.1249/MSS.0000000000003728` | 42 trained adults, eight weeks, single-set nine-exercise twice-weekly protocol | Some modest local signals favor failure; preserve this conflict with F. Not evidence that all multiset sessions should reach failure. |
| N: Refalo 2023, [PMID 36334240](https://pubmed.ncbi.nlm.nih.gov/36334240/), DOI `10.1007/s40279-022-01784-y`; Ruple 2023, [PMID 37144554](https://pubmed.ncbi.nlm.nih.gov/37144554/), DOI `10.14814/phy2.15679` | Failure review: 15 studies, mixed definitions; Ruple: 19 experienced adults, short unsupervised 0–1 vs 4–6 RIR comparison | Definitions differ; Ruple's unclear difference and uncertainty cannot prove identical effects. Supports retaining conflicting/null studies rather than claiming a narrow proven RIR optimum. |
| P: Plotkin 2022, [PMID 36199287](https://pubmed.ncbi.nlm.nih.gov/36199287/), DOI `10.7717/peerj.14142` | 43 trained adults, eight weeks, lower-body reps vs load progression | Both can express progress. Limited duration/population; no requirement for calendar-driven load increases or a prescribed universal increment. |
| C: Vasconcelos 2026 arm [PMID 42784046](https://pubmed.ncbi.nlm.nih.gov/42784046/), DOI `10.3390/muscles5030061`; leg [PMID 42617172](https://pubmed.ncbi.nlm.nih.gov/42617172/), DOI `10.1519/JSC.0000000000005494`; bioelectric DOI `10.3390/app16178724` | Related reports from **one 19-person cohort** | Count once, not independent replications. Bioelectric signals are not direct muscle growth. Preserve M4-R uncertainty about dose/progression co-interventions. |
| D: 2025 four-arm study, DOI `10.47206/ijsc.v5i1.393` | 38 recruited men; all-failure arm stopped after three participants, six discomfort withdrawals across modified protocols | Tolerability warning with serious protocol limitations, not a calibrated injury probability or a clean efficacy comparison. |

## Proposed operating rules and value-free alternatives

“I” means executable offline fixture behavior; “R” means a review-only proposal, absent from the prescription engine. The alternatives apply when support/input/admission is insufficient; they do not imply accepted replacement numerical policy.

| Decision | Exact candidate operating range / implementation | Basis, confidence and limits | Value-free alternative |
|---|---|---|---|
| Starting dose by current context | I: new 1 set/slot (21/week); returning 1, with 2 on three emphasis anchors (24/week); current 2, with 3 on anchors (45/week) | V/A/S; exact tier split is pragmatic, low confidence for these exact counts; no direct trial of this original week | Clarify current workload/tolerance with reviewer; no numerical default for unknown status |
| Weekly direct region dose | I: table below, primary counts only; no per-secondary coefficient | V/A; lower trained-user bands deliberately prioritize time/starting tolerance; not optimality evidence | Show primary/secondary/unknown entries separately; withhold complete label if a floor/ceiling fails |
| Repetition/load | I: knee/hip extension and horizontal/vertical presses/pulls 8–12; knee flexion and elbow work 10–15; other accessories 12–20. Working load unknown until exercise-specific evidence/calibration. No %1RM | A/P; broad hypertrophy rationale, exact boundaries practical; fixed kg cannot follow from status alone | Observe comfortable technique and actual effort with qualified assistance; no fabricated max or initial weight |
| RIR, RPE and failure eligibility | I: new/returning target 3–4 RIR; current 1–3 RIR. Failure not required; no 0-RIR target. R: intentional failure testing excluded from this pilot pending explicit professional eligibility decision | F/H/N/D; uncertain RIR estimates, mixed local failure signals. Exact ranges not validated for this complete design | Record uncertain effort as unknown; no inferred `RPE = 10 − RIR`. Direct RPE10 reports can be stored by C1 but this C2 standard has no approved RPE prescription range |
| Rest | I: compound groups 120–180 s; accessories 60–90 s between working sets on the same exercise; no mandatory supersets | R/A; exact bounds practical. Longer rest and station waits can extend actual sessions | Wait for comfortable technical readiness; disclose duration uncertainty/review cap rather than trimming |
| Schedule/spacing | I: exactly three selected local dates; candidate minimum two local calendar days between sessions | S plus operating convention; not proof of 48 h biological recovery; neighboring-week context unknown is disclosed | Ask for dates/context; no automatic relocation, skipped session or new weekly volume |
| Warmup | I: 8–12 min total allocation; R: reserve roughly 3 min easy general movement, 2 min unweighted rehearsals, remaining 3–7 min comfortable exercise-specific ramps on first knee/push/pull patterns | A plus coaching convention; exact split not experimentally optimized or individually qualified. No source-owned ladder imported | Use qualified individualized preparation; withhold numerical ramp weights/reps until reviewed |
| Time accounting | I: work 45–60 s/set, unilateral row 90–130 s including both sides; setup 30–60 s/exercise, transition 60–120 s between exercises, margin 180–300 s/session | Synthetic engineering assumptions, no time-motion measurement; fixed work ranges include positioning and small preparation between attempts | Display the interval; hard cap requires upper bound to fit; no guarantee under crowding/coaching |
| Completed-evidence calibration | I: exact variant/equipment/ROM/setup/unit/basis/rep/effort target; finalized complete required work; actual load/reps/effort, acceptable technique and pain=false. Lookback ≤28 days; minimum one qualifying set only for a genuinely complete occurrence | M2A evidence semantics; ages/count are local proposals, not biological expiry laws. Partial ordinary sessions cannot masquerade as a new calibration occurrence | Recalibrate rather than invent/fill missing observations; unknown pain/form/effort cannot qualify |
| Rapid underchallenge review | I: every qualifying set reaches top reps and reports ≥5 RIR (C1 also supports direct RPE10 ≤5 for an explicitly matching RPE target); flag immediately and show next supplied attainable load as information, no forced increment | P plus operating heuristic; exact effort threshold low-confidence. No waiting several arbitrary weeks for an obviously easy qualified observation | Ask for a fresh comfortable technique/effort observation. Unknown grid/no higher load means no invented plate or suggested % |
| Optional strength information | I: credible exact-identity 1RM/e1RM ≤14 days, with method for e1RM, information only; no conversion to working load, no fabricated observations | Limited transfer and model uncertainty; age heuristic unvalidated | Skip max collection; use submaximal exercise-specific calibration |
| Longer-term progression | R only: review after two successive complete comparable exposures at top reps within target effort, then consider a supplied attainable load with fresh calibration. No fixed kg, %, weekly increase or volume escalation | P/V; two-exposure count is an unvalidated operational candidate, distinct from immediate underchallenge review | Human review of actual trend/technique/tolerance; no automatic prescription mutation (C4) |
| Optional deload evaluation | R only: review two successive comparable sessions of unwanted performance decline or persistent reported fatigue; consider approximately one week with 30–50% fewer working sets, rounded with reviewer judgment and no invented load percentage. Pain prompts assessment, not a presumed deload diagnosis | Sparse direct hypertrophy-deload evidence; these numbers are explicitly low-confidence proposals, not established safety/effectiveness rules | Human evaluation without a forced calendar deload or numeric reduction. No C2 deload executor |

All routine work remains submaximal by proposal. A person can accidentally reach failure despite an RIR target; record the observed effort, do not rewrite it to match the prescription or silently increase work. Optional failure/AMRAP trials, drop sets and extended techniques are not part of this initial week. RPE eligibility/ranges and supervision details remain a concrete reviewer decision, not an implied alternative encoded in the fixtures.

## Direct-region bands: candidate starting weekly work

Counts refer to this ontology's planned primary involvement, not measured physiological dose. One set may have two primary regions; summing columns does not count unique sets. Secondary involvement is retained separately and never silently multiplied by 0.5. The unknown regional-distribution field remains visible. Regional subdivisions (e.g. muscle heads/upper vs lower portions) are unquantified.

| Region | New | Returning | Current | Current gym example |
|---|---:|---:|---:|---:|
| Quadriceps | 3–5 | 3–6 | 6–9 | 7 |
| Glutes | 3–6 | 4–8 | 6–12 | 10 |
| Hamstrings | 3–5 | 3–6 | 5–9 | 7 |
| Chest | 2–4 | 2–5 | 4–8 | 5 |
| Upper back | 2–4 | 2–5 | 4–8 | 4 |
| Lats | 1–3 | 1–3 | 2–6 | 2 |
| Anterior deltoid | 1–3 | 1–3 | 2–4 | 2 |
| Lateral deltoid | 2–4 | 2–4 | 4–6 | 4 |
| Posterior deltoid | 1–3 | 1–3 | 2–4 | 2 |
| Elbow flexors | 1–3 | 1–3 | 2–4 | 2 |
| Triceps | 1–3 | 1–3 | 2–4 | 2 |
| Calves | 2–4 | 2–4 | 4–6 | 4 |
| Trunk | 2–4 | 2–4 | 4–6 | 4 |

These modest direct amounts, particularly lats/arms/deltoids, are **not** represented as the ≥10-set pooled high-volume condition or a scientifically proven minimum. Secondary involvement may contribute; its equivalent is unknown. The professional decision is whether this is an appropriate starting tradeoff or a more voluminous/longer alternative is necessary. Failure of a declared band is surfaced for explicit review, never repaired through invented credit.

## Signoff record and next decision

| Decision owner | Status | Required concrete review |
|---|---|---|
| Qualified strength/conditioning professional | Pending, unassigned | Population/contraindications, variant/anatomy/skill qualification, every exact numeric row, RIR/RPE/failure eligibility, realistic observed timings and tolerability |
| Repository owner | Pending | Accept/revise the bounded candidate, limited-equipment/time tradeoffs and versioned numbers after professional review; explicitly record what is accepted |
| C3 admission/integration owner | Deferred | Trusted approval registry, verified inventory/ROM/setup, schedule revision/carryover, appropriate API/UI/persistence qualification |
| Release owner | No release requested/approved | Separate decision after actual integration and outcome/acceptance evidence |

No more broad research is required to review this finite candidate. A reviewer can accept/revise/reject individual rows now; unresolved rows remain `review_required` with the stated abstention alternative. Passing tests establishes deterministic modeling, not physiological efficacy or permission to prescribe.
