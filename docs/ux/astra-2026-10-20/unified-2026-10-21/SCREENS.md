# Proposed behavior, screen by screen

[Mobile gallery](MOBILE.md) · [Desktop gallery](DESKTOP.md) · [Audit trace](TRACEABILITY.md)

All behaviors are design requirements. No runtime capability or release acceptance follows from these drawings. Example prescriptions and values are synthetic; actual source values must be rendered without reinterpretation.

## 01-welcome — Ready for your next session?

[Mobile PNG](mobile/01-welcome.png) · [Mobile SVG](mobile/01-welcome.svg) · [Desktop PNG](desktop/01-welcome.png) · [Desktop SVG](desktop/01-welcome.svg)

Create account starts a new draft setup. Sign in opens the dedicated account flow without writing profile or training preferences.

Audit references: F01, F12, F18, F24.

## 02-sign-in — Welcome back

[Mobile PNG](mobile/02-sign-in.png) · [Mobile SVG](mobile/02-sign-in.svg) · [Desktop PNG](desktop/02-sign-in.png) · [Desktop SVG](desktop/02-sign-in.svg)

Use persistent email/password labels, a 48px Show password control and one submit. Pending disables duplicate sign-in. Successful authentication preserves the full safe return path and query without onboarding writes; inline failure retains email.

Audit references: F01, F17, F18.

## 03-account-recovery — Reset your password

[Mobile PNG](mobile/03-account-recovery.png) · [Mobile SVG](mobile/03-account-recovery.svg) · [Desktop PNG](desktop/03-account-recovery.png) · [Desktop SVG](desktop/03-account-recovery.svg)

Request and token confirmation are separate stages. Use the same neutral email result for matching/nonmatching addresses; a used or expired link offers a fresh request. No wipe or developer operation appears here.

Audit references: F12, F17.

## 04-new-account — Make it yours

[Mobile PNG](mobile/04-new-account.png) · [Mobile SVG](mobile/04-new-account.svg) · [Desktop PNG](desktop/04-new-account.png) · [Desktop SVG](desktop/04-new-account.svg)

Create only a new account after explicit submit; do not choose a program or run generation as a hidden authentication side effect. Existing accounts route to sign-in.

Audit references: F01, F17, F24.

## 05-choose-program — How would you like to train?

[Mobile PNG](mobile/05-choose-program.png) · [Mobile SVG](mobile/05-choose-program.svg) · [Desktop PNG](desktop/05-choose-program.png) · [Desktop SVG](desktop/05-choose-program.svg)

Explain Authored versus Customized before mode-dependent questions. Help me choose can recommend but cannot supply Customized consent or overwrite an Authored template.

Audit references: F13, F24.

## 06-authored-program — Full Body Phase 1

[Mobile PNG](mobile/06-authored-program.png) · [Mobile SVG](mobile/06-authored-program.svg) · [Desktop PNG](desktop/06-authored-program.png) · [Desktop SVG](desktop/06-authored-program.svg)

Selecting Phase 1 does not merge it with Phase 2 or generate an original plan. Source guide and provenance remain accessible. Selection leads to setup and dated preview, not silent activation.

Audit references: F13, F24, F28.

## 07-setup-basics — A few essentials

[Mobile PNG](mobile/07-setup-basics.png) · [Mobile SVG](mobile/07-setup-basics.svg) · [Desktop PNG](desktop/07-setup-basics.png) · [Desktop SVG](desktop/07-setup-basics.svg)

Collect required mode-relevant fields with explanations. Unit display is explicit (lb for an account with no prior choice); store canonical measurements unchanged. Skipped optional data remains unknown, not fabricated.

Audit references: F07, F24, F28.

## 08-equipment — Your equipment

[Mobile PNG](mobile/08-equipment.png) · [Mobile SVG](mobile/08-equipment.svg) · [Desktop PNG](desktop/08-equipment.png) · [Desktop SVG](desktop/08-equipment.svg)

Use named locations, accessible selected states and precise setup when needed. A scoped equipment change preserves all unrelated constraints and profile fields. Customized inventory changes require a new reviewed preview before replacing a plan.

Audit references: F02, F15, F26.

## 09-setup-review — Review your setup

[Mobile PNG](mobile/09-setup-review.png) · [Mobile SVG](mobile/09-setup-review.svg) · [Desktop PNG](desktop/09-setup-review.png) · [Desktop SVG](desktop/09-setup-review.svg)

Show explicit answers and omissions before the scoped profile save. A failed save preserves the setup draft and cannot show initialization success. Scheduling remains a separate preview and activation.

Audit references: F01, F02, F11, F24.

## 10-home — Your next session

[Mobile PNG](mobile/10-home.png) · [Mobile SVG](mobile/10-home.svg) · [Desktop PNG](desktop/10-home.png) · [Desktop SVG](desktop/10-home.svg)

Home prioritizes the next scheduled or in-progress occurrence and a single action. It links to Week and optional Check-In; signed-in users see no login or start-onboarding calls to action. No token-based Synced claim.

