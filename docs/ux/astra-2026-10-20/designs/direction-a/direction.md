# Direction A — Next Step

**Status: original design sketch for owner review. Documentation and visual assets only. No implementation approval, application code, deployment or backend qualification.**

Independent author: `/root/astra_execution_audit`, dispatched as the gpt-6-astra auditor/designer. Created after the frozen source and browser audit. Inputs: this agent’s execution-source audit, `/tmp/astra-browser-evidence.md`, and `/tmp/astra-journeys-source.md`. No prior Focus/Training Ledger designs or previous 15-finding report consulted.

All people, accounts, loads, dates, exercise counts, prescriptions and history shown are **synthetic examples**. The 87-set week and 29-set session demonstrate allocation readability, not source-program validation. Source rest/effort examples and suggested 40 lb have no new calculation behind them. A future implementation must render values from the qualified owning decision/source and abstain when unavailable.

## Idea and judgment

Next Step makes the app feel like a considerate guide. Each stage answers one immediate question: Which program? Which dates? What do I do now? Did that save? What comes next?

Mobile uses a warm charcoal canvas with layered dark surfaces, mint accents and legible light text, large serif task headings, one principal action, generous vertical rhythm and short instructions. Setup and training progress through explicit steps. Detailed evidence remains reachable, without putting setup fields ahead of every set. Desktop uses the full canvas for a single current task with a restrained contextual column; it does not enlarge a phone column or become a simultaneous control-room workspace.

The composition is deliberately different from Direction B’s persistent spatial session workspace: **A changes stage to follow the task**, with one active exercise/set and a clear return to overview. The stage is user-controlled; saving never launches the next exercise automatically.

Typography: **Libre Baskerville** for expressive page headings and selected large numbers; **DM Sans** for controls and reading. SVG stacks fall back to Georgia/DejaVu Serif and Arial/DejaVu Sans if the preferred fonts are absent. Central Figma publishing should use Libre Baskerville Regular/Bold and DM Sans Regular/Medium/Bold. Local system-font renders may have different line metrics; neither font is embedded or fetched by these files.

## What the sketches show

- 24 mobile frames, each 390 × 844, numbered by journey.
- Eight desktop compositions, each 1440 × 900.
- `index.html`: static asset gallery; no network calls, product state or backend operations.
- Every SVG has native text, a native accessible title/description, and a synthetic/design caption.

| Files | Task and proposed interaction |
|---|---|
| `01-welcome-mobile.svg`, `02-sign-in-mobile.svg` | Two clean account choices. Existing-account sign-in restores a session only; it does not enter a profile-save/onboarding pipeline. Persistent labels, password reveal and a separate recovery action. Guest screens have no signed-in navigation. |
| `03-program-path-mobile.svg`, `desktop-01-start-program.svg` | Choose Authored Phase 1, Authored Phase 2, or explicitly Customized before extensive setup. A recommendation may help select an Authored program, but cannot confer design permission. Selection is one tap; Continue moves to setup. |
| `04-setup-mobile.svg` | One display-unit choice and clear equipment scope. Authored details describe load context; Customized requires exact inventory before a new design. A saved global unit preference is a **proposed capability**, not an existing setting. |
| `05-home-mobile.svg`, `desktop-02-home.svg` | One dominant task: open the actual scheduled session. Selected dates and check-in remain secondary. Rest day, loading, unavailable and unscheduled states are distinct; no generic “Synced” badge from token presence. |
| `06-week-review-mobile.svg`, `desktop-03-week.svg` | Choose dates → preview → inspect workload/relationships → save those reviewed dates. Workload comes before activation. Fewer dates are described as longer sessions, with no invented duration or equivalent-results claim. |
| `07-customized-consent-mobile.svg` | Review the exact program and complete change summary → explicit acknowledgement → accept reviewed version → separately confirm activation dates. Input changes invalidate preview/acknowledgement. Existing performed history remains separate. |
| `08-first-load-mobile.svg` | Three clearly distinct first-load paths: recent comparable actual set, historical known 1RM, or comfortable manual entry. **Known-strength intake for Authored is proposed domain capability.** No legacy formula is activated, no maximal testing is requested, and no percentage is invented. |
| `09-source-warmup-mobile.svg` | Show source warm-up count once in readable formatting, source instructions, actual reps/load and optional actual effort. Save creates a warm-up receipt, not a working-set completion. |
| `10-working-before-mobile.svg`, `11-working-after-mobile.svg` | Individual readable before/after frames, with exactly matching control geometry and compact rest countdown beside the receipt. Source target is distinct from actual entries. One status region changes from ready to a single receipt; no repeated receipt list above/below. |
| `12-rest-mobile.svg` | Saving a working set starts source-owned rest, with clear countdown/pause and an explicit next-set action. It does not advance the exercise. |
| `13-correction-mobile.svg` | Open the effective receipt, edit actual values, save a correction. Unknown effort is not converted to a target. Undo is offered only for the latest eligible record through the existing undo-last-set boundary, with a concise confirmation naming that record. Older receipts allow correction, not arbitrary undo. |
| `14-unconfirmed-save-mobile.svg` | Uncertain response is visible in the active task. Freeze attempted values, keep same command identity, offer Retry same set. No editable new payload masquerading as that retry. |
| `15-complete-history-mobile.svg`, `desktop-05-history-review.svg` | Completed working-set count is explicit; partial, planned, unscheduled/rest, unavailable and complete are separate. Every recorded weight has a unit. Corrections and effective values remain discoverable. |
| `16-check-in-mobile.svg` | Review experience with labeled units and optional/private context. Saving a review is separate from next-week scheduling and never implies undisclosed program generation. |
| `17-settings-mobile.svg`, `desktop-06-settings-library.svg` | Scope each preference edit; visibly acknowledge success/failure. Program change routes through preview, not a generic profile save. Account menu provides normal sign-out. |
| `18-library-mobile.svg` | Source programs stay distinct. Program and exercise guidance is reachable from primary navigation and contextual exercise links. No raw JSON, internal IDs or copied licensed instructions. |
| `desktop-04-execution.svg` | Comparison storyboard (not the desktop runner) plus explicit Authored pair/technique and Customized RIR variants. The right column explains context, never invents prescription policy. |

