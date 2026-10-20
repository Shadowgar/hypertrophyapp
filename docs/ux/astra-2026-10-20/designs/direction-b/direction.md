# Direction B — Training Atlas

**An independent spatial workspace concept by the delegated gpt-6-astra journey auditor. Design proposal only; no runtime implementation, persistence qualification or deployment.** All sample records, loads, prescriptions, dates and quantities in the visuals are synthetic. Source-like examples illustrate presentation requirements; they are not transcriptions of either authored program and are not training recommendations. The small banner on every image preserves that distinction when an image is shared alone.

Training Atlas keeps three things in stable places: the exercise map, the next actual set entry, and its supporting evidence. It is designed for someone who repeatedly looks away from a phone to train, then returns to the same controls. It does not force the person through a new screen after each set. On desktop, the three areas are simultaneous columns. On mobile, a compact map stays above one fixed-height context region and the set composer; evidence opens into its own view and does not grow above the inputs.

The distinction from a task-sequenced alternative is structural. The user can revisit any exercise or inspect evidence while retaining the current draft and session position. Navigation represents places in the training record, not steps in a wizard. Setup and consent may contain dependent actions, but the application's organizing idea is a persistent map, not a sequence of prompts.

## Visual language

- **Background:** soft mineral `#F1F4EF`; cards white; boundaries `#D6DFD5`.
- **Primary ink:** pine `#15382E`. This is also the desktop navigation rail and primary action surface.
- **Working area:** pale clay `#FBE8DC`; copper `#C76138` marks the current exercise and selected emphasis. Copper is not the sole status signal.
- **Confirmed work:** green `#DDEBDD` plus a check and plain-language receipt text. **Pending:** blue `#E5EEF5`; **not confirmed:** red `#FBE7E2` with `#A23A31` text.
- **Typography:** IBM Plex Sans for UI and values; Libre Baskerville for restrained page headings. Standalone SVGs declare Arial/Georgia fallbacks and use native text. Figma can use the intended installed fonts. Font fallback metrics are a visual review limit, not a guarantee of pixel identity.
- 16–18 px main action text at desktop, 14–16 px mobile copy, large numeric inputs; compact secondary annotations remain secondary. The small synthetic/proposal banner is documentation metadata, not proposed product chrome.
- No glass, glows, nested telemetry cards or decorative gradients. The graphical session track and calendar carry navigation meaning.

## Artifact inventory

**Final inventory: 26 mobile SVGs and 6 desktop SVGs (32 total), plus this specification and the static gallery.** All mobile images are **390 × 844**. All desktop images are **1440 × 900**. Each SVG contains native text, a title, a description and `role="img"` with `aria-labelledby`. The static gallery is [index.html](index.html); SVGs are standalone and require no server or application dependencies.