Audit references: F11, F18, F24.

## 11-home-no-schedule — Your week is open

[Mobile PNG](mobile/11-home-no-schedule.png) · [Mobile SVG](mobile/11-home-no-schedule.svg) · [Desktop PNG](desktop/11-home-no-schedule.png) · [Desktop SVG](desktop/11-home-no-schedule.svg)

Show this empty state only after an acknowledged absence of a schedule. It never substitutes for loading, auth expiry or a failed fetch. Existing history and chosen program remain available.

Audit references: F08, F11, F18.

## 12-programs — Your programs

[Mobile PNG](mobile/12-programs.png) · [Mobile SVG](mobile/12-programs.svg) · [Desktop PNG](desktop/12-programs.png) · [Desktop SVG](desktop/12-programs.svg)

Each Authored phase retains a distinct name and identity. Choosing another program enters a replacement review; it does not overwrite started occurrences or history. Auto recommendation remains separate from mode consent.

Audit references: F13, F24.

## 13-customized-consent — Build a Customized program

[Mobile PNG](mobile/13-customized-consent.png) · [Mobile SVG](mobile/13-customized-consent.svg) · [Desktop PNG](desktop/13-customized-consent.png) · [Desktop SVG](desktop/13-customized-consent.svg)

The consent checkbox starts unchecked; Agree & continue is disabled until checked. Record the reviewed consent/version under the existing authority. No inferred consent from equipment, recommendation or a preference.

Audit references: F13, F24.

## 14-customized-inputs — Shape your program

[Mobile PNG](mobile/14-customized-inputs.png) · [Mobile SVG](mobile/14-customized-inputs.svg) · [Desktop PNG](desktop/14-customized-inputs.png) · [Desktop SVG](desktop/14-customized-inputs.svg)

Raw answers map through the existing normalized GenerationProfile before generation. Display active/informational fields honestly. No generation within the visual asset; no new deterministic rule or scoring authority.

Audit references: F13, F15, F24, F28.

## 15-customized-preview — Review your program

[Mobile PNG](mobile/15-customized-preview.png) · [Mobile SVG](mobile/15-customized-preview.svg) · [Desktop PNG](desktop/15-customized-preview.png) · [Desktop SVG](desktop/15-customized-preview.svg)

Activation binds to the exact reviewed preview and consent version. Any changed input invalidates the old preview. Started/completed occurrences are preserved and replacement conflicts must be resolved explicitly.

Audit references: F13, F14, F15.

## 16-week — Your training week

[Mobile PNG](mobile/16-week.png) · [Mobile SVG](mobile/16-week.svg) · [Desktop PNG](desktop/16-week.png) · [Desktop SVG](desktop/16-week.svg)

Use local dates with weekday-aligned columns. Scheduled, started, completed and rest days use words/icons, not just color. Persistent occurrence identity survives navigation; no date compaction when filtered.

Audit references: F08, F09, F14, F28.

## 17-select-dates — Choose actual dates

[Mobile PNG](mobile/17-select-dates.png) · [Mobile SVG](mobile/17-select-dates.svg) · [Desktop PNG](desktop/17-select-dates.png) · [Desktop SVG](desktop/17-select-dates.svg)

Choose actual date values rather than merely a day count. A new selection invalidates any prior preview; timezone/local-day semantics are visible and consistent through DST. Preview does not activate.

Audit references: F09, F14, F28.

## 18-schedule-preview — Review the workload

[Mobile PNG](mobile/18-schedule-preview.png) · [Mobile SVG](mobile/18-schedule-preview.svg) · [Desktop PNG](desktop/18-schedule-preview.png) · [Desktop SVG](desktop/18-schedule-preview.svg)

Synthetic 29-set illustration is not a reproduction of the owner incident. Show source groups and totals before activation, preserve every prescribed set, do not invent duration or silently delete/reassign work.

Audit references: F14, F28.

## 19-schedule-conflict — Review the updated week

[Mobile PNG](mobile/19-schedule-conflict.png) · [Mobile SVG](mobile/19-schedule-conflict.svg) · [Desktop PNG](desktop/19-schedule-conflict.png) · [Desktop SVG](desktop/19-schedule-conflict.svg)

Detect stale revision/preview conflicts before committing. No automatic merge or replacement of started/completed history. Keep the selected dates as a draft until the user reviews a fresh owned preview.

Audit references: F11, F14.

## 20-today-loading — Opening your workout

[Mobile PNG](mobile/20-today-loading.png) · [Mobile SVG](mobile/20-today-loading.svg) · [Desktop PNG](desktop/20-today-loading.png) · [Desktop SVG](desktop/20-today-loading.svg)

Render a meaningful loading state immediately. Delayed loading is not No workout or a rest day; offer a visible status/retry path after failure without fabricated percentages or a performance claim.

Audit references: F11, F18.

## 21-today-rest — A day between sessions