Additional review frames complete the first-load and failure journeys:

| Files | State |
|---|---|
| `19-known-1rm-entry-mobile.svg` | Actual historical-1RM entry with exercise/setup, labeled load and observed date. Proposed intake; no maximal test or workout-set insertion. |
| `20-recent-set-entry-mobile.svg` | Actual recent-set load/reps/date entry, with optional blank effort and comparability review. Proposed intake. |
| `21-manual-calibration-mobile.svg` | No suggestion available; user chooses a comfortable working load, then proceeds to source warm-up. The displayed insufficiency explanation is a synthetic server fact, not frontend inference. |
| `22-home-loading-mobile.svg`, `23-home-rest-mobile.svg`, `24-home-error-mobile.svg` | Explicit loading, intentional rest and failed request states, with appropriate disabled/loading, view-week and retry actions. |
| `desktop-07-execution-before.svg`, `desktop-08-execution-after.svg` | Genuine desktop runner: a single composer, session trail and adjacent persistent rest/context column. The before/after pair shares identical composer coordinates. |

The consent frame now shows selected week **19–25 October**, exact three dates, **48 illustrative working sets / 16 per date**, and unknown duration before the checkbox. Its unchecked state has a visibly disabled accept button. The input example is not a current prescribed workload.

## Information architecture and tap paths

Signed-in mobile navigation: **Home · Week · History · Library**. The 44 px account button opens account/settings/sign-out; Home offers weekly check-in. Desktop adds direct Check-in and Settings destinations because space permits. A full-screen task retains an explicit return to the prior overview. Escape/back returns focus to the launching control, preserving list position and draft state where safe.

New person: Welcome → Get started → choose authority (1 selection) → relevant units/equipment → dates → workload review → explicit save → Home. Authored Phase 1/2 remain separate choices with their guides. Customized inserts its own generation/preview/consent before date activation. Optional biographical inputs are requested only when the active qualified capability needs them, with a reason and honest unknown state. This is proposed journey restructuring; it is not a claim current onboarding can skip every field safely.

Returning person: Sign in → restore intended route or Home. No profile-save, reset, initial check-in or generation side effect. Recovery is a separate email step, then link-based new-password step, then return to sign-in. Recovery results should avoid disclosing account existence; rate limits and account lifecycle remain owned by the existing security path.