| Mobile artifact | Coverage |
|---|---|
| [01 Welcome / sign-in](m01-welcome-sign-in.svg) | Stable labels, separate recovery entry, account creation, pure returning-user login |
| [02 Program authority](m02-program-authority.svg) | Distinct Authored Phase 1, Authored Phase 2 and explicit Customized permission |
| [03 Equipment / units](m03-equipment-units.svg) | Real inventory, per-hand meaning, proposed saved display preference, visible save |
| [04 Home](m04-home.svg) | Resume session map, current week, next required decision |
| [05 Week compression](m05-week-compression.svg) | Actual dates, per-session sets, preserved total dose, unknown duration, review before activation |
| [06 Customized consent](m06-customized-consent.svg) | Exact version, shorter/longer workload, provisional rules, explicit acceptance |
| [07 Active lifecycle](m07-active-dates-replacement.svg) | Date-only amendment versus program replacement; recorded work preserved |
| [08 First load — proposed](m08-first-load-proposed.svg) | Manual entry, recent-set evidence, known 1RM as separate evidence routes; no invented calculation |
| [09 Warm-up](m09-warmup.svg) | Separate warm-up receipt and count, same unit/basis, source prescription retained |
| [10 Before save](m10-set-before-save.svg) | Actual entry distinct from prescribed target and suggested load |
| [11 After acknowledgement / rest](m11-set-after-ack-rest.svg) | One receipt, set advancement only after acknowledgement, no input displacement |
| [12 Pending](m12-set-pending.svg) | No receipt yet; held attempt and visible waiting state |
| [13 Not confirmed / retry](m13-set-error-retry.svg) | In-place failure, exact original attempt, visible retry semantics |
| [14 Correction / undo](m14-correction-undo.svg) | Receipt-specific correction; Customized RIR target separate from unknown actual effort |
| [15 Completion / history / analytics](m15-completion-history-analytics.svg) | Real completion distinction, intentional rest, scheduled work, insufficient comparable evidence |
| [16 Check-In](m16-checkin.svg) | Labeled bodyweight units; review save distinct from scheduling |
| [17 Settings](m17-settings.svg) | Separate profile editors, proposed unit/accessibility preferences, visible feedback, sign-out |
| [18 Guides](m18-guides.svg) | Source target and AMRAP preserved, program→phase→day trail, return to session map |
| [19 Known 1RM form — proposed](m19-known-1rm-form-proposed.svg) | Historical load/date/setup/observation type and unchecked confirmation; no estimate |
| [20 Recent-set form — proposed](m20-recent-set-form-proposed.svg) | Actual load/reps/date, optional actual effort and explicit unavailable estimate |
| [21 Manual starting load](m21-manual-starting-load.svg) | User-chosen input, not a calculated estimate or performed receipt |
| [22 Session loading](m22-session-loading.svg) | Stable skeleton and disabled loading action; no false empty/rest conclusion |
| [23 Planned rest day](m23-planned-rest-day.svg) | Saved schedule context and next workout; no missed-work implication |
| [24 Session unavailable](m24-session-unavailable.svg) | Request failure, retry loading, no regeneration suggestion |
| [25 Account recovery](m25-account-recovery.svg) | Labeled email, enumeration-safe result, direct email-link password step |
| [26 Authored source pair](m26-authored-pair-variant.svg) | Dedicated A1→A2 sample; source relationship controls the next task |

| Desktop artifact | Coverage |
|---|---|
| [01 Home workspace](d01-home-workspace.svg) | Persistent navigation and weekly context beside session map |
| [02 Week workspace](d02-week-workspace.svg) | Three date columns, separate compression evidence, activation after review |
| [03 Workout before save](d03-workout-before-save.svg) | Exercise navigator + composer + independent evidence pane |
| [04 Workout after acknowledgement](d04-workout-after-ack.svg) | Same geometry, evidence receipt update, rest state |
| [05 Customized workspace](d05-customized-workspace.svg) | Declared setup, program map and consent side by side |
| [06 History workspace](d06-history-workspace.svg) | Correct calendar alignment, selected-day receipts, explicitly insufficient analytics |

## Information architecture and existing-route mapping

These are presentation destinations over the current route families, not a proposal to build duplicate domain systems. Route aliases may retain compatibility during any separately authorized implementation.