[Mobile PNG](mobile/21-today-rest.png) · [Mobile SVG](mobile/21-today-rest.svg) · [Desktop PNG](desktop/21-today-rest.png) · [Desktop SVG](desktop/21-today-rest.svg)

Rest day requires a successful dated response. It has no completion penalty and does not offer misleading generation/reset actions.

Audit references: F08, F11, F16.

## 22-today-unavailable — We couldn’t open this workout

[Mobile PNG](mobile/22-today-unavailable.png) · [Mobile SVG](mobile/22-today-unavailable.svg) · [Desktop PNG](desktop/22-today-unavailable.png) · [Desktop SVG](desktop/22-today-unavailable.svg)

A failed fetch remains an error, never a rest/empty state. Any cached information is labeled with freshness; no Online or Synced claim from a token. Retry is read-only.

Audit references: F05, F11.

## 23-today-session — Workout B

[Mobile PNG](mobile/23-today-session.png) · [Mobile SVG](mobile/23-today-session.svg) · [Desktop PNG](desktop/23-today-session.png) · [Desktop SVG](desktop/23-today-session.svg)

Persistent exercise map opens a specific source slot/occurrence. Repeated names retain source grouping; selecting a slot does not silently substitute, advance or merge it. Warm-ups are counted separately.

Audit references: F03, F13, F14, F27.

## 24-starting-load — Find a starting weight

[Mobile PNG](mobile/24-starting-load.png) · [Mobile SVG](mobile/24-starting-load.svg) · [Desktop PNG](desktop/24-starting-load.png) · [Desktop SVG](desktop/24-starting-load.svg)

Three optional intake paths are distinct and discoverable. A self-report never displaces better comparable effective performance. Known max support is a proposed capability requiring approved engine admission; no browser formula.

Audit references: F03, F23, F28.

## 25-known-max — Your known 1-rep max

[Mobile PNG](mobile/25-known-max.png) · [Mobile SVG](mobile/25-known-max.svg) · [Desktop PNG](desktop/25-known-max.png) · [Desktop SVG](desktop/25-known-max.svg)

Explicitly label reported known 1RM, unit and exact setup. Qualify evidence through the existing owned engine, not local percentage math. No max test, no invented equipment equivalence, and no estimate if unsupported.

Audit references: F07, F23.

## 26-recent-set — Use a recent set

[Mobile PNG](mobile/26-recent-set.png) · [Mobile SVG](mobile/26-recent-set.svg) · [Desktop PNG](desktop/26-recent-set.png) · [Desktop SVG](desktop/26-recent-set.svg)

Keep historical self-report separate from verified effective receipts and from a known 1RM. Unknown effort remains unknown. Derived e1RM is identified as an estimate with owned basis only if supported.

Audit references: F07, F23.

## 27-manual-calibration — Start with your own weight

[Mobile PNG](mobile/27-manual-calibration.png) · [Mobile SVG](mobile/27-manual-calibration.svg) · [Desktop PNG](desktop/27-manual-calibration.png) · [Desktop SVG](desktop/27-manual-calibration.svg)

Manual calibration accepts the user’s actual attainable load without invented formulas or mandatory override reasons. It does not change authored set/rep/effort targets or claim a completed calibration before evidence exists.

Audit references: F03, F23, F27.

## 28-load-unavailable — Choose a weight manually

[Mobile PNG](mobile/28-load-unavailable.png) · [Mobile SVG](mobile/28-load-unavailable.svg) · [Desktop PNG](desktop/28-load-unavailable.png) · [Desktop SVG](desktop/28-load-unavailable.svg)

When evidence, setup, source target or attainable increments are insufficient, show a supported inability state. Do not fabricate Smith counterweight, load basis, metadata scoring or an explanatory cause.

Audit references: F23, F28.

## 29-warmup — Prescribed warm-up

[Mobile PNG](mobile/29-warmup.png) · [Mobile SVG](mobile/29-warmup.svg) · [Desktop PNG](desktop/29-warmup.png) · [Desktop SVG](desktop/29-warmup.svg)

Show exact source warm-up separately, with actual load/reps and optional effort. The illustrative 20 lb × 8 is entered work, not a new warm-up prescription. Warm-ups never advance the working-set counter.

Audit references: F03, F04, F05, F06, F07, F11, F22, F25, F27.

## 30-warmup-saved — Warm-up saved

[Mobile PNG](mobile/30-warmup-saved.png) · [Mobile SVG](mobile/30-warmup-saved.svg) · [Desktop PNG](desktop/30-warmup-saved.png) · [Desktop SVG](desktop/30-warmup-saved.svg)

Only an acknowledged warm-up gets saved status. Start working sets switches task in place; it cannot submit the warm-up again. Source warm-up details remain accessible.

Audit references: F03, F04, F05, F06, F07, F11, F22, F25, F27.

## 31-working-ready — Before Save set

