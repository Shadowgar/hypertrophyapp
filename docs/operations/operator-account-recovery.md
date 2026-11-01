# Private operator account recovery (implementation; no live issuance approved)

Uses the existing 0027 PasswordResetToken and confirmation endpoint. No deployment,
SMTP, account deletion or schema migration is required. The user chooses their new
password in FERRAVIS; the operator must never request or inspect that password.

Run only from a private, unrecorded, authenticated terminal on the verified host
with local Docker access. Do not run issuance through Codex, chat, screen sharing,
terminal recording, shell tracing, CI, sudo logging sessions, or redirected pipes.
TTY checks cannot prove a terminal is not recorded. Codes must never be copied into
command arguments, history, files, logs, tickets or chat. They are bearer secrets.

1. Independently inspect the host, API image/container revision, PostgreSQL
   container/image/cluster/volume/schema/database/role and intended account. Do not
   print the address/hash. Supply a protected owner-only JSON target file with:
   `operator_uid`, `machine_sha256` (SHA256 of stripped /etc/machine-id),
   `api_container`, `api_image`, `db_container`, `db_image`, `revision`, `database`,
   `role`, `cluster`, `volume`, `schema`, `server_addresses` (sorted container IPs),
   `account_id`. IDs must be full, immutable values; no environment defaults.
2. `umask 077` and run `python3 scripts/operator_recovery.py prepare --target /private/target.json --manifest /private/recovery.json`.
   Type the exact login email at the hidden prompt. Only a protected comparison
   fingerprint is retained. Preparation is read-only and binds credential/reset
   state. It prints a nonsecret manifest SHA256.
3. Run `python3 scripts/operator_recovery.py verify --manifest /private/recovery.json`.
   Present the verified target identities and digest to the owner. **Stop here**
   until the owner separately approves this exact string:

   `ISSUE ONE FERRAVIS RECOVERY CODE <exact manifest SHA256>`

4. After approval, the operator runs `python3 scripts/operator_recovery.py issue --manifest /private/recovery.json` and enters the approved string at its hidden
   prompt. It rechecks host/API/database/volume/schema/account state, locks the
   User and atomically invalidates older reset tokens and inserts one hashed code
   expiring in ten minutes. It does not change the password or training records.
5. The code appears once directly on the private controlling terminal after
   commit. The owner immediately enters it in the existing FERRAVIS **Enter a
   reset code** screen and chooses a new password. Confirmation owns atomic
   single use and invalidates previous sessions. Sign in again; verify saved
   account and history without creating synthetic workouts.
6. Preserve the protected, secret-free `.issuance.json` and `.displayed` receipt.
   Missing display receipt means uncertain delivery, not proof of rollback. Never
   replay/reprint. Another attempt requires a fresh state-bound manifest and fresh
   explicit owner authorization and invalidates the previous code. Do not edit or
   delete attempt markers to retry. A failure may commit before transport fails.

The host script sends only reviewed worker source and target binding to the
existing API interpreter; no installation, source mount or restart. The worker
uses the configured DB only after verifying the exact backend/name/role, cluster,
server IP/port, schema and APP_VERSION, independently cross-checked via PostgreSQL
socket and immutable Docker metadata. Privileged host/Docker operators are inside
the trust boundary. Issuance is not exposed through an HTTP API.

Permanent backup codes need additive 0028 and the candidate API/web deployment,
separately approved. One backup code reset consumes only that code; an operator
or legacy email token reset revokes all permanent backup codes after deployment.
No production token, password, database or release-control change is authorized by
this runbook or PR. Issues #103 and #105 remain open.