| Existing route | Atlas destination and behavior |
|---|---|
| `/` | Home. Guests see welcome/sign-in/create-account. Signed-in users see the training workspace. No simultaneous account-creation controls compete with the resumed session. |
| `/login` | Account / Sign in. Successful authentication restores the intended destination including validated query context; never submits onboarding/profile changes. |
| `/reset-password` | Account / Recover access. First show email request. A valid email-link entry shows new-password confirmation, not both forms at once. Manual-token entry, if still supported, is a secondary recovery aid. Request outcome stays enumeration-safe. No developer wipe guidance. |
| `/onboarding` | Account creation followed by a concise editable setup summary: program authority, equipment, availability and relevant personal inputs. All skipped/defaulted inputs are named before save. Existing-account action goes to pure sign-in. New-user questionnaire staging requires further scope approval; no claim it exists. |
| `/today` | Train / Session map. Opens today's actual scheduled occurrence, or explicit loading/rest/unavailable state. Existing occurrence and exercise identities remain authoritative. |
| `/week` | Week. Current/next local week, chosen dates, map preview, dose/spacing review, activation. “Manual/Auto” is recommendation convenience, never a mode badge named “custom.” |
| `/customize` | Programs / Customized workspace. Explicit inputs, exact inventory, original preview and workload comparison. Version-bound acceptance and activation remain separate. Active plan exposes Date changes and Replacement as different operations. |
| `/generated-onboarding` | Programs / Legacy preferences reference. Clear current-workflow link; do not imply archived preferences change the current original pilot. Compatibility route remains available. |
| `/history` | History / Calendar and evidence. Includes recorded sessions, receipts, correction history, comparable exercise analytics. No-record rest days are not “missed.” |
| `/checkin` | Check-In / Weekly review, available on any day. Saves bodyweight/nutrition/adherence/notes with explicit units and meanings; hands off to Week without implicitly activating dates. |
| `/settings` | More / Settings on mobile, persistent Settings on desktop. Account, units, equipment, constraints and accessibility are separate editor scopes. No unrelated data cleared by a narrow save. |
| `/guides` | Guides / Library, available in More and desktop rail. |
| `/guides/[programId]` | Guides / Program with visible phase selection and program identity. |
| `/guides/[programId]/phase/[phaseId]` | Guides / Phase, with authored source lineage retained. |
| `/guides/[programId]/phase/[phaseId]/day/[dayIndex]` | Guides / Day, meaningful source order and relationships retained. |
| `/guides/[programId]/day/[dayIndex]` | Compatibility entry into the same day-guide presentation; do not guess missing phase identity. |
| `/guides/[programId]/exercise/[exerciseId]` | Guides / Exercise. Visible prescription, relevant source notes, demo, return to exact session/exercise. No raw JSON wall. |
| `/programs/[id]` | Compatibility program-guide entry into Programs/Guides. Preserve valid links before any migration. |

Mobile bottom navigation is Home, Train, Week, History, More. More contains Check-In, Programs, Equipment, Guides, Settings and Account. It is a real labeled sheet/page, not an unlabeled overflow icon. Desktop displays these places in the persistent rail. This prioritizes the frequent loop without making program and account tools undiscoverable.

## Interaction and state transitions

### Stable working-set composer

The pair of mobile mockups 10/11 is intentionally geometrically identical at the next action. Composer rectangle: `(16,470,358,282)`. Load field: **`(32,531,147,52)`**. Reps field: **`(195,531,163,52)`**. Effort controls: y=619; primary action: `(32,675,326,48)`. The receipt/status region always occupies `(16,351,358,99)`. Acknowledgement changes content in that region and the set ordinal, not its height.

Desktop 03/04 preserves composer `(570,474,502,346)`, load **`(594,552,215,64)`**, reps **`(829,552,219,64)`** and action `(594,736,454,48)`. Effective receipts appear only in the evidence pane at x=1100; growing evidence scrolls independently. This directly addresses the rendered 90 px input displacement without deleting canonical receipts or retry identity.

The main before/after comparison is deliberately **unpaired**, so set 1 → set 2 in the same exercise does not invent a pair policy. Mobile 26 is a separate source-pair fixture: the sample source specifies A1 followed by A2, and its next composer correctly selects A2 set 1. Desktop acknowledgement also changes navigator progress from 0/3 to 1/3.

1. Select an exercise in the map. It becomes the visible workspace; any draft remains scoped to the exercise occurrence. Source sets, nonnumeric targets, effort scale, intensity technique and pair/primer position stay visible.
2. Enter actual load/reps. Prescribed RPE/RIR is never copied into actual effort. Blank remains unknown. A suggested working load is labeled as suggested and uses the server-owned explanation; a manual baseline is never promoted to a qualified recommendation.
3. **Save:** freeze the exact attempted values and operation identity; field region becomes read-only while confirming. Keep focus on the action/status area, not document body. The pending screen displays the frozen attempted load/reps and no receipt.
4. **Acknowledged:** add exactly one effective receipt; update next-set ordinal and owned guidance without moving the field rectangles. Announce “Set 1 confirmed; set 2 ready.” Restore focus to the expected editable field unless the user has intentionally moved elsewhere. Do not hold the primary acknowledgement hostage to a secondary analytics/progress fetch.
5. **Uncertain response:** keep the exact frozen attempt, show an inline explanation in the same workspace and offer “Retry the same set.” Retry cannot send newly visible edited values under the old operation identity. Editing is disabled until the uncertain command is reconciled; do not invent a cancellation guarantee.
6. **Rejected/invalid:** distinguish explicit rejection from unknown acknowledgement. Show field-specific validation and permit a reviewed new attempt only under the current owner’s protocol. Never claim a set was saved optimistically.
7. **Rest:** a fixed context slot shows remaining time and the source rest range. A countdown is not measured actual rest. Implementation would need a qualified deadline/resume model; the design does not establish background-timer correctness. Timer expiry must say rest target reached, not reset to a fresh full duration.
8. **Correct/undo:** select the receipt in evidence; correction replaces the evidence editor, not the next-set composer. Preview old→new values, keep unknown effort unknown, submit under existing correction identity and wait for acknowledgement. Undo is available only for the **latest eligible record**, consistent with the existing undo-last-set API. Older historical receipts offer correction only; this design does not introduce arbitrary receipt deletion. Mobile 14 explicitly labels its fixture as the latest eligible receipt. Undo names the record that will cease to count and does not silently erase history. Show any failure inside the active workspace.