[Mobile PNG](mobile/31-working-ready.png) · [Mobile SVG](mobile/31-working-ready.svg) · [Desktop PNG](desktop/31-working-ready.png) · [Desktop SVG](desktop/31-working-ready.svg)

Persistent source exercise and program, exact target, concise owned suggestion and editable actuals. Weight and reps fields are fixed; advanced guidance is one step away. The actual effort is unknown by default.

Audit references: F03, F04, F05, F06, F07, F11, F22, F25, F27.

## 32-working-pending — Save pending

[Mobile PNG](mobile/32-working-pending.png) · [Mobile SVG](mobile/32-working-pending.svg) · [Desktop PNG](desktop/32-working-pending.png) · [Desktop SVG](desktop/32-working-pending.svg)

Freeze the immutable attempted payload and disable duplicate submit; preserve focus/scroll. Reserved status changes without inserting a new block. Pending never increases confirmed count or starts a confirmed rest.

Audit references: F03, F04, F05, F06, F07, F11, F22, F25, F27.

## 33-working-saved — Set saved and rest

[Mobile PNG](mobile/33-working-saved.png) · [Mobile SVG](mobile/33-working-saved.svg) · [Desktop PNG](desktop/33-working-saved.png) · [Desktop SVG](desktop/33-working-saved.svg)

After authoritative acknowledgement, the reserved region announces Set 1 saved and a rest timer once. Set 2 composer occupies exactly the same coordinates, with retained weight and blank reps. Its Save stays disabled until valid reps. Receipt actuals appear only in Recorded sets.

Audit references: F03, F04, F05, F06, F07, F11, F22, F25, F27.

## 34-working-next — Continue to the next set

[Mobile PNG](mobile/34-working-next.png) · [Mobile SVG](mobile/34-working-next.svg) · [Desktop PNG](desktop/34-working-next.png) · [Desktop SVG](desktop/34-working-next.svg)

After rest expires, keep the same fields and allow the next actual set. Timer is a deadline-based aid, not automatic work; expiry never resets itself or auto-saves. Any source sequence restriction is preserved.

Audit references: F03, F04, F05, F06, F07, F11, F22, F25, F27.

## 35-working-failed — Definite save failure

[Mobile PNG](mobile/35-working-failed.png) · [Mobile SVG](mobile/35-working-failed.svg) · [Desktop PNG](desktop/35-working-failed.png) · [Desktop SVG](desktop/35-working-failed.svg)

This example is a definite failure before send, so retry may submit the retained attempt. Server validation rejection has a separate field-error state. Feedback remains within the current runner.

Audit references: F03, F04, F05, F06, F07, F11, F22, F25, F27.

## 36-working-unconfirmed — Save outcome unknown

[Mobile PNG](mobile/36-working-unconfirmed.png) · [Mobile SVG](mobile/36-working-unconfirmed.svg) · [Desktop PNG](desktop/36-working-unconfirmed.png) · [Desktop SVG](desktop/36-working-unconfirmed.svg)

Timeout after send is not a definite failure. Lock the attempted values, reconcile by command identity, and allow only same-payload retry when safe. Do not advance or label the set saved until confirmed.

Audit references: F03, F04, F05, F06, F07, F11, F22, F25, F27.

## 37-working-resume — Reconcile after returning

[Mobile PNG](mobile/37-working-resume.png) · [Mobile SVG](mobile/37-working-resume.svg) · [Desktop PNG](desktop/37-working-resume.png) · [Desktop SVG](desktop/37-working-resume.svg)

Load effective occurrence receipts and reconcile a pending command before deciding the next set. Show held draft separately from confirmed evidence. Old account/occurrence responses cannot update this screen.

Audit references: F03, F04, F05, F06, F07, F11, F22, F25, F27.

## 38-effort — How hard was that set?

[Mobile PNG](mobile/38-effort.png) · [Mobile SVG](mobile/38-effort.svg) · [Desktop PNG](desktop/38-effort.png) · [Desktop SVG](desktop/38-effort.svg)

For Authored, retain native RPE with a plain explanation. For a native RIR target, ask How many more reps could you have done? and retain RIR. Do not silently convert or prefill effort. Before-save attaches to draft; after-save is an explicit receipt update.

Audit references: F03, F20, F28.

## 39-load-details — Why this suggestion?

[Mobile PNG](mobile/39-load-details.png) · [Mobile SVG](mobile/39-load-details.svg) · [Desktop PNG](desktop/39-load-details.png) · [Desktop SVG](desktop/39-load-details.svg)

Display only the responsible engine’s actual inputs, basis and reason. When the engine supplies no reason, say reason unavailable instead of inventing a causal explanation. Suggestions never overwrite entered actuals.

Audit references: F03, F06, F23, F28.

## 40-recorded-sets — Recorded sets

[Mobile PNG](mobile/40-recorded-sets.png) · [Mobile SVG](mobile/40-recorded-sets.svg) · [Desktop PNG](desktop/40-recorded-sets.png) · [Desktop SVG](desktop/40-recorded-sets.svg)

