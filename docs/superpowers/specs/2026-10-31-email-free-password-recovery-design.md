# Email-free password recovery — bounded design

Status: proposed implementation design for the owner's explicit two-priority
assignment. Production issuance, migration, integration and deployment remain
unauthorized. Base: protected main `88bb339fc820e59973fc20666ea00423f43f73fa`.

## Intent and scope

Restore access without dependence on mail/SMS, preserving the existing account and
every training record. First deliver an operator-only utility usable with the
currently deployed 0027 API; then one reviewable PR for authenticated enrollment
of ten independent backup codes and the corresponding recovery journey.

No passkeys, public operator/admin API, runtime LLM, training-policy change,
production password/token issuance, reset, restart, deployment, release activation
or artifact cleanup belongs to this implementation assignment.

## Approach and migration decision

The immediate utility can reuse `PasswordResetToken` and the existing confirmation
endpoint with no application/schema deployment. The current confirmation handler
invalidates all outstanding short-lived tokens after resetting a password.
Reusing those rows for ten permanent codes would silently invalidate the other
nine. Putting security credentials into onboarding/preferences JSON would create
an inappropriate second authority.

Recommended permanent approach: two small dedicated tables, `account_recovery_codes`
and `account_security_events`, plus additive migration `0028_account_recovery_codes`.
Existing training tables and User credential/session representation are unchanged.
The alternative is to ship only the no-migration operator utility and defer the
permanent feature; existing schema has no suitable durable code/audit store.

The owner's final "no migration" restriction needs explicit clarification: this
design requests permission to **include migration 0028 in the unmerged PR and run
it only against verified disposable PostgreSQL**. No production migration runs.
If that scope is declined, the permanent runtime portion remains blocked rather
than overloading unrelated state.

## Priority 1: private local operator issuance

- A host-side CLI defaults to read-only preparation/dry run. No HTTP issuance
  endpoint is added. Issuance requires the authenticated operator UID, a private
  controlling terminal and explicit one-time approval bound to a protected target
  manifest. Refuse redirected/piped output and non-terminal execution.
- Bind the host identity/local Docker daemon, exact API/container/image/revision,
  PostgreSQL container/image/cluster/database/role/volume, schema, selected account
  identity and current credential/reset-state fingerprints. Recheck immediately
  before the transaction. Never choose an account from inherited environment or
  print an address/password hash.
- Execute a reviewed minimal worker through the existing verified API container,
  importing only the existing model/security helpers. No image installation,
  application source mount, container restart or new schema is needed.
- Lock the existing User row, recheck identity/credential state, mark older unused
  `PasswordResetToken` rows used, generate one existing 32-byte random token, hash
  it with `hash_password_reset_token`, and insert its ten-minute expiry in the
  same transaction. No password or training row is updated by issuance.
- Commit before displaying the plaintext once directly to the private terminal.
  No plaintext in arguments, environment, files, logs, audit, exceptions or chat.
  A display/transport failure after commit is uncertain issuance: stop, retain a
  secret-free receipt, and never replay/reprint automatically. A new issuance
  requires renewed approval and invalidates the previous outstanding token.
- The owner uses the deployed **Enter a reset code** screen. Existing
  `/auth/password-reset/confirm` owns password change, atomic single use and
  credential-bound session revocation. The assistant never issues/displays a
  production code through a tool terminal or chat.

## Priority 2: permanent recovery lifecycle

Proposed defaults below are implementation calls for owner review, not claims of
existing approval.

1. **Enrollment/regeneration:** require current authenticated credentials, explicit
   confirmation and the current password. Lock/reload User and revalidate the
   presented JWT credential binding after acquiring the lock, including when a
   concurrent reset reused the same plaintext password but changed its salt.
2. Generate ten independent 256-bit random codes, grouped as one batch. Their
   domain-separated SHA-256 digests are indexed uniquely; high entropy makes
   guessing infeasible without a password-derived hash or JWT-key dependency.
   Codes remain usable until individually consumed or their batch is revoked.
   Never accept user-chosen recovery codes.
3. Generation revokes previous unused recovery codes atomically. A per-account
   command ID prevents duplicate/racing requests from issuing another batch.
   Plaintext is returned only by the winning initial response; a retry receives
   a non-secret already-processed result, never a replay of plaintext.
4. React holds the winning codes only in transient state, with no-store responses
   and explicit saved/dismissed acknowledgment. Clear them on dismissal, unmount,
   logout or account change. Do not save them in browser storage, logs, URLs,
   telemetry or screenshots. An unreceived response requires authenticated
   regeneration rather than retrieving stored plaintext.
5. **Password recovery:** preserve the existing confirmation endpoint/body and
   short-lived token flow. The server resolves either short-lived reset-token or
   permanent recovery-code authority, not email identity alone. It locks User,
   rechecks the selected code and consumes it conditionally in the same
   transaction as `hash_password(new_password)` and the audit event.
6. A permanent-code reset consumes only that code; the other nine remain valid.
   It invalidates all short-lived reset tokens and all prior JWT sessions through
   the existing credential binding. An operator/email-token reset additionally
   revokes existing permanent codes, so previously enrolled codes cannot silently
   survive that stronger recovery action. No automatic new codes are disclosed.
7. All invalid, expired, used, revoked or wrong-account recovery inputs receive
   generic errors. Existing shared auth concurrency/global budgets apply, with
   explicit recovery and authenticated-generation limits. Do not bypass limits
   because SMTP is unavailable. Current single-process limiter limitations remain
   documented; no distributed-rate-limiter rewrite is included.
8. `account_security_events` records only owner, event type, time, optional
   generation command ID/batch identifier and acknowledgment time. It stores no
   code, password, request body or secret-derived recovery input. Generate/use/
   revoke events commit with the credential operation. Authenticated settings
   show a security notice after recovery; acknowledgment preserves the audit row.

## Browser journey and compatibility

Authenticated Settings gets one Security section: status/remaining count, current
password-confirmed setup/regeneration, one-time display and security notices.
No plaintext can be fetched later. Failed/stale requests never show another
account's codes.

Forgot Password defaults to entering a recovery or operator code plus a new
password, explaining that codes must have been saved or issued by the trusted
operator. An email address alone grants no recovery authority. Existing emailed
token URLs and the existing confirmation endpoint remain compatible. The legacy
email-request API is not removed until the alternative is qualified; the normal
journey no longer depends on it or promises an email.

## Qualification and deliverables

Use explicit synthetic-only disposable targets and cleared test environments
before any imports/startup/DDL. No restored owner data is used for feature tests.
Focused tests cover target/TTY/approval refusal, expired/stale issuance, display
failure, old-token revocation, real PostgreSQL two-winner races, replay, concurrent
generation/reset, account isolation, session revocation, rollback, secret-free
validation/logs, and unchanged training records. Rehearse additive 0027→0028 on
populated synthetic PostgreSQL only after migration-scope approval.

Browser checks cover desktop/mobile settings, reauthentication, one-time display,
duplicate/stale responses, regeneration, recovery, notification, account switch,
generic failure and legacy token entry. No production forms are submitted.
Run Codex Security review and normal final-head PR qualification; no repeated
local full suites or production builds/scans. Preserve compiler inputs and
licensed artifacts byte-for-byte.

Deliver the tested immediate procedure and exact separate production-issuance
approval, one focused unmerged PR with head SHA, evidence and limitations. Keep
Issues #103/#105 open. Local terminal privacy/recording cannot be proven by Python
isatty alone; the operator runbook must explicitly require an unrecorded private
terminal and prohibit tool/chat execution for live issuance.