**Source-specific distinctions:** Authored Phase 1 and Phase 2 have separate source identity. AMRAP stays AMRAP; set-specific targets and techniques retain source wording. Superset/primer relationships remain visible on the map and cannot be reordered by navigation. The Customized example uses RIR and its accepted version’s targets; it is not an Authored RPE relabeling. Guided source substitutions still require their explicit confirmation, preserve the source slot, and leave declined conflicts unresolved.

### First-load choice — explicitly proposed capability

Mobile 08 proposes a clearer entry into three evidence paths; it does not activate the existing legacy calculator for Authored. Manual load is simply the user's actual planned input. A recent-set path asks for date, reps, load, unit, setup and effort if known. A known-1RM path records a historical observation with source/date/setup; no maximum testing is requested. Neither evidence path computes a number in these designs. Admitting it into an Authored working-load or warm-up recommendation requires a separately authorized, deterministic decision owner and qualified contract. No formula, percentage, confidence score, invented history or scientific endorsement is introduced.

### Planning and consent

Week first shows total preserved work and the distribution across actual chosen dates. The synthetic compression board uses 48 total sets over five versus three dates to show arithmetic burden only; it makes no training-effect claim. Expanded date columns expose complete exercise order, pairs, effort and technique. Activation follows this evidence. Timezone is presented as a familiar place label with a searchable timezone editor; storage still uses a validated IANA identifier.

Customized input changes invalidate the reviewed preview and acknowledgement. Review acceptance shows the exact version and full differences. Mobile 06 and desktop 05 depict an **unchecked** acknowledgement with a visibly disabled Accept action. Date, workload comparison and uncertainty remain visible before checking it. Accept does not activate automatically. Date-only amendments retain the exact program and frozen dates; replacement requires new consent and respects started/recorded work. None of these operations grants Authored mutation permission.

### Loading, empty, error and account state

The Home and Train workspace must distinguish: **loading**, **rest day with a saved schedule**, **no schedule yet**, **unavailable request**, and **expired session**. During loading show a stable skeleton map and text, never “No workout loaded” or “Ready to train.” API errors do not become empty libraries or green Online. Unavailable requests have Retry without suggesting regeneration. Authentication recovery returns to the intended place; it never overwrites a profile. Save success/failure stays beside the relevant editor, independent of developer gating. Sign-out clears account-scoped transient evidence and returns to welcome under the app's session/cache authority.

### History and analytics

Calendar placement uses actual weekday slots, preserving blank leading positions and date positions while filters dim irrelevant cells. Distinguish scheduled/unstarted, partial, complete, rest and unknown; “missed” needs a real scheduled obligation and qualified policy. A session is not complete because one set exists. Receipt rows show actual unit/basis, reps, effort unknown when absent, warm-up/work kind and correction status. Comparable-trend eligibility is stated explicitly; insufficient data produces no trend claim. Adherence is called adherence, never renamed readiness. Set counts describe work, not growth.

## Accessibility and input behavior

