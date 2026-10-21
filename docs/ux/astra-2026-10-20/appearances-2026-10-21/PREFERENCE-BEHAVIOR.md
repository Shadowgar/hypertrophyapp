# Appearance preference behavior — Proposed design

Design-only review, 2026-10-21. [Appearance overview](README.md) · [Settings mockups](SETTINGS.md). This document proposes behavior; it does not establish existing implementation, qualification, approval of layout/typography, or permission to implement/deploy. The active product contract preserves authored/generated prescription authority and training history. Appearance has no authority to change those records or decisions.

## Independent settings and six visual results

Settings exposes two separately labeled single-selection groups:

- **Theme family:** Graphite, Charcoal, Classic WorkoutApp.
- **Appearance:** Light, Dark, Follow Device Settings.

Each family has a complete Light and Dark palette: six visual results. Follow Device Settings is a resolution rule, not a seventh palette. Family names never imply or lock appearance. Changing either group preserves the other selection. Appearance choice must be stated explicitly even when its current result happens to match another choice.

## Saved choice and local resolution

An authenticated user's saved preference is the pair `(family, appearance choice)`, shared across mobile and desktop. The effective Light/Dark result is derived locally: explicit Light or Dark wins; Follow Device Settings reads that device's current system preference. The derived result never replaces the saved choice. System appearance changes update the app only while Follow Device Settings is selected and preserve family, navigation, form input, focus and workout state.

Example: a saved Charcoal + Follow Device Settings preference renders Charcoal Light on a light-mode phone and Charcoal Dark on a dark-mode desktop. Synchronizing the choice must never synchronize one device's resolved palette into the other's account preference.

Proposed default for a genuinely unset preference: Graphite + Follow Device Settings. If a system preference is unavailable, resolve Follow Device Settings to Light while retaining Follow Device Settings as the choice. These defaults require owner acceptance.

## Editing, saving and recovery states

| State | Proposed user-visible contract |
|---|---|
| Loading | Resolve from a valid, account-scoped last-confirmed preference when available. Otherwise use the proposed default provisionally. Do not display a loading default as a confirmed saved choice, and do not write it over an existing preference. Minimize a wrong-palette flash; no zero-flash implementation claim is made. |
| Saved | Both groups identify the account's confirmed selections. Follow Device Settings additionally identifies its current local result, e.g. “Currently Dark.” |
| Preview / unsaved | Selection changes preview both choices together on this device only. Show an unsaved state with Save preferences and Restore saved. Merely viewing or previewing a family sends no account update. |
| Restore saved / leave with an unsaved draft | Restore saved discards the local preview and resolves the latest confirmed preference; it sends no server write. Back navigation with a dirty draft offers Keep editing or Discard preview. Discard preview leaves without saving; Keep editing preserves the draft. |
| Saving | Keep the preview and show “Saving…”; disable duplicate Save actions until this attempt resolves. Do not claim cross-device persistence before confirmation. |
| Save succeeds | Mark only the acknowledged preference as Saved. Other devices receive the saved choices when they refresh/synchronize; immediate live propagation is not promised by this design. |
| Definite save failure / offline before submission | Keep the draft visibly unsaved, show a concise retryable error, and provide Retry or Restore saved. Do not silently queue a later overwrite, display success, reset other settings, or touch training records. |
| Save outcome unknown | A timeout or lost response does not prove failure. Show “Save not confirmed”; retain the draft and check the latest acknowledged account preference before retrying or claiming success. Do not claim the account is unchanged after an uncertain submission. Restore saved can discard the local preview, but cannot undo a potentially completed account save; resolve the confirmed account state when available. An account cache is last-confirmed evidence, not proof of the latest server state. |
| Account preference changed elsewhere | Never let a stale draft silently overwrite a newer preference. Preserve the draft for inspection and offer “Use saved preference” or “Save my selection” against the latest state. No unrelated profile fields participate in this conflict. |

Only appearance fields may change in an appearance save. No whole-profile replacement, training-data reset, onboarding resubmission, program regeneration or history repair is a valid preference-error recovery. A late response from a previous account or superseded attempt must not change the current account's displayed or saved preference. Exact persistence/concurrency mechanisms remain outside this design task.

## Account and logged-out boundaries

Proposed: retain a last-confirmed cache scoped to the authenticated account for that account's next visit. Never borrow another account's cached preference. Signing out ends the account preview and applies a separate device-local anonymous preference (or default); anonymous choices do not write to an account. Signing in resolves the saved account preference without silently promoting an anonymous choice. Account switching clears pending drafts and prevents a previous account's response from updating the new session. Storage, retention and synchronization mechanisms require separate approval and verification.

## Shared design system scope

The proposed token artifact defines the same 23 semantic keys in all six palettes: canvas; surface, surface_raised, surface_selected; border_subtle, border_control; text_primary, text_secondary, text_muted; accent_text; action_fill, action_text; focus; success_text, warning_text, error_text, info_text; status_surface; input_fill; disabled_fill, disabled_text; selection_fill, selection_text. This is a shared vocabulary, not a claim that every component/state mapping is complete or qualified.

Proposed shared state styling should reuse these roles wherever practical: selected surfaces use surface_selected or the selection pair as appropriate; disabled controls use the disabled pair; focus uses focus; informational and outcome messages pair their text role with status_surface. Hover and pressed treatments are not dedicated keys in the current artifact. Define their consistent shared component mappings, using existing surface/border roles where sufficient, and qualify their visual distinction after layout approval. Do not invent separate implementations per family. Shared components should apply the roles consistently across Today, Week, workout execution, history, settings, authentication, dialogs, menus and transient messages. Portal content and browser-native controls also need qualification in each effective appearance.

Family-specific values express visual identity; component structure, labels, state meaning and interaction contracts stay shared. No page may invent an isolated palette or use a color change to alter prescription meaning. This contract does not approve component geometry, density, typography or the overall page layout; those require the next visual decision. Reuse of tokens and components must not imply that one family is only a renamed copy of another.

## Design acceptance assertions

- Review all six palettes on identical representative content; each family retains a recognizable identity in both Light and Dark.
- Review selected/unselected, focus, hover/pressed, disabled, loading, empty, warning, error and success states in both appearances. Selection and status remain understandable without color alone.
- Both selection groups have visible labels and a discernible selected state. Keyboard users can reach and operate each group, Save preferences, Restore saved and Retry with persistent visible focus; appearance changes do not move focus.
- Establish readable text and distinguishable controls/focus in each palette, including muted text and error states. Static contrast samples are documented in [validation](VALIDATION.md); full assistive-technology and interactive browser qualification remain future work.
- Demonstrate opposite device system appearances under one saved Follow Device Settings choice, explicit appearance ignoring system changes, family preserving appearance, failure preserving the draft, and account isolation. These are proposed acceptance examples, not test results.
