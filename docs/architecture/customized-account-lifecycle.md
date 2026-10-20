# Customized account-owned inactive candidate lifecycle

Status: implemented isolated C3B1 proposal under [Issue #92](https://github.com/Shadowgar/hypertrophyapp/issues/92), stacked on [C3A #90](https://github.com/Shadowgar/hypertrophyapp/pull/90). No production schema, route, migration, accepted science policy or release. [Product](../requirements/product-contract.md), [execution](../contracts/execution-plan.md), [dates](../contracts/selected-date-scheduling.md) and [C3A boundary](customized-preview.md) remain controlling.

## Owners and data flow

`customized_lifecycle.LifecycleService` owns account authorization, candidate revision and consent commands. C1/C2 own training decisions; `customized_preview_service.evaluate_preview` returns the existing C3A response plus typed internal evidence. The public `preview_program` interface and its decisions are preserved. No duplicate constructor, runtime LLM, metadata scoring or Authored adapter is introduced.

The snapshot contains the strict request with missing versus cleared input semantics, normalized C1 profile/origins, active versus trace-only controls, complete C2 plan and selections, versioned standard/design/catalog/source hashes and catalog payload, equipment/load semantics, comparable exposure assessments and effective receipts, optional strength reports, target versus observed effort, load calibration, every session/time phase/region ledger, exact dose gaps and complete declared reference comparison. It also retains the trusted scheduling port document, selected date-only local dates/timezone, explicit planning instant and source revision. The snapshot is serialized into independent JSON before storage. A content digest identifies it; that digest is **not scientific qualification or consent**.

The separate `customized_lifecycle_http.create_lifecycle_app` is not mounted or imported by production `main`. Default and production factories deny requests before authentication/storage. The host must explicitly supply a lifecycle service, allowed subjects, trusted identity dependency and browser origin. The optional `existing_account_dependency()` bridge uses the actual `deps.get_current_user` verifier and account lookup; it grants experimental capabilities only within the separately enforced server allowlist. Its session binding hashes the verified bearer credential; no raw bearer is persisted. This does not add revocation to the app's existing JWT lifecycle.

HTTP uses bearer authorization only, no cookie fallback/CORS; an existing Origin must exactly match the configured origin and cross-site Fetch requests are denied. Requests have the existing 16 KiB preparse limit, bounded fields, safe validation/auth errors, no-store/CSP/frame/nosniff/referrer headers. Account IDs, approval material and arbitrary omission/consent references are rejected from proposal commands. The shell contains no account data; credentials remain in memory. Account/input/action generations discard stale asynchronous responses, including already-committed responses from the old account. No sensitive telemetry is introduced.

## Identity, revisions and consent

A proposal has a server-generated account-owned `proposal_id`. `plan_version` advances only for a new immutable candidate snapshot; `revision` advances for each appended lifecycle event. Ownership is checked before object reads or commands; foreign and nonexistent objects both return `not_found`. No client actor or source occurrence identity can change that scope.

| State | Meaning |
|---|---|
| `previewed` | Stored exact candidate snapshot; not a physical workout. |
| `requires_information` | Existing planner needs explicit skill/restriction/training inputs. No invented clearance. |
| `review_required` | Candidate is reviewable; scientific approval and possibly feasibility remain unresolved. |
| `accepted_candidate` | Exact account/session action acknowledged the stored version and all terms. No active workout. |
| `activation_blocked` | Separate authorization assessment recorded blockers; never an execution state. |
| `declined` / `withdrawn` | Candidate choice declined or acceptance withdrawn; prior snapshots/receipts retained. |

Create and revise append `previewed` then the assessed state atomically. Revising clears current consent/challenge and retains all prior revisions. Decline/withdraw clear current acceptance without changing dates or performed history. GETs never mutate state. Authorization checks are explicit POST commands and append their own decision.

Consent preparation rechecks expected revision, exact snapshot digest, unchanged policy/catalog/reference/effective history and scheduling revision, elapsed local dates and candidate feasibility. It issues a random, expiring, one-use challenge bound to the authenticated session, subject, Customized mode, proposal/version and exact terms. Acceptance requires the nonce, expected revision, snapshot and terms hashes, strict explicit agreement, and the exact acknowledgement multiset. The transaction consumes the pending challenge and stores an account-owned receipt. Client references or hashes alone cannot perform this transition.

Every mutating command requires an account-scoped idempotency key and digest including session, operation, target/version and payload. Identical retries return the original historical result; changed payload/session conflicts. An original acceptance retry after withdrawal/decline **does not restore current consent**; read current state independently. Optimistic checks and event/receipt writes occur in one adapter transaction. Two distinct commands at the same revision have one winner.

## Workload and scheduling integrity

The existing long candidate remains 45 sets, upper estimates 69/70.5/69 minutes: hard60 fails. The short candidate is 33 sets, upper estimates 57.5/59/57.5: synthetic hard60 fits but six unapproved direct-dose gaps remain. Hard45 fails for both, without trimming.

For reduced-dose consent the host must provide one valid reference. All three dates, exercise identities, reps, effort and rest must match; only declared set reductions are compared. Missing, unknown, partial or incompatible comparisons fail closed. The current explicit pair produces 12 one-set reductions plus six exact primary-count/proposed-band acknowledgements and two general limitations (20 total). No shorter default, equivalent results or optimal hypertrophy claim follows. Core preview coverage remains incomplete when unapproved gaps exist, even after lifecycle acceptance.

`customized_lifecycle_schedule.SchedulePort` is versioned `customized-schedule-port-c3b1-v1`; it reads account/timezone-owned revision, explicit clock/week, full previous/current/next-week occurrence context, completeness and source references. It preserves source-slot IDs and prescription hashes, including started/completed/partial Authored work. Known adjacent dates pass to the existing planning context. Missing context stays unknown. Source kind `synthetic` or a local hash cannot become source verification.

The C1 context cannot represent an intervening retained same-week workout. C3B1 therefore blocks consent for **every retained noncancelled current-week occurrence** pending qualified source resolution, rather than silently excluding it or inventing another spacing algorithm. Exact protected-date collisions are also named. This conservative limitation includes unstarted planned occurrences; there is no implicit replacement, stacking, carryover, auto-advance or cancellation. #83's implementation files are unchanged. C3B2 must integrate/recheck accepted scheduling state atomically with activation; this read-only port is not that qualification.

## Persistence and activation boundary

`ProposalStore` exposes an atomic transaction port. Only `research/m4c3b1/store.py` implements it here: exclusively created, marked, 0600 SQLite files under an explicit task directory within `/tmp`, append-only event/retry inserts, no app ORM/reset/migration. Reopening the marked database preserves exact snapshots and receipts. SQLite serializes transactions across independent handles; it cannot qualify PostgreSQL grants, constraints or races. Full repeated snapshots are acceptable for this disposable adapter, not a proposed production retention/storage design.

The authorization result is distinct from planning and consent. It consults C3A admission and records missing independent professional qualification/independence, signed owner release decision, real qualified catalog/inventory/skill, source-verified scheduling, authentic consent and live lifecycle/release authority. **Eligibility and activation remain false even under simulated positive cryptographic admission.** This service ships no operational qualification mechanism or approved registry entries; it does not pretend to validate human credentials. There is no activation flag, workout writer, production route registration or Start Workout control.

The only C3B2 decisions are Issue #92 A/B/C: qualified science/owner acceptance of exact policies and reduced-work tradeoffs with retained evidence and authority operations; genuine variant/source/licensing/inventory/skill and measured timing qualification; owner-approved live lifecycle/schema/roles/session security, #83 date integration and explicit activation/rollback scope. Production auth/browser/DB/security qualification is then engineering evidence for that enabled scope, not evidence supplied by these synthetic tests. C4 adaptation and Military/Hybrid remain separate.
