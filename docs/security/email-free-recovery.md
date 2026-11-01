# Email-free recovery implementation contract

Owner-approved bounded design: [design and scope](../superpowers/specs/2026-10-31-email-free-password-recovery-design.md).
Implementation base: `88bb339fc820e59973fc20666ea00423f43f73fa`. This PR is not
production issuance, migration, deployment or security acceptance.

## Authority and storage

`app.account_recovery` owns backup generation and both reset authorities;
`routers.auth` owns authenticated API binding and shared auth limits. The existing
User lock and password-hash-bound JWT CV remain the session authority. No auth
version or training state is introduced. `PasswordResetToken` remains the operator
and legacy-email authority. [Operator runbook](../operations/operator-account-recovery.md)
requires independent exact target binding and fresh one-time owner approval.

Migration `0028_account_recovery_codes` adds `account_recovery_codes` and
`account_security_events` only. No user, training or schema-state backfill occurs;
Alembic advances as expected. Backward API deployment needs an independently
reviewed migration/cutover; do not silently use bootstrap in production. The
existing automatic schema-change gate remains intact.

## API and lifecycle

- `GET /auth/recovery-codes`: owned count and last 50 security events; never hashes
  or plaintext. Authenticated security settings are the notification channel.
- `POST /auth/recovery-codes`: current JWT, current password, explicit confirmation
  and UUID command ID. User is locked and refreshed, JWT CV is revalidated under
  lock, previous unused codes revoked, ten independently random 256-bit codes
  generated and hashes/audit committed atomically. Only winning initial response
  contains plaintext; same command retry returns `already_processed` and no codes.
  Lost response requires authenticated regeneration; there is no retrieval API.
- `POST /auth/password-reset/confirm`: same body/route as legacy. Resolve stored
  authority, lock User, conditional single-use claim and password/audit commit.
  One backup code consumes only itself; other nine remain usable. Either reset
  invalidates all short-lived reset tokens and prior JWT sessions. An operator or
  email reset also revokes permanent codes. Wrong/used/revoked/expired codes share
  the existing generic error. Email address alone never authorizes a reset.
- `POST /auth/recovery-events/{id}/acknowledge`: own event only; acknowledgment
  retains the audit row. Events contain no address, code, password or request body.

Setup/regeneration uses three attempts per account per fifteen minutes, sharing
existing global sixty-per-minute and four concurrent auth-work ceilings. Public
confirmation keeps five attempts per credential per minute and the same global
budget. Limits are process-local and reset on restart: multiple workers require
separately qualified shared limiting. This feature does not certify ingress,
XSS/session storage, host access, OS vulnerability remediation or email delivery.

## Browser and operating limits

Settings holds plaintext only in transient React state and clears it on dismissal,
unmount or auth/account change; POST response is `no-store`. No codes in browser
storage, URLs, analytics, application logs or screenshots. Local password managers
and operating-system clipboard/terminal recording remain outside application
control. Store saved codes privately outside FERRAVIS. Lost password and lost codes
require the trusted local operator; passkeys are a later separate design.

Forgot Password defaults to code/new-password entry. Legacy emailed token URLs and
the request API remain compatible, without presenting mail delivery as the normal
journey. Confirmation does not auto-login. Future deployment requires separate
owner authorization and migration/recovery qualification. Issues #103/#105 stay
open for real-device/gym acceptance; no production smoke writes belong in this PR.
