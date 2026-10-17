# Customized staging integration: C3B2A

**Implemented candidate, not release acceptance.** [Issue #94](https://github.com/Shadowgar/hypertrophyapp/issues/94) authorizes isolated account/session integration on corrected C3B1. The [bounded plan](../plans/m4-c3b2a-staging-integration.md) and [revision-specific evidence](../evidence/2026-10-17-m4-c3b2a-staging-integration.md) delimit the work. Existing [lifecycle ownership](customized-account-lifecycle.md), C1 planner and C3A admission remain the decision owners. No production router, User model, migration, Authored contract or workout writer changes.

## Account and session admission

`create_staging_app` is an unregistered factory, disabled by default. Its explicit bridge calls the existing `get_current_user` signature/expiry/current-User verifier. A valid application JWT alone grants no Customized capabilities. A separately provisioned server port must supply an enabled, time-bounded grant for the verified subject and exact authorization-header fingerprint, with the two required scopes and an entitlement reference. Client claims cannot mint these grants.

`StagingAccessGate` binds the actual account credential revision and immutable grant digest into the actor. Every service command checks the current grant and a fresh account credential revision before using cached command responses and again before committing. Password reset, missing account, grant revocation or changed grant revision deny the experimental boundary. The fresh credential port must bypass a request's cached ORM User. A reset during acceptance rolls back both the event and idempotency receipt in the disposable implementation.

This is **not application-wide session revocation**. No production entitlement/session repository or transactional credential/grant lock is installed. Future PostgreSQL admission must serialize credential/grant changes, calendar freshness and commit on the accepted account lock, closing the interval after the final read as well as validating a request. Synthetic grants and fixture tokens must never be provisioned into production.

## Consent protocol and audit

The staging boundary admits only `compact-candidate-consent-v2`. The single unchecked acknowledgement covers a readable comparison and identifies its exact plan version and summary hash. It expressly acknowledges an inactive candidate with unapproved science and uncertain estimates; it is not a scientific or medical approval.

The challenge and receipt bind subject, session, authorization revision, Customized mode, proposal ID, plan version, immutable snapshot, complete summary, complete audit terms, nonce and expiry. The server recomputes the summary; the client submits only the versioned hashes/challenge and strict `agree=true`. Wrong protocol, invented audit fields, stale revision/summary, expired/consumed challenge or changed schedule fail. Revision clears consent and requires a new acknowledgement. Decline and withdrawal remain separate actions. Replayed old commands return historical results only after current authorization and do not resurrect withdrawn current state.

The routine consumer flow has one checkbox. The backend still retains all **20** original individual terms, **12** exercise/date-specific set changes, **six unapproved proposed-range conflicts**, both full candidate/reference previews, timing phases/assumptions, alternatives and limitations. Legacy v1 receipts remain distinguishable; the legacy isolated factory is not silently converted or mounted in production.

## Workout comparison

The renderer uses stored planner responses, not its own prescription policy. It shows three selected local dates, timezone, daily and weekly sets, estimated duration ranges and the selected hard cap. Both directions retain expandable individual changes and the complete workout preview.

| Candidate | Sets/day | Sets/week | Estimated upper minutes/day | Hard 60-minute result |
|---|---|---|---|---|
| Longer original | 15 / 15 / 15 | 45 | 69 / 70.5 / 69 | Infeasible |
| Shorter gym alternative | 11 / 11 / 11 | 33 | 57.5 / 59 / 57.5 | Fits the provisional model only |

The shorter alternative removes 12 sets. Less scheduled work may reduce hypertrophy opportunity; no equal or optimal results are asserted. Six regions conflict with unapproved candidate ranges: lateral/posterior deltoid, elbow flexors, triceps, calves and trunk. Those ranges are not established biological minima. Setup, equipment access, rest, warm-up and transition estimates are synthetic and uncalibrated; actual sessions can exceed the cap. Hard 45 minutes remains infeasible; there is no automatic truncation. Alternatives are reviewing the longer candidate with a larger allowance, revising inputs/dates, or declining.

## Read-only calendar contract

`ReadOnlyCalendarAdapter` consumes a server-owned account/window envelope pinned to **PR #83 at `3f4927b3cdcca1e8655337b30b93894741bfca9c`**. It reads the preceding, selected and following week, retains local dates/IANA timezone across DST, stable occurrence/plan/source-slot identities, placement and effective-history revisions, status, void evidence and prescription hash. It selects the latest unambiguous placement, deduplicates identical rows and rejects contradictory equal revisions. Started, partial and completed work cannot become voided/planned or acquire a different date, mode, plan, prescription or source-slot identity. Voided planned entries leave evidence in the freshness envelope.

The adapter has no write operation. It never moves, stacks or replaces work. Known adjacent sessions constrain C1 spacing; unresolved retained work in the selected week blocks consent. Any source revision, undo/edit/void or envelope change invalidates the challenge; source row order alone does not. Foreign, incomplete-provenance and malformed envelopes fail closed where required. Missing overall source completeness remains an activation blocker.

**This port is qualified with synthetic shaped records only.** `source_kind` stays `synthetic`, even if the supplied envelope claims completeness. PR #83 remains open and unmerged. No accepted ORM join/current-next-week resolver/effective-history projection, source-verification admission or atomic shared-account calendar locking is supplied. Its files and production scheduling behavior are unchanged.

## Proposed additive PostgreSQL design and replay

This is a reviewable design, **not DDL or a migration**. Retain the existing `users` identity and all Authored/history/placement tables. Add only account-owned candidate lifecycle storage:

| Proposed relation | Minimum identity and retained content |
|---|---|
| Customized candidate | `subject` FK to existing User, stable proposal ID, current revision; account-scoped ownership on every query |
| Candidate event/revision | Unique `(subject, proposal_id, revision)`, event kind/time, expected prior revision, immutable document and content digest, request/profile/planner/policy/catalog/inventory pins, complete calendar envelope and comparison previews |
| Consent receipt | Account/proposal/version/snapshot, explicit consent protocol, summary/terms digests and complete audited terms/summary, session grant revision/fingerprint, nonce/issued/accepted time; immutable and linked to the event |
| Command receipt | Unique `(subject, idempotency_key)`, canonical command digest and exact historical response/event identity; mismatched reuse rejects |
| Explicit session entitlement | Account/session fingerprint, credential revision, scopes, validity, revocation/monotonic revision and provisioning authority; no JWT auto-grants |

Use one transaction with an account/grant locking protocol compatible with #83 and credential reset, then compare expected candidate revision and verified effective-calendar revision before append/current-pointer CAS/command receipt. Enforce ownership with parameterized account-qualified queries and reviewed database privileges; do not grant public candidate write access. Current-state replay must be deterministic from ordered immutable events and retain superseded consent/history. Retries must not restore an obsolete projection. Receipt/retention/account-erasure policy requires explicit privacy review; no cascade deletion of real workout history is proposed.

Before a migration exists: approve the schema/lock order, constraints, retention and backfill (prefer no inferred legacy consent), then rehearse empty install, existing-data compatibility, concurrent CAS/retry/reset/schedule changes, replay/hash equality, backup/restore and rollback against an explicitly disposable PostgreSQL database. No PostgreSQL binary or disposable instance was available for this task; SQLite success is not PostgreSQL qualification. Real activation later needs a separate explicit authorization and atomic workout admission transaction. It remains unimplemented and disabled here.
