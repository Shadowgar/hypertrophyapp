# Forbidden Patterns

Last updated: 2026-03-12

This is a practical anti-pattern list for active implementation work.

## UI Maps Internal Codes To Coaching Prose

Forbidden:

- `switch` / map helpers in React pages or components that turn reason codes into human coaching language
- title-casing codes so they sound like rationale
- fallback copy that sounds causal when the backend only emitted a raw code

Do instead:

- render `rationale` directly when the owner emitted it
- otherwise render the raw code or render nothing

## Facade Layers Own Reason-Message Maps

Forbidden:

- message tables in `packages/core-engine/core_engine/intelligence.py`
- local `humanize_*reason*` implementations in façade/orchestration files
- compatibility wrappers that do more than alias, forward, or pick among already-authoritative fields

Do instead:

- keep message ownership in the decision-family owner
- leave compatibility surfaces as thin aliases or pass-through selectors only

## Execution Engines Invent Doctrine

Forbidden:

- `scheduler.py` or similar execution code deciding progression philosophy, weak-point doctrine, substitution philosophy, or deload meaning
- rule executors silently becoming business-level owners

Do instead:

- keep doctrine in `decision_*` owners and canonical rule/runtime inputs
- let execution code apply policy, not create it

## Compatibility Layers Retain Local Meaning Logic

Forbidden:

- wrappers that started as migrations but still translate, soften, or elaborate authoritative outputs
- adapters that keep old behavior by adding local prose

Do instead:

- delete the wrapper
- or reduce it to direct aliasing
- or keep a trivial field-selection helper with zero local humanization

## Tests Validate Narrative Labels Instead Of Authority Boundaries

Forbidden:

- tests that pass because a friendly string appears
- tests that encode UI storytelling instead of checking owner boundaries, raw fields, or trace-backed rationale

Do instead:

- assert raw authoritative fields
- assert forbidden strings are absent
- assert façade symbols are aliases when a compatibility surface remains

## Router Or UI Explains Why A Decision Happened

Forbidden:

- API response shaping that rewrites reason codes into guidance
- component-level text that implies a recommendation happened because of a local heuristic

Do instead:

- emit explanation from owner output
- if the owner did not emit rationale, do not invent one

## Documentation Pretends A Closed Seam Is Still Open

Forbidden:

- implementation notes that tell future coders to keep revisiting already-closed Tier 4A seams without evidence
- status docs that blur law, current-state maps, and historical audits together

Do instead:

- treat law, current-state maps, execution rails, and evidence as separate classes
- reopen a closed seam only with current-code proof
