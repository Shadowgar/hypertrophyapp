# Transition UI And Testing Readiness Design

**Goal:** Surface authored-sequence completion and next-step coaching guidance in the web UI, then make internal browser dogfooding easier with lightweight tester docs.

## Scope
- Extend the frontend coach-preview contract to include the new phase-transition fields already present in the API.
- Render an inline `Program Transition` section inside the existing coaching panel when transition state is pending.
- Keep existing progression/phase messaging intact when transition is not pending.
- Add lightweight tester docs for desktop/mobile browser internal dogfooding.

## UI Design
When `phase_transition.transition_pending` is true, the coaching panel should render a concise section:
- heading: `Program Transition`
- status: `Current block complete`
- recommendation: `Rotate program`
- fallback: humanized `post_authored_behavior` when present
- rationale: use API rationale first, fallback to reason text helper

This section should appear on existing surfaces that already reuse the coaching panel:
- Settings
- Week
- Check-in
- Today

## Data Contract
Frontend `phase_transition` should support:
- `authored_sequence_complete?: boolean`
- `transition_pending?: boolean`
- `recommended_action?: string`
- `post_authored_behavior?: string`

## Testing
Use TDD:
- add failing component/route tests showing the new transition section when preview returns transition-pending state
- ensure legacy previews without transition-pending state still render the old panel cleanly

## Docs
Add tester-facing docs:
- concise internal runbook for PC/mobile browser dogfooding
- concise issue template focused on reproducible flows, device/browser, and coaching-trace context
