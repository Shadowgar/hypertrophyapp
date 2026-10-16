# Customized C3A preview and future policy admission

Status: implemented **isolated, nonproduction C3A seam**, not production wiring, qualified training science or release acceptance. Authorized by [Issue #89](https://github.com/Shadowgar/hypertrophyapp/issues/89). Stack: corrected [C2 #88](https://github.com/Shadowgar/hypertrophyapp/pull/88), then [C1 #86](https://github.com/Shadowgar/hypertrophyapp/pull/86). Existing product/consent/profile/load/metadata/date contracts remain controlling; no Proposed ADR is silently accepted.

## Actual owners and flow

| Owner | Inputs → outputs / scope |
|---|---|
| `app.customized_preview_http.create_preview_app` | Explicit server configuration, authentication port and schedule-context port → two read-only POST routes. Factory is never mounted/imported by production `main.py`. No startup/DDL/database dependency. |
| `app.customized_preview_service.preview_program` | Strict preview request + server principal/capability + exact typed context → `PreviewResponse`; no writer or activation capability. |
| Existing `build_generated_training_profile` | Request controls → existing normalized `GeneratedTrainingProfile`, retained for compatibility/trace. No existing source constructor, scaffold or generation router is invoked. |
| C3A explicit profile mapping | Explicit consent, recency, skill, equipment, dates, cap and supported restrictions → C1 `CustomizedProfile`; raw answers never reach the core. |
| `core_engine.customized.pilot.plan_pilot` | Explicit server-owned synthetic catalog, policy and original design + normalized profile/context → C2 original sessions, timing/coverage/calibration and replay trace. |
| `core_engine.customized.admission.admit_policy` | Requested ID + immutable server registry + typed audience + explicit clock → future admission or fail-closed denial. No approved policy/authority keys ship. |
| `app.customized_preview_view` | The same response facts → escaped consumer-readable HTML; no new scientific policy or causal explanations. |

The route is an **equivalent isolated demonstration adapter**, not an extra production router. `/customized/preview` returns JSON; `/customized/preview/render` returns HTML. POST is used to keep profile controls out of URLs; it performs no persistence. There is no Activate, Start, plan-save or set-log endpoint. No existing Authored, history/undo, scheduling, account authentication or database module is modified.

## Access and audience contract

Default `PreviewServer()` has `enabled=False`, production environment, no synthetic access, no subjects/bundles/authorities/approved entries. Environment and flags are server-owned typed configuration, never request fields. The HTTP middleware rejects disabled or production hosts with 404 before invoking authentication, context or planning, even if someone sets enabled=true in production. It bounds actual request bytes to 16 KiB and returns secret-free validation errors. JSON/HTML use no-store, restrictive CSP, no-referrer and nosniff headers.

An enabled test/staging host must supply an authenticator returning `PreviewPrincipal`; absent authentication is 401, absent scope `customized:preview` or allowlisted subject is 403. C3A supplies no new JWT/login scheme. Production's existing database-backed `get_current_user` is not imported merely for a synthetic demonstration. Binding a real account/capability resolver and its lifecycle/ownership controls belongs to C3B qualification, not a client-selectable port.

`synthetic_review_preview` additionally requires server `synthetic_enabled=True` and an exact unique server bundle ID. Each bundle must remain provisional/review-required and cannot carry a claimed approval. The client cannot upload policy, catalog, inventory, reviewer, root, signature or server environment/flag. C2 fixtures are imported only by the uninstalled `research/m4c3a` developer entrypoint; application modules import none of them.

`approved_prescription` resolves the requested ID against the server registry; missing/unapproved records return **409 policy_not_approved with no sessions**, without falling back to a synthetic bundle. Even a fully endorsed isolated positive-control record returns **activation_disabled with no sessions**. All responses enforce `can_activate=False`, `prescriptive=False`, and `effectiveness=not_established`. Audience labels distinguish review from future approved authority; a label never grants permission.

## Normalized profile: active vs trace-only

Active C3A fields are explicit mode/consent, hypertrophy goal, new/returning/current training context, three actual date-only dates, timezone, exact hard/flexible cap, supplied equipment, separately confirmed skill, movement restriction tags, variant preferences/exclusions/support preference and explicit omission receipts. Origins distinguish supplied fields from missing optional controls; an omitted preference/exclusion is not falsely labeled an explicit user answer. No implied legacy consent is persisted.

Missing training context or skill abstains. Missing/null movement restrictions are **unknown** and request clarification; an explicit empty list means “reported none,” not medical clearance. Unsupported action/health restrictions explain that no qualified mapping exists. Exact `avoid_<action>` tags are the limited supported vocabulary, not clinical diagnosis or automated translation of all legacy restrictions. Missing equipment stays empty/unavailable; no full-gym pool, bench, machine identity, ROM or load is invented. The broadly-healthy-adult population field is an explicit scope declaration, not a screening/clearance result.

Existing normalization also derives recovery, generated mode, coarse equipment/time/status, weak points, starting RIR, volume/rep bands, physiology and anthropometry defaults. **Those do not set C3A doses, skill, recency, inventory or clearance.** The response identifies them as trace-only/ignored legacy defaults. Exact C1 profile fields and the separately injected C2 standard own this simulation. The fixed original designs are named comparisons, not adaptive topology/volume or expected-hypertrophy-per-minute optimization.

A server-supplied `PlanningContext` port provides explicit planning instant, local week and optional neighbor dates. Missing context abstains. C1/C2 validate chosen dates/timezone; no route moves/skips a date, writes a placement revision or assumes known cross-week recovery. The app never reads server today inside the core. #83 date persistence/two-week context remains separate.

## Future trusted science-policy registry

`TrustedPolicyRegistry` holds frozen tuples of versioned `PolicyRecord`, `ApprovalAuthority`, source pins and metadata/inventory evidence pins. Registry construction is a trusted server/build operation, not an HTTP payload or arbitrary client manifest loader. There is no approval upload/signing endpoint. No keys or non-test approved records are included.

A record binds numerical `SciencePolicy`, complete catalog including exact inventory/ROM/setup, original design hash, status/revision, bounded goal/training/population audience, validity window and metadata/inventory evidence references. Both science and owner endorsements sign a domain-separated canonical digest of the **complete record** (endorsements excluded from that digest). Each endorsement includes authority, role, pinned evidence reference, digest, issue/expiry and HMAC-SHA256 signature. Distinct trusted IDs and keys, enabled/current authority records, correct role and pinned evidence, constant-time signature comparison and exact valid time windows are required. A local C1 approval hash or invented coach name cannot substitute for either endorsement.

Resolution additionally rejects unknown/duplicate IDs, unapproved policy/status, absent/unpinned sources, unqualified exercise metadata, synthetic/unverified inventory attestations and missing equipment/ROM/setup/load information. Source pins match exact `(reference, version, sha256)` entries; **they do not fetch or independently certify remote source bytes**. Signed catalog/qualification/inventory content and evidence pins establish the declared upstream trust chain. They cannot prove anatomy, licenses, professional credentials or a person's real physical equipment by software alone.

HMAC authenticates server-provisioned authority secrets; it does not establish that a named human is qualified, and a privileged host controlling both keys is trusted. Actual authority assignment, evidence inspection/retention, secure key provisioning/rotation/revocation and approval workflow must be established before C3B. Positive tests use explicitly fake local authorities and fabricated qualification attestations solely to test the future gate; they are never runtime records. The empty default registry admits nothing.

## Preview meaning and limitations

Coverage means nominal declared action/region presence and local candidate bands, **not optimal hypertrophy or equal gains**. The longer gym example retains 45 working sets/week and upper estimates 69/70.5/69 minutes; hard 60 fails. The shorter comparator has 33 sets, upper estimates 57.5/59/57.5, unchanged rest/warmup/setup/transition assumptions and six unmet original direct-work floors. Without explicit dose-omission receipts it remains infeasible; acceptance yields a limited nonprescriptive comparison. Both hard-45 cases fail. [Full C2 comparison](../research/m4c2/example-week.md#review-correction-shorter-original-gym-comparator).

HTML displays targets separately from actual qualifying observed effort; unknown remains unknown. No starting weight is guessed from 1RM/e1RM. Actual comparison/calibration remains C1-owned; the renderer preserves status and reasons, including pain, stale evidence and unsupported load semantics. Pain/technique admission checks do not validate an injury-risk model or justify mandatory failure tests. The preview exposes every timing/coverage tradeoff and primary/secondary/unknown ledger separately; no fractional secondary credit or frozen metadata scoring is activated.

## Only C3B activation decisions

1. Assign/verify scientific reviewer authority and owner approval, accept/revise the bounded population and exact numerical policy/effort/calibration rules, and provision the matching signed registry/evidence chain. No universal optimum is claimed.
2. Qualify real exercise descriptions/anatomical/ROM/skill/restriction metadata and actual equipment/load inventories with provenance; choose explicitly accepted short/long workload tradeoffs. Synthetic C2 catalog/inventories cannot be promoted by changing a boolean.
3. Integrate real account-owned consent and immutable plan/revision/occurrence lifecycle, with any separately authorized schema/migration and preserved Authored/history behavior; approve actual activation permissions and rollback boundaries.
4. After #83, qualify selected-date persistence, stale revision handling, started/completed preservation and two-week neighbor/carryover context. C3A's typed port is not that implementation.
5. Qualify the real auth/capability binding, security/release evidence and manual desktop/mobile real-device consent/activation walkthrough. Current synthetic software/browser results do not qualify a live release or physiological effectiveness.

C4 response optimization and Military/Hybrid remain separate; they are not prerequisites to reviewing this bounded C3B pilot.
