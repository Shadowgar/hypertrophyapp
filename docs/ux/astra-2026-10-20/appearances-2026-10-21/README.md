# WorkoutApp — three families, six appearances

**21 October 2026 · Design review only.** Retain **Graphite, Charcoal and Classic WorkoutApp**, each with Light and Dark. This follows the owner's family-retention direction; the new light palettes, Settings composition, overall layout and typography remain proposals. No application implementation or full-package regeneration is authorized.

Settings has two independent choices:

- **Theme family:** Graphite / Charcoal / Classic WorkoutApp.
- **Appearance:** Light / Dark / Follow Device Settings.

That produces six visual appearances. Follow Device Settings chooses the matching Light or Dark palette locally; it is not an extra theme. The proposed persistent account preference stores the family and the appearance choice separately. A light-mode phone and dark-mode desktop can therefore show different appearances under the same saved family.

| Review | Open |
|---|---|
| Three new light palettes, six complete token maps and shared component roles | [Palettes and semantic tokens](TOKENS.md) |
| Graphite — representative Light / Dark pairs | [Graphite gallery](GRAPHITE.md) |
| Charcoal — representative Light / Dark pairs | [Charcoal gallery](CHARCOAL.md) |
| Classic WorkoutApp — representative Light / Dark pairs | [Classic WorkoutApp gallery](CLASSIC-WORKOUTAPP.md) |
| New Settings theme selector in all six appearances, mobile and desktop | [Settings mockups](SETTINGS.md) |
| Persistence, device resolution, preview/save and failure behavior | [Proposed preference behavior](PREFERENCE-BEHAVIOR.md) |
| Text alternatives and measured checks | [Transcripts](TRANSCRIPTS.md) · [Validation](VALIDATION.md) |

![Three new light palettes: Graphite with blue action, Charcoal with dark neutral action, Classic WorkoutApp with selective red; neutral surfaces and distinct statuses](boards/light-palettes.png)

## Settings preview

The two groups remain independent. Each family row previews both Light and Dark. The example below uses Follow Device Settings on a light-mode and a dark-mode device; the selected account choice is the same in both.

![Graphite Settings editor: Light and Dark side by side with separate Theme family and Appearance groups, explicit unsaved preview and Save preferences action](boards/settings-graphite-mobile.png)

## What stays fixed

Only **six representative existing frames** are translated into each new light palette: Next Step Home and before/after set entry, plus Training Atlas before/after set entry and desktop workout. Their wording, geometry, prescription values, adaptive guidance, hierarchy and typography declarations are unchanged. The paired dark images are the existing PNGs reused unchanged, not regenerated approximations.

The new Settings editor is a portable section proposed for either overall layout direction. Its DM Sans typography is provisional. Existing screen comparisons retain their existing serif/body font declarations. The separate [typography decision](../theme-comparison-2026-10-21/TYPOGRAPHY.md) and [overall layout decision](../COMPARISON.md) are still open; retaining all three families settles neither.

This package adds 18 light screen variants, 12 Settings editor variants and 26 comparison/palette/state boards. All figures contain synthetic data. The original 64-screen package, prior dark theme assets, audit, flows and Figma board remain unchanged.

**STOP — review and approve the overall layout, typography and detailed appearance design before implementation. No application coding, merge, live-data changes or deployment.**