The sole ordered effective receipt list includes units, kind, actual effort and explicit correction actions. On mobile it opens from the fixed composer; on desktop it occupies the evidence column. No duplicated value list above the composer.

Audit references: F04, F07, F20.

## 41-correct-set — Correct working set 1

[Mobile PNG](mobile/41-correct-set.png) · [Mobile SVG](mobile/41-correct-set.svg) · [Desktop PNG](desktop/41-correct-set.png) · [Desktop SVG](desktop/41-correct-set.svg)

Name the exact effective receipt, original actuals and proposed replacements. Acknowledge before changing effective count/values and recomputing owned guidance. Preserve the correction chain and return focus to the invoking receipt.

Audit references: F05, F06, F20, F25.

## 42-correction-pending — Saving your correction

[Mobile PNG](mobile/42-correction-pending.png) · [Mobile SVG](mobile/42-correction-pending.svg) · [Desktop PNG](desktop/42-correction-pending.png) · [Desktop SVG](desktop/42-correction-pending.svg)

Correction pending does not optimistically replace authoritative evidence. Same-command reconciliation applies to uncertain responses; duplicate correction submit stays disabled.

Audit references: F05, F06, F20.

## 43-correction-confirmed — Correction saved

[Mobile PNG](mobile/43-correction-confirmed.png) · [Mobile SVG](mobile/43-correction-confirmed.svg) · [Desktop PNG](desktop/43-correction-confirmed.png) · [Desktop SVG](desktop/43-correction-confirmed.svg)

After acknowledgement, the effective receipt and dependent guidance refresh from authority. The original 12-rep record remains inspectable in history; no duplicate effective row is inserted.

Audit references: F04, F20.

## 44-undo-confirm — Undo working set 2?

[Mobile PNG](mobile/44-undo-confirm.png) · [Mobile SVG](mobile/44-undo-confirm.svg) · [Desktop PNG](desktop/44-undo-confirm.png) · [Desktop SVG](desktop/44-undo-confirm.svg)

Confirm exact set, kind and actuals. Undo is a void of the effective record, not physical deletion. Warm-up undo must be separately named; no blanket undo across a different occurrence.

Audit references: F06, F20.

## 45-undo-pending — Undoing working set 2

[Mobile PNG](mobile/45-undo-pending.png) · [Mobile SVG](mobile/45-undo-pending.svg) · [Desktop PNG](desktop/45-undo-pending.png) · [Desktop SVG](desktop/45-undo-pending.svg)

Do not decrement effective count or discard history on a pending undo. Ambiguous outcome uses the same immutable request reconciliation and visible recovery region as logging.

Audit references: F05, F06, F20.

## 46-undo-confirmed — Working set 2 undone

[Mobile PNG](mobile/46-undo-confirmed.png) · [Mobile SVG](mobile/46-undo-confirmed.svg) · [Desktop PNG](desktop/46-undo-confirmed.png) · [Desktop SVG](desktop/46-undo-confirmed.svg)

Rebuild current set and load guidance from effective acknowledged evidence. Preserve the voided record and command chain. No stale local counter can revive it on reload.

Audit references: F06, F20.

## 47-pair-technique — Follow this exercise pair

[Mobile PNG](mobile/47-pair-technique.png) · [Mobile SVG](mobile/47-pair-technique.svg) · [Desktop PNG](desktop/47-pair-technique.png) · [Desktop SVG](desktop/47-pair-technique.svg)

Entirely fictional pair/technique fixture, not an assertion about an Authored source. Actual rendering preserves the original paired exercise identities, order, exact set-specific effort/rest and technique targets; technique-child actuals remain attached to the parent working set and never add ordinary completion count.

Audit references: F03, F14, F27, F28.

## 48-substitution — Review the exercise change

[Mobile PNG](mobile/48-substitution.png) · [Mobile SVG](mobile/48-substitution.svg) · [Desktop PNG](desktop/48-substitution.png) · [Desktop SVG](desktop/48-substitution.svg)

No substitute is invented by the sketch. An available owned/source-approved option requires an explicit confirmation naming original and performed variant before use. Constraints alone grant no prescription mutation.

Audit references: F13, F20, F28.

## 49-finish-review — Review before finishing

[Mobile PNG](mobile/49-finish-review.png) · [Mobile SVG](mobile/49-finish-review.svg) · [Desktop PNG](desktop/49-finish-review.png) · [Desktop SVG](desktop/49-finish-review.svg)

Only effective working-set evidence drives completion. A partial finish is explicitly labeled and confirmed; an unresolved save blocks finalization until reconciled. Warm-ups and technique children do not satisfy working completion.

Audit references: F08, F11, F20.

## 50-workout-complete — Workout complete

[Mobile PNG](mobile/50-workout-complete.png) · [Mobile SVG](mobile/50-workout-complete.svg) · [Desktop PNG](desktop/50-workout-complete.png) · [Desktop SVG](desktop/50-workout-complete.svg)

