# Current and proposed data model

Status: **Proposed additive design**, not a migration prescription. Current model facts were verified against the audited [models](../../apps/api/app/models.py); [audit registry](../evidence/README.md) supplies runtime limitations. Schema/identity mechanisms require ADR-005/009 acceptance and isolated rehearsal.

## Current persisted records

| Model | Persisted purpose and key limitation |
|---|---|
| User | UUID/string identity, unique email, password hash, selection/profile/raw onboarding, single equipment list and frequency preferences. No explicit consent mode, history of normalized profiles, auth version or weekly selected-date contract. |
| PasswordResetToken | User FK, unique token hash, expiry/used/created times; sequential single-use. No qualified atomic version revocation. |
| WorkoutPlan | User/week/split/phase and JSON payload; no immutable source/rule/version or stable occurrence relationship contract. |
| WorkoutSetLog | User, reused workout string, primary/performed exercise IDs, set index, reps, float weight, nullable RPE, set-kind/parent/technique and created time. No occurrence/prescription FK or retry identity. |
| WorkoutSessionState | Mutable counts, rep/load recommendations and JSON set history. Unique `(user_id, workout_id, exercise_id)` still collapses reused weeks and repeated exercise occurrences. |
| ExerciseState | Current working weight, per-set exposure/streak/fatigue and guidance; no user/exercise uniqueness, incomplete variant semantics, undo divergence. |
| CoachingRecommendation | Preview/application JSON, type/phase/action/status and applied time; not a complete typed user outcome ledger. |
| WeeklyCheckin / WeeklyReviewCycle | Dated adherence/body-weight/context and derived adjustments/summary. Repeated submissions lack a fully defined correction/cardinality contract. |
| SorenessEntry / BodyMeasurementEntry | Dated user observations and measurement units; useful context, not a qualified individual-response dataset. |

Current timestamps use naive UTC conventions and `weight` is an untyped float. Do not assume database timestamp type proves local timezone, or that all existing loads mean total kilograms. Absence of a unit field is uncertainty, not permission to reinterpret history.

## Proposed additive records and constraints

Use [domain terminology](domain-model.md). ProgramVersion binds immutable source/importer/artifact/rule hashes. PlanRevision snapshots normalized profile, mode/consent, prescription and date/timezone inputs. WorkoutOccurrence and ExerciseOccurrence add stable user-owned identities and explicit source-slot lineage. Retain source and performed variant separately, including substitution consent. Effective SetRecord retains original submissions and correction/void relationships through audited edits or append-only amendment rows; storage choice is not yet accepted.

Proposed uniqueness/integrity:

- Unique user/occurrence/command idempotency key with normalized payload digest; same retry returns original result, changed payload conflicts.
- An effective logical prescription set has one active record unless an explicit additional-attempt identity was requested. Technique children retain parent/type identity and do not become extra ordinary progression exposures.
- Workout/exercise occurrences belong to one user; plan/version/slot references must remain ownership-consistent. Two identical catalog exercises in one workout have different occurrence IDs.
- Projection/version writes are atomic with the effective record or recoverably marked for deterministic rebuild. Use reviewed locking/optimistic revisions; PostgreSQL must qualify concurrent behavior.
- LoadRecommendation and outcome records link effective evidence, rule/context version, feasible load and acceptance/decline/edit provenance. Correction invalidates dependent advice rather than silently retaining confidence.

Occurrence placement history can be a separate revision/link rather than rewriting original plan membership. Completed prescriptions and original dates remain reconstructible. An explicit cancellation/partial-closure record does not masquerade as full completion.

## Units, load and time

Record planned and performed reps/load/effort separately. Load needs numeric magnitude, unit (`kg`/`lb` or documented alternative), basis (total external, per-hand, per-side, machine-stack, added-bodyweight or assistance) and equipment/profile version. Less assistance can mean greater difficulty; do not compare it as ordinary added mass. Historical body mass and machine calibration may be unknown. Unit conversion does not prove exercise comparability.

Actual RPE/RIR remains nullable and distinct from source targets. Do not derive historical RPE from target or convert RIR through an unaccepted rule. Capture work/warm-up/technique kind, form/ROM/pain flags, performed timestamps and actual-rest semantics explicitly; missing timing yields unknown duration.

Use UTC instants for actions/observations plus separate local dates, IANA timezone and local week for scheduling. DST is resolved at the scheduling boundary. Log receipt time alone cannot prove a set’s performed time. Client time and server receipt time have different trust/uncertainty.

## Migration and owner decisions

Add fields/relations in bounded migrations after accepted contracts; do not prescribe a total schema rewrite. Audit synthetic legacy mapping and preserve unmapped records. Never fabricate slot/week identity, actual effort or units to fill required columns. Importer repairs create versioned artifacts; completed old prescriptions retain lineage and disclosed missing-source limitations.

Decisions still needed: audited-edit versus amendment storage, lock/revision strategy, legacy confidence policy, started-occurrence reschedule/carryover, unit semantics for existing loads, and retention/export access. SEC-S2 auth_version is separately proposed in [urgent plan](../plans/urgent-account-recovery.md); no history redesign blocks SEC-S1. Migration/runtime grants, backup and restore follow [ADR-009](../adr/0009-production-schema-and-data-authority.md).
