# Onboarding and deterministic GenerationProfile

Owner-approved normalization/mode boundary; detailed mapping mechanisms Proposed. Application evidence: `df9965232ce731f8234d222acc526a90bc6be620`. Governing [product](../requirements/product-contract.md), [ADR-002](../adr/0002-mode-authority-and-consent.md), [ADR-004](../adr/0004-deterministic-runtime-and-ai-boundary.md), [runtime authority](../architecture/runtime-authority.md), [GEN requirements](../requirements/catalog.md#gen) and [M4 plan](../plans/generated-stabilization.md).

Authored selection is separate from Customized consent. Normalize raw answers before generation and retain profile version, origin (user/default/history/compatibility), effective value and validation outcome. Empty/cleared input must have explicit semantics; it cannot retain a stale restriction or silently substitute a seed. Hard constraints dominate soft preferences; ambiguous/unsupported fields are reported, not invented.

| Control group | Audited influence / target obligation |
|---|---|
| Days, time band, recovery, weak points, movement restrictions and mode | Six principal active controls in the audit. Reproduce their actual influence and clearing behavior; protect authored dose from generic control effects. |
| Equipment | Legacy equipment still feeds assessment. Canonical equipment pool/availability and fallback semantics need reconciliation; do not claim every normalized field is consumed. |
| Goal, preferences, anthropometry, optional physiology, self-reported bests / calibration | Historical profile/spec targets are partially implemented or trace-only. Declare support/origin; no new influence or numerical policy is activated here. |

Preserve optional sensitive-field minimization, non-diagnostic restrictions and no stereotyped sex-based programming. Start-load provenance favors comparable logs, then qualified self-reports, then conservative seed/calibration. Source-defined Authored effort stays fixed; Generated starting-RIR and other historical numeric bands are proposals/compatibility facts, not accepted universal thresholds.

Profile validation, invalid/unsupported/cleared cases, identical-input replay, active-control sensitivity and Authored negative tests qualify a future change. Trace records alone do not qualify behavior. Preserve historical field/type examples in [profile schema](../GENERATED_PROFILE_SCHEMA.md) and [onboarding specification](../ONBOARDING_GENERATED_PLAN_SPEC.md); read them only to resolve a referenced compatibility question. Public API/profile schema changes and legacy-user consent mapping remain pending.