Completion is explicit and acknowledged. No new week, program replacement or generation is triggered by finishing. Unknown timing/energy/calorie metrics are not fabricated.

Audit references: F08, F11, F20.

## 51-history — Your training history

[Mobile PNG](mobile/51-history.png) · [Mobile SVG](mobile/51-history.svg) · [Desktop PNG](desktop/51-history.png) · [Desktop SVG](desktop/51-history.svg)

Calendar retains true weekday positions under filters. Distinguish scheduled-not-done, partial, complete, rest and unknown; no blanket Missed label for dates without data. Select date/occurrence before loading detail.

Audit references: F08, F09, F20, F21.

## 52-history-detail — Wednesday 21 October

[Mobile PNG](mobile/52-history-detail.png) · [Mobile SVG](mobile/52-history-detail.svg) · [Desktop PNG](desktop/52-history-detail.png) · [Desktop SVG](desktop/52-history-detail.svg)

Every receipt has units, kind, effort, source identity and effective correction status. Historical write controls are shown only where current authority permits; audit/provenance remains readable regardless. No new historical editing permission is implied.

Audit references: F07, F20, F21.

## 53-history-loading — Monday 19 October

[Mobile PNG](mobile/53-history-loading.png) · [Mobile SVG](mobile/53-history-loading.svg) · [Desktop PNG](desktop/53-history-loading.png) · [Desktop SVG](desktop/53-history-loading.svg)

Key result application to account/date/occurrence and current request. Clear or explicitly label stale details during selection; a late response cannot silently show another day under the current header.

Audit references: F11, F21.

## 54-analytics — See your progress

[Mobile PNG](mobile/54-analytics.png) · [Mobile SVG](mobile/54-analytics.svg) · [Desktop PNG](desktop/54-analytics.png) · [Desktop SVG](desktop/54-analytics.svg)

Use user-facing exercise names, explicit units, date ranges and comparable setup filters. A weight trend is not proof of muscle growth or readiness. Tables provide the same values; uncertainty and missing evidence stay visible.

Audit references: F07, F20, F21, F28.

## 55-analytics-empty — More training will tell the story

[Mobile PNG](mobile/55-analytics-empty.png) · [Mobile SVG](mobile/55-analytics-empty.svg) · [Desktop PNG](desktop/55-analytics-empty.png) · [Desktop SVG](desktop/55-analytics-empty.svg)

No invented trend, score or adherence-as-readiness label with insufficient data. Distinguish empty evidence from loading/fetch failure and offer the factual record.

Audit references: F08, F11, F21.

## 56-check-in — How are you feeling?

[Mobile PNG](mobile/56-check-in.png) · [Mobile SVG](mobile/56-check-in.svg) · [Desktop PNG](desktop/56-check-in.png) · [Desktop SVG](desktop/56-check-in.svg)

Show units and unknown optional values. Explain review scope without invented causal claims or automatic Authored prescription changes. Separate saving the review from selected-date scheduling/any separately authorized planning action.

Audit references: F07, F16, F28.

## 57-check-in-saved — Your check-in is saved

[Mobile PNG](mobile/57-check-in-saved.png) · [Mobile SVG](mobile/57-check-in-saved.svg) · [Desktop PNG](desktop/57-check-in-saved.png) · [Desktop SVG](desktop/57-check-in-saved.svg)

Acknowledge review separately from plan activation. If owned review outputs are unavailable, say so; never translate Load Scale into an invented causal story or silently generate a week.

Audit references: F11, F16, F28.

## 58-settings — Settings

[Mobile PNG](mobile/58-settings.png) · [Mobile SVG](mobile/58-settings.svg) · [Desktop PNG](desktop/58-settings.png) · [Desktop SVG](desktop/58-settings.svg)

Put appearance and units in normal Settings, not Developer Tools. All saves show pending/success/failure beside the affected control. Separate equipment/profile/mode/preferences write scopes; no whole-profile overwrite.

Audit references: F02, F07, F10, F15, F18, F26.

## 59-appearance — Theme and appearance

[Mobile PNG](mobile/59-appearance.png) · [Mobile SVG](mobile/59-appearance.svg) · [Desktop PNG](desktop/59-appearance.png) · [Desktop SVG](desktop/59-appearance.svg)

Two independent account preferences: Theme family and Appearance (Light, Dark, Follow Device Settings). Family changes retain appearance. Preview is local, Save requires acknowledgement, Restore saved discards the local preview. Existing unconfigured accounts retain Classic WorkoutApp Dark. This baseline preserves the familiar look without a forced introduction.

Audit references: F10, F18, F19, F26.

## 60-appearance-preview — Unsaved appearance preview

[Mobile PNG](mobile/60-appearance-preview.png) · [Mobile SVG](mobile/60-appearance-preview.svg) · [Desktop PNG](desktop/60-appearance-preview.png) · [Desktop SVG](desktop/60-appearance-preview.svg)

