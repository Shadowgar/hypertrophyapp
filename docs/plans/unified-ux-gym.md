# Unified UX: account protection, foundations and gym execution

Status: **First application slice implemented and qualified in isolation, 2026-10-22; application PR prepared for review.** No merge, deployment or production migration authorized.

Spec: [approved design PR #108 at 33598c3](https://github.com/Shadowgar/hypertrophyapp/tree/33598c3fb35328cc2d2b6310865f716380b6c81e/docs/ux/astra-2026-10-20/unified-2026-10-21). Source base fc3bd0c. First implementation PR; later focused PRs complete the remaining page layouts.

## Global constraints

Preserve deterministic core owners, immutable Authored dose/source and Customized consent. Effective-history, occurrence and retry commands remain authoritative. No legacy estimate formula becomes new guidance. Only explicit disposable databases and synthetic accounts. Keep design assets on PR #108.

### Task 1: Protect accounts and persist presentation preferences

Interfaces: equipment PATCH changes only location/equipment; account appearance resource defaults Classic Dark with revision checking. Login never invokes setup writes. Existing full profile endpoint preserves omitted optional fields.

1. Add failing preservation/ownership/revision and onboarding login tests; run on explicit disposable SQLite and observe failures.
2. Implement scoped handlers and login separation; additive preference migration file only.
3. Run focused tests; expect pass. Commit.

### Task 2: Shared appearance and navigation foundations

Interfaces: task 1 account preferences; approved semantic tokens; local DM Sans; independent family/appearance. Shared responsive shell and Settings controls.

1. Add failing preference resolution/account-transition tests.
2. Implement tokens/provider, navigation, accessible Settings saving/recovery, typography.
3. Run focused tests and TypeScript; expect pass. Commit.

### Task 3: Stable gym execution

Interfaces: current Today command callbacks, effective receipts, source-preserving warmups. Stable composer, persistent exercise navigation; canonical kg at boundaries; actual effort separate from targets; immutable uncertain attempts, deadline timer, account/occurrence-scoped recovery.

1. Add failing pending/error/unit/reload tests.
2. Replace overlay layout, optional calibration without invented arithmetic; preserve source and correction/undo owners.
3. Run runner/source/identity/correction/history regressions; expect pass. Commit.

### Task 4: Qualify and publish

1. Run old/new apps on isolated synthetic data, mobile/desktop, Cross-Body Lat Pull-Around warmup/save/rest/next/correct/undo/reload/history and failed/uncertain replies.
2. Record timing/scroll measurements, DB preservation, screenshots and limits.
3. Run typecheck/build, regression suites, focused security review and final branch review. Fix material findings with regression tests.
4. Publish application PR/evidence and next remaining slice. No merge or deploy.

## Review Focus

Account changes during outstanding requests; concurrent appearance saves; pending commands after refresh; duplicate prevention; warmup/technique children and original/performed identity; unknown effort; unit conversion; confirmed receipts versus local draft; composer geometry and keyboard focus. No browser cache transfers data between accounts.

## Delivery evidence

[Runtime galleries, preservation proof, measurements and qualification limits](../evidence/unified-ux-gym/README.md). [All 28 audit finding statuses](../evidence/unified-ux-gym/TRACEABILITY.md) distinguish this slice from the remaining approved layouts. Production acceptance remains separate.
