# Auth Expansion Architecture Contract (Phase 12)

Purpose: define the architecture for adding OAuth (Google/Apple) and Passkey (WebAuthn) authentication without breaking deterministic planner/runtime behavior or current JWT session semantics.

## Scope

- Additive authentication methods for existing user accounts.
- Identity-linking rules across password, OAuth, and passkey credentials.
- Session issuance and revocation behavior.
- Security and operational boundaries for self-hosted deployment.

This document is contract/architecture scope and does not by itself claim full endpoint implementation.

## Core Invariants

- Existing email/password login remains supported and backward-compatible.
- Auth expansion must be additive; no forced migration for existing users.
- Deterministic planner/workout behavior is unchanged by auth method.
- All successful auth methods issue the same session model (JWT + existing API auth contract).
- Account identity resolution is deterministic and never ambiguous.

## 1) Identity Model Contract

Primary user record remains canonical:

- `users.id` is the only internal identity key for app data ownership.

Auth method attachments are modeled as linked credentials:

- Password credential: local email/password hash.
- OAuth credentials: `(provider, provider_subject)` pair.
- Passkey credentials: WebAuthn credential id + public key material + sign counter.

Deterministic uniqueness rules:

- One `(provider, provider_subject)` maps to exactly one `users.id`.
- One passkey credential id maps to exactly one `users.id`.
- Email-based linking requires verified email match or explicit authenticated link flow.

## 2) OAuth Architecture Contract (Google + Apple)

### Provider flow
- Use Authorization Code + PKCE.
- Validate provider tokens/signatures server-side.
- Do not trust client-decoded identity claims without provider verification.

### Account resolution order (deterministic)
1. Existing linked OAuth credential match `(provider, provider_subject)` -> login.
2. Else verified email matches existing account -> require authenticated link confirmation (or deterministic policy toggle if user already authenticated).
3. Else create new account and attach OAuth credential.

### Token/session behavior
- OAuth login issues first-party app session tokens (same JWT model as password auth).
- Provider access/refresh tokens are optional and must be encrypted/isolated if stored.
- Logout/revoke semantics apply to local session independently of provider session.

## 3) Passkey (WebAuthn) Architecture Contract

### Registration
- Challenge generated server-side with expiry and single-use nonce semantics.
- Relying Party ID is deterministic per deployment domain.
- Attestation policy configurable (none/indirect), default privacy-preserving.

### Authentication
- Server verifies assertion signature, challenge, origin, RP ID, and sign counter behavior.
- Passkey credential resolution maps deterministically to one `users.id`.
- Successful assertion issues the same app session tokens as other auth methods.

### Recovery & fallback
- At least one fallback login method must remain available unless explicitly disabled by user policy.
- Passkey removal requires recent re-authentication.

## 4) Session & Claims Contract

- Session claims remain minimal and consistent across auth methods.
- `sub` must always be `users.id`.
- Optional claim `amr` may indicate auth method class (`pwd`, `oauth`, `webauthn`) for auditing.
- Session TTL/refresh policy remains centrally configured, method-agnostic.

## 5) API Surface Contract (Planned)

Additive endpoint families (exact naming may vary during implementation):

- OAuth:
  - start authorization (provider-specific)
  - callback exchange + account resolution
  - link/unlink provider credentials
- WebAuthn:
  - registration challenge
  - registration verify
  - authentication challenge
  - authentication verify
  - list/delete passkeys

Error semantics:

- Invalid challenge/signature/origin -> deterministic `401`/`400` class responses.
- Identity linking conflicts -> deterministic `409`.
- Validation failures -> deterministic `422`.

## 6) Data & Migration Contract

Planned additive tables (or equivalents):

- `user_oauth_accounts`
- `user_passkeys`
- `auth_challenges` (ephemeral/persistent strategy)

Migration invariants:

- Existing users unaffected until they opt into new methods.
- No destructive change to current password auth tables.
- Rollback path documented for partially applied auth expansion migrations.

## 7) Security Requirements

- Strict redirect URI allowlists for OAuth providers.
- CSRF/state + nonce verification on OAuth callback.
- Challenge replay protection and expiration enforcement for WebAuthn.
- Audit logging for link/unlink, passkey add/remove, and suspicious failures.
- Rate limiting integration with Phase 11 policies for auth endpoints.

## 8) Test Matrix (Minimum)

1. Existing password login unchanged.
2. OAuth login for pre-linked account resolves correctly.
3. OAuth new-account create path deterministic.
4. OAuth link conflict returns deterministic `409`.
5. WebAuthn registration challenge replay rejected.
6. WebAuthn assertion with invalid origin rejected.
7. Passkey login issues same session shape as password login.
8. Link/unlink operations audited and constrained by re-auth policy.

## Change Control

Any contract change here requires synchronized updates to:

- `docs/High_Risk_Contracts.md`
- `docs/GPT5_MINI_HANDOFF.md`
- `docs/Master_Plan.md`

## Progress Sync (2026-03-06)
- Repository state synchronized through commit `09ac04e` on `main` (pushed to `origin/main`).
- Validation baseline is green via `./scripts/mini_validate.sh`:
  - API: `60 passed`
  - Web tests: `16 passed`
  - Web build: success
- Latest delivered stabilization work:
  - fixed containerized API test DB resolution to prefer `DATABASE_NAME`
  - added regression coverage for test DB configuration precedence
  - fixed Settings test by mocking `next/navigation` router
  - resolved web lint/build blockers in `today` and `history` routes
  - removed invalid `<center>` nesting from the home page markup
- Known follow-up (non-blocking): Vitest reports `2 obsolete` snapshots in `apps/web/tests/visual.routes.snapshot.test.tsx`.
- Drift prevention protocol for next sessions: run `./scripts/mini_preflight.sh` and `./scripts/mini_next_task.sh` before implementation, and `./scripts/mini_validate.sh` before commit/push.