Training: Home → session overview → current exercise → first-load setup only when needed → source warm-up → working set → rest → next set → next source exercise. The overview is always reachable; no forced completion of pain-conflicted work. The guided order must preserve source-defined pairings/primers and set-specific techniques. A source pair uses a visible A1 → A2 trail; its source order/rest remains authority. A technique cue appears on the prescribed set, with its existing confirmation boundary. Unresolved substitutions show the original source slot, permitted alternative, reason and explicit confirmation; they never silently advance or delete the slot.

Manual load remains possible when evidence is insufficient. Entering recent work or an existing 1RM records its own evidence kind, exact exercise/setup, unit and observed date. A known 1RM is never inserted as a performed work set. Qualification, comparability and any resulting load remain the deterministic owner's decision. If no supported intake path exists, the UI must say so and retain manual entry rather than invoke the old browser formula.

## Stable execution state model

The desktop runner preserves one composer at x332–980 and keeps the rest display adjacent at x1004–1392. Its status region remains y441–521, reps/load labels y560, effort label y686 and primary action y785–839 in both states. The compact mobile after-save status includes the live rest count and Pause alongside Edit/undo latest without any height change.

The mobile working-set frames share these coordinates: source card y244–338; status region y354–442; reps/load labels y467, fields y479–535; actual-effort label y590, field y602–658; save action y699–753. This reserve prevents a new receipt from pushing the next set action downward. Status detail that exceeds its allowance opens a focused detail panel rather than growing the form. These are design coordinates, not a mandate for fixed pixels at all text sizes.

1. **Ready:** Actual effort is blank. Source target and suggestion origin are labeled. Suggested load can prefill only from the qualified owner; user edits remain visible.
2. **Saving:** Disable duplicate submission; show “Saving set…” in the same action/status locations. Keep the exact attempted payload and command identity. Inputs become read-only, not silently reinterpreted.
3. **Confirmed:** Render one receipt in the reserved region. Announce success once. The next set is identified separately. Retain or deliberately move focus according to the user’s task; never drop it to page body. Do not replace typed draft values with asynchronous advice.
4. **Not confirmed:** Retain/freeze the attempted payload; explain that Retry sends the same set once. Retry uses the same identity. An independently confirmed receipt reconciles this state. Do not offer a new-set save until uncertainty resolves.
5. **Rejected or stale:** Name the problem inline. Refresh qualified advice where supported, preserve actual inputs for review, and clearly distinguish a corrected new attempt from retrying an uncertain one.
6. **Correction:** Open receipt detail with visible original/effective value and optional reason. Keep correction versus new set distinct. Blank effort means unknown only through explicit intended behavior; leaving unchanged preserves existing effort.
7. **Undo:** Offer only the latest eligible receipt supported by the existing undo-last-set operation; older historical receipts expose correction only. Name whether warm-up, work or technique child is being undone. Confirmation is one focused dialog. Reflect effective server receipt/count before changing progress. Error remains inside the task.
8. **Complete:** Only qualified completed working sets create session-complete presentation. Partial closure has a distinct honest label. Completing a session does not prove growth or recommendation efficacy.

Rest uses an explicit end instant for elapsed-time rendering in a future implementation, with paused state and an expiry label. Reopening an exercise should restore the same current timer, not create a second countdown. Actual suspension/reload semantics require implementation design and device qualification; this sketch does not claim they are shipped. Timer sounds/vibration are optional user choices, never the only indication.

## Units, effort and rationale

A proposed shared display preference applies consistently to warm-ups, work, advice, receipts, corrections, bodyweight and history, while canonical values and original recorded unit/basis remain preserved. Switching display unit converts the visible value without changing the underlying performed observation; rounding must not create new evidence. Per-hand, total external, assistance, machine setup and added-bodyweight meanings remain explicit where relevant. Assistance must not inherit ordinary “more is better” language.

Authored source target RPE/RIR and actual effort are visibly different. Actual effort always starts blank/unknown; no target copying or silent RPE↔RIR conversion. Customized displays the effort scale owned by its accepted prescription; the desktop variant includes an explicitly blank actual-RIR field. Brief “What does this mean?” help explains the scale without inventing historical values.

Why this load is secondary disclosure that renders real owner facts: action, evidence scope, uncertainty, setup/basis and override. It may not translate opaque rule IDs into invented causal explanations. Unknown duration stays unknown. Empty/error states do not display zero as certainty or direct the user to destructive setup actions.

## Accessibility and responsive intent

