# September 2026 codebase, product and documentation audit — retained summary

Audit key: **AUD-20260928**. Audit date: **2026-09-28**. Audited revision: **`df9965232ce731f8234d222acc526a90bc6be620`**. This sanitized retained summary derives from the completed external audit, verification notes and 199-file inventory; it is not a new audit or live deployment certification. Complete raw originals originally lived outside Git in the owner's audit collection and remain outside this branch. Basenames/original SHA-256 identities are in the [evidence registry](../evidence/README.md#audit-reference-and-migration-plan).

## Scope and major findings

Source review covered API/web/core, authored ingestion/artifacts, generated planning, contracts/docs, scripts/workflows and persistence/security/operations; deeper probes examined selected runtime paths. The documentation inventory covered **199 files**, including generated guides, runtime rule JSON, qualification data and empty placeholders. This is not exhaustive review of every source line, historical claim, dependency, browser behavior or production control.

| Finding | Established observation / limit |
|---|---|
| Account recovery | High severity source finding: unauthenticated reset responses expose the reset credential under shipped defaults or incomplete SMTP. Effective production settings/compromise unknown. [Urgent proposal](../plans/urgent-account-recovery.md), no fix implemented. |
| DB safety | High operational risk: destructive validation can inherit ordinary DB targets. A fresh container does not prove isolation. Production DB untouched; [safety lock](../../DB_SAFETY_LOCK.md) remains. |
| Credential/session/configuration | Medium: accepted public JWT placeholder is conditional on retention; existing JWTs survive reset; SMTP STARTTLS lacks verified context and needs network-attacker prerequisites. Low: validation rejection values may evade key-name redaction. Original severities and prerequisites remain; no live configuration/log inspection. |
| History integrity | Session IDs repeat across weeks; occurrence binding, retry uniqueness, concurrency and undo/derived progression are inadequate. PostgreSQL behavior is not established by SQLite runs. |
| Authored restrictions | Any nonempty restriction disables authored passthrough protection, reopening generic adaptation. Probes: 88 sets unrestricted vs 85/86, or 91 for an unmatched restriction. No generated writer overwriting authored files was established. |
| Source fidelity | Phase 1 315/315 rows matched tested fields; Phase 2 310 source vs 305 retained, AMRAP push-up weeks 6–10 omitted by numeric-only importer. Diagnostic skips are not permission to admit incomplete source. |
| Execution fidelity | Loader sums working sets and uses first numeric target; typed relationships/set-specific/warm-up/order fidelity is incomplete. 80 unrestricted prescription-multiset cases do not certify ordering or missing rows. |
| Load intelligence | Persistent state advances per submitted set, not completed exposure; actual logged weight is absent from the progression calculation; normal logger RPE is null. Reliable comparable exposure/override/undo qualification is missing. |
| Scheduling | Day count/mechanical offsets exist; actual chosen dates, timezone/week/spacing and identity-preserving reschedule are not implemented. |
| Generated planning | Useful deterministic pipeline, but overlapping policy ownership, inherited authored scaffolding/fallback and trace-only controls remain. Six principal active controls identified. Metadata-v2 scoring stays disabled/no-op; accounting is active. |
| Operations / claims | Dual schema owners (Alembic/startup create_all), limited backup/restore proof, unsafe validation assumptions and incomplete CI gates. Documentation/maturity checkmarks exceed established source/device evidence. |

Positive/negative controls are retained: inspected protected data routes use server-derived user scope; no cross-account IDOR was established in reviewed paths. JWT algorithms are pinned; reset credentials are random/hashed/expiring/single-use in sequential flow, which does not prove concurrent consume safety. Development wipe defaults off and is flag-gated; it is not unconditionally exposed. Program path containment and offline ingestion were observed. No XSS, leaked redirect token, verified ingress/TLS, active session state or all-file security coverage is asserted.

## Original verification results

| Procedure | Original result / interpretation |
|---|---|
| Core | 364 passed, 4 failed; individual contract disposition pending. |
| Full API | 430 passed, 18 failed, 8 skipped; retain full result. |
| Selected API recheck | 12 passed: 11 previously failing plus one previously passing; nine flag assumptions/two copied-fixture issues cleared, one absolute-workbook-path issue separately retained. |
| Behavioral API recheck | Six persistent failures: two Today/progress totals, generated core-slot balance, legacy-alias deload assumption, authored review-overlay assumption, substitution fixture expectation. Reproduction alone does not make each a code defect. |
| Web | 51 passed, 1 failed across 20 files; ambiguous Today query expectation. |
| TypeScript | 102 diagnostics: 90 TS2304 and 12 TS2582 for test globals. No successful production build established. |

## Verification and retention limitations

Tests ran in a copied disposable repository with explicit temporary DB/log targets, cleared Python/Node environments and network/database guards, never the production checkout. Copied dependencies/source do not establish an initially complete byte-identical snapshot: two early rule-fixture reads failed; fixture hash matched on recheck. No source-side repair occurred. The fidelity probe compares a multiset; positional Phase 2 fallout is not 1,239 independent defects. The independent workbook parser covers tested columns/paths, not every source paragraph/program rule. Use aligned omissions for source loss.

SQLite does not establish PostgreSQL concurrency or migrations. No production HTTP/account request, DB read/write, restart/deploy, production tests, personal-data/secret/log inspection, real-device/browser run, live smoke, backup restore or deployed-image verification occurred. Effective ingress/TLS/secrets/session/backup controls remain unknown. Optional managed security export **failed** its directory-privacy check; permissions were not changed. Independent source findings remain ordinary audit evidence, without sealed export or complete all-file coverage.

SnakeTracker at pinned revision `87652f8ea80f6328a15385dc2cc32beaf4dbc9e2` was studied read-only as a governance/traceability/evidence quality reference. Its domain/application architecture was not validated or adopted. No proprietary source workbook/manual, private raw environment output, personal training data or secret is republished by this summary.

## Documentation integration relationship

[Complete migration registry](2026-09-28-documentation-migration-registry.md) preserves all 199 dispositions and original hashes; [migration report](2026-09-28-documentation-authority-migration.md) records the later documentation-only integration. [Current-state architecture](../architecture/current-state.md) carries revision-scoped defects; [target system](../architecture/system.md) expresses desired ownership. [Requirements/traceability](../requirements/catalog.md) and [roadmap](../roadmap/milestones.md) define future qualification, not retrospective passes. No product behavior is repaired, milestone completed or Proposed ADR accepted by documentation publication.