- Use semantic page landmarks and a skip-to-composer link. Desktop panes have headings and a deliberate DOM reading order: source context, composer, evidence; visual position does not create an inaccessible order.
- Map items are buttons/links with exercise, ordinal and progress in their accessible name; selected item exposes `aria-current` or equivalent. Color is never the only meaning. Source pair relationships have text labels.
- Every editable input has a persistent label, unit and basis. Numeric inputs use appropriate decimal keyboards; actual RPE/RIR remains optional and explicit. Authentication fields have email/password autocomplete semantics.
- All primary/touch targets are at least 44 px; desktop small link targets get sufficient hit area. Standard focus indication uses a high-contrast outline with offset, not a glow alone.
- Pending and acknowledged transitions use a polite status region. Errors use concise announcements near the relevant action. Do not announce the entire changing receipt pane on every timer tick.
- Evidence, guide or More sheets on mobile have dialog semantics only when modal: contain focus, provide a labeled close action, close with Escape, and restore focus to the originating control. A full-page exercise workspace need not pretend to be a modal.
- Keyboard sequence from map → source details → composer → evidence remains stable. Saving does not remount fields. Correction changes restore focus to the receipt's Edit action after success/cancel, not the next set by surprise.
- With the on-screen keyboard, pin the composer to the visual viewport and allow its surrounding context to compress/scroll; do not cover inputs with dock or rest card. Visual viewport geometry and physical-device behavior require qualification. The SVGs depict keyboard-closed review states.
- At narrow screens the three desktop panes become a compact map, composer and separate evidence view. At zoom/large-text sizes, use a linear document layout rather than forcing fixed pixel heights; stable action position means stable within the usable viewport, not clipping content.
- Reduced motion disables animated map movement and panel transitions. No essential status uses animation. Intended palettes need measured contrast checks in actual implementation; these artifacts do not claim WCAG qualification.

## Advantages, tradeoffs and scope

**Advantages:** repeated set entry has stable spatial memory; source intent remains close; receipts stay singular and inspectable; desktop space is used for meaningful context; planning can compare workload without hiding the core consequence; the same app places provide a coherent route from equipment to consent to training to history.

**Tradeoffs:** a persistent map is denser than a guided single-task experience and may need a short first-use introduction. Mobile cannot show all three panes simultaneously; evidence requires an extra tap. An always-visible map can distract a novice, while advanced lifters benefit from direct access. Independent scrolling needs careful focus/scroll restoration. Rich desktop composition means additional responsive qualification, not automatic desktop parity.

**Presentation-only candidates:** semantic labels, visible inline errors, truthful loading/empty states, source-preserving hierarchy, fixed receipt slots, familiar navigation labels and separate account sign-in presentation.

**Requires separately authorized behavior/contracts:** fixing profile replacement and constraint clearing, persisted display-unit/accessibility preferences, no-side-effect weekly-review changes, new first-load evidence admission, account/session controls if API support is missing, corrected calendar completion semantics, timer persistence and any new correction/history projection. Design approval does not authorize these implementations.

The package stops at AUDIT → SKETCH → PRESENT. No app code, source program, database, API behavior, production service or deployment was changed. Root owns raster screenshot review and Figma publication; neither is claimed by this subagent.


## Review corrections incorporated

Root's rendered review identified right-edge title overflow, overlapping wordmark text, stale after-save navigator count, adjacent unseparated correction controls and ambiguity in paired sequencing. The revised assets shorten/scale mobile titles, separate wordmark text, show 1/3 after acknowledgement, use distinct 44 px Correct/Undo buttons, and make the main logging sample unpaired with a separate source-pair screen. Reviewer feedback also constrained historical Undo to the latest eligible receipt. Product copy now says Saved sets and Set 1 saved; technical idempotency language stays in this specification.

Structural authoring checks parsed all 32 SVGs successfully, verified the requested dimensions, native title/description metadata and the same before/after input rectangles. This is asset validation, not application or accessibility qualification. The root agent owns the final raster/browser visual review and Figma publishing.

Final targeted polish: mobile 19 displays the unambiguous observation date **Oct 6, 2026**. Mobile 25 uses a guest account shell with no signed-in dock or avatar; its Back to sign in action remains visible. These were direct SVG edits after authoring-source generation; the SVGs are the final review artifacts.
