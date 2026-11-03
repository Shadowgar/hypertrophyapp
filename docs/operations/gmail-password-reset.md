# Gmail delivery for FERRAVIS password recovery

Owner decision, 2026-10-31: use personal Gmail SMTP. This replaces the proposed
self-hosted MTA and PR #135's operator/backup-code architecture. Base main and
production revision: `88bb339fc820e59973fc20666ea00423f43f73fa`, schema0027.
No new application sender, schema, recovery endpoint, mailbox service or VPS is
required. This reference PR does not authorize future production changes.

## Evidence and root cause

Read-only Pi feasibility found TCP/25 timeouts to Google and Microsoft exchangers,
no IPv4 PTR, and residential Xfinity restrictions. Public IPv4 and IPv6 exist;
static-IP assignment, CGNAT status and ISP PTR delegation were not established.
Cloudflare hosts authoritative DNS. The root domain publishes SPF `-all` and
strict reject DMARC. These records remain unchanged: sending as the personal
Gmail address uses Google's domain and authentication, with FERRAVIS as display
name. No custom-domain From address is fabricated.

The existing API already supports verified STARTTLS on587, generic reset-request
responses, hashed expiring single-use tokens, rate limits and credential-bound JWT
revocation. The earlier authentication-only test returned535; a fresh privately
entered Google app password succeeded with235. No login password was inspected.
This is an SMTP credential/configuration repair, not an application-auth rewrite.

Google requires 2-Step Verification for app passwords. Availability restrictions
and Gmail limits remain provider-controlled. A Google-account password change can
revoke its app passwords; changing the FERRAVIS password does not change Google.
The sender credential must remain private and revocable. An app password is not a
mail-send-only capability; protect the host and credential files accordingly.

## Configuration authority

The production API receives SMTP values from an older immutable activation
Compose override. Editing `.env` alone does not supersede them. Preserve historical
backups: add one protected, last SMTP override to the existing frozen Compose file
list instead. The approved repair changes only SMTP_PASSWORD and SMTP_FROM_NAME
in effective runtime configuration. The username and From address already match.

`infra/mail/compose.gmail.yml` is a fail-closed reference template with explicit
new variable names; it cannot silently inherit the old SMTP_PASSWORD. Load values
only from a protected private input, never command arguments, public environment
exports, screenshots, chat, Git or logs. Render an owner-only0600 override and
include its path/UID/mode/hash in the installed controller's configuration guard.
Do not point the running service at this checked-in template automatically.

The approved canonical credential source is the protected override referenced by
`~/.config/workoutapp-release/config.json`. Its current path is
`~/.local/state/ferravis-gmail-preparation/gmail-smtp-override.json`.
It is active configuration: do not remove it as disposable preparation output.
No credential values belong in this document. The inactive input and sanitized
receipts are protected separately; receipts never contain a password/reset token.

Before any credential rotation, independently verify the current API/container,
immutable image, revision, schema, PostgreSQL cluster/volume and guarded config.
Resolve the complete installed Compose file list in memory with explicit inputs.
Require exact parity except the approved SMTP keys; preserve API validate-only
startup and the direct-Node web command. Reconcile file hashes without changing
enabled/rollback flags, acquire the existing executor lock, and keep publishing
false and the timer disabled/inactive. Record the approved manifest digest.

Recreate only API using its already-qualified immutable image, with no build,
pull, web/PostgreSQL recreation, migration or reset. Verify API/web revision,
unchanged PostgreSQL identity/schema and all table fingerprints before sending.
A new Compose file list on API is truthful configuration provenance; do not forge
web's unchanged labels or recreate web merely to align those labels. The normal
executor uses the updated frozen manifest. Any bootstrap tooling assumption that
API/web label file lists match must be reviewed before future re-bootstrap.

## Accepted operation and verification boundaries

The owner separately approved plan
`f7d136c0233e04b342fa38c38abcaa0c92003feca80b40d083ec1762fa19686e`:
SMTP override/guard reconciliation, one API recreation at the same qualified
image, and one normal reset email to the privately verified preserved account.
All25 table fingerprints matched before the email. The sole subsequent table
change was normal PasswordResetToken state; account/training fingerprints remained
unchanged. Exactly one new hashed active token was present. No password was
changed by the agent, and all release controls remained disabled/inactive.

The first public health checker used Python's default user agent and received403
from Cloudflare. Local API health and ordinary public curl requests independently
returned the correct SHA. A minimal forward verification finished the same
approved email operation; no repeated recreation or second email occurred.
Preserve the initial failure evidence and final success receipt.

A generic200 or active token establishes application submission, not inbox arrival.
Owner confirmation of actual Inbox/Spam arrival, successful link/code use and a
fresh sign-in is separate acceptance evidence. Do not fetch or publish the email
body, token, reset URL or password. Do not send another message automatically.
The existing emailer has no SMTP debug output and sanitizes errors; keep reset
request bodies and full credential-bearing URLs out of application/access logs.
Existing query-token link compatibility is unchanged by this configuration PR.

## Exact end-to-end acceptance

1. Privately prepare a fresh Google app password; verify2-Step and sender identity.
   Stage it in an owner-only inactive file. Independently inspect effective config.
2. With appropriate authorization, make one certificate-verified AUTH-only test;
   record numeric status only, no MAIL/RCPT/DATA and no automatic retry.
3. Obtain separate exact-target approval for the rendered override, config-guard
   reconciliation and same-image API-only recreation. Verify all unchanged state.
4. Obtain explicit approval for a recipient and mail count. Use the normal Forgot
   Password endpoint once. Its generic response must disclose no reset credential.
5. Recipient confirms actual arrival and uses Gmail's Show original summary to
   verify SPF/DKIM/DMARC. Report only pass/fail, never full headers or message body.
   SMTP acceptance alone is not delivery qualification. Outlook requires its own
   explicitly approved test mailbox/message; it has not been qualified here.
6. Owner uses the normal reset screen, chooses their own password and signs in.
   Verify single-use/expiry and old-session rejection using isolated synthetic
   accounts, not repeated production resets. Verify original training/history is
   retained. No test workout, account deletion or database reset is permitted.

This PR carries no production secret, schema migration or automatic activation.
Issues #103/#105 remain open for physical iPhone/gym acceptance.

Primary references: [Google app passwords](https://support.google.com/accounts/answer/185833),
[Google SMTP](https://support.google.com/mail/answer/7104828),
[Xfinity port25](https://www.xfinity.com/support/articles/email-port-25-no-longer-supported),
[Tailscale exit nodes](https://tailscale.com/docs/features/exit-nodes).