- Touch targets: all interactive rows, tabs, icon buttons and receipt actions must have a **minimum 44 × 44 px hit region** in a future implementation; principal actions 54 px high. SVG text links represent a larger row/hit region in implementation. Visual checkbox is 25 px inside a 73 px selectable row, not a 25 px isolated target.
- Type: primary controls/body intended 15–17 px, headings 27–39 px, supporting metadata 12–14 px. 10–11 px synthetic captions are documentation labels, not critical product instructions. At 200% text/zoom, natural reflow and vertical scroll take precedence over these static viewport coordinates; no clipped status or forced fixed card height.
- Measured chosen dark color pairs: `#F1F1E7` on `#1C1D1A` **14.90:1**; `#BBC2B5` on `#282A25` **7.94:1**; `#16261C` on `#9FD5B5` **9.53:1**; `#A9DDBD` on `#283D33` **7.62:1**; `#F0C995` on `#413426` **7.74:1**; `#E2D1AF` on `#24382E` **8.32:1**; `#788272` on `#282A25` **3.61:1**. Canvas `#1C1D1A`, cards `#282A25`, selected panels `#283D33`, hero panels `#24382E`, and disabled controls `#42483F` remain dark. Mint-filled actions and selected chips use dark `#16261C` text; light text on dark hero panels is preserved. Color is supplemented by words/icons for selected, saved, partial, warning and error states. These are computed sRGB palette ratios, not a completed accessibility audit.
- Focus: visible 3 px focus ring with 3 px offset; logical DOM order matches reading order. Dialogs contain focus, escape intentionally, label their purpose and restore the invoking control. Navigation uses current-page semantics. Selection uses native radio/checkbox state, not color alone.
- Forms: persistent labels, appropriate autocomplete/email/numeric input modes, unit in each load/bodyweight label, actual-effort scale named. Errors associate with fields and are announced. Recovery and authentication use pending guards and visible outcomes.
- Announcements: polite status for confirmed save; assertive only where immediate correction is required. No per-second screen-reader countdown announcements. A timer offers a non-live readable value and announces expiry once.
- Keyboard: action region follows the visible keyboard viewport or moves immediately after active inputs; it must not sit beneath the OS keyboard. The focused input, its label and validation remain visible. Receipt edits appear in their own focus-managed panel. Physical iOS/Android keyboard testing remains required.
- Motion: short optional opacity transition, no required sliding page choreography or animated count interpolation. Reduced-motion uses immediate state replacement. No blinking timer or motion-only save feedback.
- All SVGs include native `<title>`/`<desc>`; gallery images have alt text. Static SVG mockups are illustrations of interactions, not working form controls or accessibility-qualified application pages.

## Advantages and trade-offs

**Advantages:** reduces first-session decision load; makes the immediate training action prominent; provides natural places for source cues, consent and recovery; treats each save as a legible state transition; presents workload before commitment; restores Home/library/account discoverability; desktop finally uses available space.

**Trade-offs:** experienced lifters may dislike stepping through stages; comparing multiple exercise records takes an overview/detail transition; advanced setup is less immediately visible; stable status space uses vertical room even before the first save; broader onboarding/unit/preference changes require real product/domain work beyond CSS. Offer overview access and persist safe preferences, but do not turn this direction into the other direction’s multi-panel workspace.

## Review boundaries and handoff

This is a full-app direction for selection, not a ready implementation specification. Proposed domain capabilities include Authored historical-strength intake, a persisted global unit preference, revised profile mutation scope, unified honest history statuses, timer persistence and journey changes. They require separately bounded implementation authorization, the corresponding context groups, decision ownership and negative-boundary tests. A visual redesign cannot authorize new prescription policy, scoring, source mutation, consent shortcuts or production writes.

Revision 2 dark asset checks: all 32 native SVGs parse as XML and retain their title/description; every non-color attribute, text node and element order matches the preceding revision. Geometry, wording and flow are unchanged. Semantic action-label overrides keep dark text on mint controls; all large panels retain dark fills. Palette ratios calculated from declared sRGB colors. No application tests/imports/startup/database operations. This agent did not use the shared browser. Parent owns actual SVG rendering, screenshots/PNG exports and central Figma publishing; those results must be recorded separately. Owner review is the next gate. Stop before implementation.

Final review correction: the unconfirmed-save helper says “Attempted values · retry this exact set,” not that the locked inputs can be changed. Undo labels are explicitly latest eligible record only; no arbitrary historical void capability is proposed.