Two independent account preferences: Theme family and Appearance (Light, Dark, Follow Device Settings). Family changes retain appearance. Preview is local, Save requires acknowledgement, Restore saved discards the local preview. Existing unconfigured accounts retain Classic WorkoutApp Dark. The mockup shows a dirty preview; Back offers keep editing or discard. It is not persisted on selection.

Audit references: F10, F18, F19, F26.

## 61-appearance-pending — Saving appearance

[Mobile PNG](mobile/61-appearance-pending.png) · [Mobile SVG](mobile/61-appearance-pending.svg) · [Desktop PNG](desktop/61-appearance-pending.png) · [Desktop SVG](desktop/61-appearance-pending.svg)

Two independent account preferences: Theme family and Appearance (Light, Dark, Follow Device Settings). Family changes retain appearance. Preview is local, Save requires acknowledgement, Restore saved discards the local preview. Existing unconfigured accounts retain Classic WorkoutApp Dark. Freeze the intended pair and disable duplicate save. Follow Device Settings remains a stored choice, not the currently resolved mode.

Audit references: F10, F18, F19, F26.

## 62-appearance-failed — Appearance save failed

[Mobile PNG](mobile/62-appearance-failed.png) · [Mobile SVG](mobile/62-appearance-failed.svg) · [Desktop PNG](desktop/62-appearance-failed.png) · [Desktop SVG](desktop/62-appearance-failed.svg)

Two independent account preferences: Theme family and Appearance (Light, Dark, Follow Device Settings). Family changes retain appearance. Preview is local, Save requires acknowledgement, Restore saved discards the local preview. Existing unconfigured accounts retain Classic WorkoutApp Dark. Definite failure retains the local preview and permits retry. An uncertain write is reconciled before a new write; no false saved claim.

Audit references: F10, F18, F19, F26.

## 63-appearance-saved — Appearance saved

[Mobile PNG](mobile/63-appearance-saved.png) · [Mobile SVG](mobile/63-appearance-saved.svg) · [Desktop PNG](desktop/63-appearance-saved.png) · [Desktop SVG](desktop/63-appearance-saved.svg)

Two independent account preferences: Theme family and Appearance (Light, Dark, Follow Device Settings). Family changes retain appearance. Preview is local, Save requires acknowledgement, Restore saved discards the local preview. Existing unconfigured accounts retain Classic WorkoutApp Dark. Show one confirmation after acknowledgement. Other signed-in devices apply the account pair and resolve device-following appearance independently.

Audit references: F10, F18, F19, F26.

## 64-account-accessibility — Account & accessibility

[Mobile PNG](mobile/64-account-accessibility.png) · [Mobile SVG](mobile/64-account-accessibility.svg) · [Desktop PNG](desktop/64-account-accessibility.png) · [Desktop SVG](desktop/64-account-accessibility.svg)

Visible sign-out clears account-scoped cached preferences/drafts after resolving active work. Support device text size, reduced motion and keyboard focus. Account deletion/developer resets do not appear as ordinary recovery actions.

Audit references: F12, F17, F18, F25, F26.

## 65-library — Program library

[Mobile PNG](mobile/65-library.png) · [Mobile SVG](mobile/65-library.svg) · [Desktop PNG](desktop/65-library.png) · [Desktop SVG](desktop/65-library.svg)

Library is reachable from More and the desktop rail, with program→phase/day→exercise breadcrumbs. Loading/error states are honest; guides do not claim Online from a token.

Audit references: F11, F18, F28.

## 66-exercise-guide — Exercise guide

[Mobile PNG](mobile/66-exercise-guide.png) · [Mobile SVG](mobile/66-exercise-guide.svg) · [Desktop PNG](desktop/66-exercise-guide.png) · [Desktop SVG](desktop/66-exercise-guide.svg)

Preserve licensed source content and guide routing without republishing proprietary instructions in the synthetic sketch. No raw JSON in the main reading path; technical provenance stays accessible.

Audit references: F18, F27, F28.

## 67-more-navigation — More

[Mobile PNG](mobile/67-more-navigation.png) · [Mobile SVG](mobile/67-more-navigation.svg) · [Desktop PNG](desktop/67-more-navigation.png) · [Desktop SVG](desktop/67-more-navigation.svg)

Mobile Home/Today/Week/History remain persistent; More provides the same destinations as desktop rail. Return to the active workout without losing its occurrence or draft context.

Audit references: F18, F19.

## 68-recovered-draft — You have an unfinished entry

[Mobile PNG](mobile/68-recovered-draft.png) · [Mobile SVG](mobile/68-recovered-draft.svg) · [Desktop PNG](desktop/68-recovered-draft.png) · [Desktop SVG](desktop/68-recovered-draft.svg)

Offer account/occurrence-scoped draft recovery only when durable local storage was actually successful and server reconciliation confirms its state. Do not promise offline saving or cross-device draft sync. Discard affects only that local draft.

Audit references: F06, F11, F20.

## 69-working-validation — Correct an invalid entry

