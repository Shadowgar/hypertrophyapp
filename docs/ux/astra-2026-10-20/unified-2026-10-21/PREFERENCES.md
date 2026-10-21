# Theme, appearance and existing-account continuity

**Proposed behavior for a future approved implementation. No preference or account data was changed.**

## Two independent choices

| Preference | Values | Meaning |
|---|---|---|
| Theme | Graphite / Charcoal / Classic WorkoutApp | Chooses one semantic color map family. |
| Appearance | Light / Dark / Follow Device Settings | Chooses a fixed mode or lets the current device resolve its own mode. |

The stored account pair is independent of the resolved device appearance. Graphite + Follow Device Settings can be Graphite Light on one device and Graphite Dark on another. Selecting another family does not reset the appearance choice. Selecting Light or Dark stops following that device’s OS mode until the user explicitly chooses Follow again.

## Existing accounts keep their familiar look

1. Preserve any valid, explicitly saved theme/appearance pair.
2. For an existing account with no new preference, resolve to **Classic WorkoutApp + Dark**. Do not automatically choose Graphite, Light or Follow Device Settings—even if the OS is Light.
3. This compatibility fallback can be a read-time design policy; these documents authorize no migration, backfill or write. A later implementation must explicitly decide and qualify persistence mechanics.
4. Show ordinary Settings access, not a blocking first-run wizard or forced theme-selection dialog. The baseline [Settings sketch](mobile/59-appearance.png) simply says “Your familiar appearance.”
5. For a new account, the proposal also starts with Classic Dark unless the user chooses another appearance during setup or Settings. This is a proposed default, not a claim that a database migration or product release has been approved.

The prior appearance round’s proposed Graphite + Follow default is superseded **for this unified proposal** by the owner’s non-disruptive transition requirement. Old dated documents remain historical proposals, not current acceptance authority.

## Preview, save and recovery

The canonical sequence is [Classic Dark baseline](mobile/59-appearance.png) → [Graphite Dark preview](mobile/60-appearance-preview.png) → [pending](mobile/61-appearance-pending.png) → [saved](mobile/63-appearance-saved.png). The selected family and displayed palette change together in these drawings. All six family/mode variants are in the [appearance gallery](APPEARANCES.md).

- A local preview is clearly labeled unsaved and applies consistently to the current application shell. It does not write the account preference on every radio click.
- **Save preferences** freezes the intended pair, disables duplicate submit and confirms only after acknowledgement. It does not write program/equipment/profile fields.
- **Restore saved** discards the local preview without a server write. Back/navigation with a dirty preview offers keep editing or discard; it never silently persists the preview.
- A [definite failed save](mobile/62-appearance-failed.png) retains the preview and exposes retry beside the controls. An [uncertain outcome](mobile/75-appearance-unconfirmed.png) checks the exact attempted pair/revision before a new write; it does not assert that the account is unchanged.
- A [concurrent preference change](mobile/70-preference-conflict.png) shows both pairs and requires review before replacing the newer saved value.
- Follow Device Settings remains the saved choice when the OS changes. A local unsaved preview resolves using the same device mode without changing the saved pair. A device-mode change during a pending preference save does not change the frozen request.

## Persistence across mobile and desktop

The saved pair is account-owned. Signed-in sessions read the same preference on reload/login and refresh it on a defined account-preference event or next foreground refresh. The future implementation must choose and qualify that transport; these sketches do not promise real-time broadcast. The applied mode is device-local only when Follow Device Settings is selected.

Resolve a trusted account preference before painting the main app. Any cache is keyed to the authenticated account and revision; an untrusted anonymous cache cannot choose another account’s theme. Authentication loading can use a neutral branded shell rather than flash a previous account’s full UI. On logout/account switch, discard the previous account’s theme preview and draft cache. Do not promote an anonymous preview into a signed-in preference without a deliberate save.

OS switching changes colors only. It must not remount the current composer, lose focus, alter the immutable set attempt, restart rest, change display units or mutate training data. All layouts and components consume the same semantic roles; there is no theme-specific workout implementation.

## Units remain separate

[Weight display](mobile/73-weight-display.png) is a distinct persisted preference. It converts all visible/input weights consistently while preserving canonical values and historical meaning. A pending set command keeps its original values and units until reconciled; an active draft requires an explicit conversion/review, not relabeling. Theme changes never affect units, Authored/Customized mode, prescriptions, consent, equipment or History.
