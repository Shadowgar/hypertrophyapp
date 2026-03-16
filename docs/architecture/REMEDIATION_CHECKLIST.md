# Remediation Checklist

**Status:** Retired (2026-03-16). Items below were completed as part of the Phase 1 canonical path work. Do not reopen these as active blockers without current-code regression evidence.

Previous active wave: `Blocker 1`

Completed items:

1. ~~Make generated week emit one real top-level authoritative `decision_trace`~~ — Done. `decision_generated_week.py` owns generated-week meaning; top-level trace on generate-week path.
2. ~~Move generated-week template selection into a named owner and keep `generation.py` orchestration-only~~ — Done. Template selection and runtime resolution at loader/decision_generated_week boundary.
3. ~~Strip doctrine invention out of `scheduler.py` on the generated-week spine~~ — Done. Scheduler executes doctrine from rules_runtime and canonical template metadata; does not invent policy.
4. ~~Remove silent doctrine fallback from gold-path first-class generation~~ — Done. Canonical rules load first; legacy overlay only as explicit compatibility fallback.
5. ~~Enforce explanation-law classification on first-class week surfaces~~ — Done. Week/today/check-in/history render authoritative or raw fields only; no invented rationale (see FORBIDDEN_PATTERNS, ACTIVE_REMEDIATION_RAIL).

For current execution guidance, use `docs/implementation/ACTIVE_REMEDIATION_RAIL.md` § Next Tasks (task rail).