[Mobile PNG](mobile/69-working-validation.png) · [Mobile SVG](mobile/69-working-validation.svg) · [Desktop PNG](desktop/69-working-validation.png) · [Desktop SVG](desktop/69-working-validation.svg)

A definite field rejection preserves draft and marks the invalid field. Editing creates a valid new command only after the rejected attempt is resolved; it is not an uncertain transport retry.

Audit references: F03, F04, F05, F06, F07, F11, F22, F25, F27.

## 70-preference-conflict — Your preferences changed

[Mobile PNG](mobile/70-preference-conflict.png) · [Mobile SVG](mobile/70-preference-conflict.svg) · [Desktop PNG](desktop/70-preference-conflict.png) · [Desktop SVG](desktop/70-preference-conflict.svg)

A stale preference revision cannot silently overwrite a newer account choice. Re-read, show both pairs, then require an explicit replacement action. Existing account look is not reset by device resolution.

Audit references: F10, F18.

## 71-session-expired — Sign in to continue

[Mobile PNG](mobile/71-session-expired.png) · [Mobile SVG](mobile/71-session-expired.svg) · [Desktop PNG](desktop/71-session-expired.png) · [Desktop SVG](desktop/71-session-expired.svg)

Auth expiry pauses writes and preserves only a securely account-scoped local attempt where supported. Reauthenticate to the same account, then reconcile. Switching account never adopts or exposes the previous account draft.

Audit references: F01, F06, F11, F18.

## 72-program-change — Review a program change

[Mobile PNG](mobile/72-program-change.png) · [Mobile SVG](mobile/72-program-change.svg) · [Desktop PNG](desktop/72-program-change.png) · [Desktop SVG](desktop/72-program-change.svg)

Program selection and replacement are distinct. Preview exact eligible future occurrence changes, preserve all started/completed work, reject stale revisions, and require explicit activation. Never merge Phase 1/2 or reinterpret Authored as Customized.

Audit references: F13, F14, F20.

## 73-weight-display — Weight display

[Mobile PNG](mobile/73-weight-display.png) · [Mobile SVG](mobile/73-weight-display.svg) · [Desktop PNG](desktop/73-weight-display.png) · [Desktop SVG](desktop/73-weight-display.svg)

Persist the account preference and convert all inputs/outputs consistently, including 1RM, warm-up, guidance, actuals, corrections, bodyweight and charts. Preserve canonical precision. Resolve active attempt/draft before changing entry units; no silent reinterpretation.

Audit references: F07, F10, F20.

## 74-rir-effort — How many more reps?

[Mobile PNG](mobile/74-rir-effort.png) · [Mobile SVG](mobile/74-rir-effort.svg) · [Desktop PNG](desktop/74-rir-effort.png) · [Desktop SVG](desktop/74-rir-effort.svg)

Native RIR feedback remains distinct from native RPE. An optional answer belongs to the draft or an explicitly acknowledged receipt update; never derive it silently from a target or invent a cross-scale equivalence.

Audit references: F20, F28.

## 75-appearance-unconfirmed — Preference save not confirmed

[Mobile PNG](mobile/75-appearance-unconfirmed.png) · [Mobile SVG](mobile/75-appearance-unconfirmed.svg) · [Desktop PNG](desktop/75-appearance-unconfirmed.png) · [Desktop SVG](desktop/75-appearance-unconfirmed.svg)

An uncertain preference write cannot be described as definitely unsaved or rolled back. Reconcile the exact account/revision/pair before allowing another write or claiming confirmed cross-device persistence.

Audit references: F10, F11.

## 76-analytics-table — The values behind the chart

[Mobile PNG](mobile/76-analytics-table.png) · [Mobile SVG](mobile/76-analytics-table.svg) · [Desktop PNG](desktop/76-analytics-table.png) · [Desktop SVG](desktop/76-analytics-table.svg)

Offer a text table with the same sampled values, range, units and series labels as the chart. This separate synthetic analytics scenario is not the illustrated 40 lb gym session. Color is not the only means of reading values.

Audit references: F07, F21.

## 77-keyboard-before — Set entry with keyboard open

[Mobile PNG](mobile/77-keyboard-before.png) · [Mobile SVG](mobile/77-keyboard-before.svg)

Illustrated reduced visual viewport with a numeric keyboard. Context condenses when the keyboard opens; fields, Save and reserved status remain reachable. A save itself does not change their coordinates or remount the inputs. Physical iOS keyboard behavior remains unqualified.

Audit references: F03, F04, F25.

## 78-keyboard-after — Saved with keyboard still open

[Mobile PNG](mobile/78-keyboard-after.png) · [Mobile SVG](mobile/78-keyboard-after.svg)

Same reduced-viewport geometry after acknowledgement. Focus stays at the reps field, next-set reps reset to blank, and Save is disabled until valid. The keyboard is not dismissed by save. This is an illustrative design requirement, not a Safari measurement.

Audit references: F04, F22, F25.
