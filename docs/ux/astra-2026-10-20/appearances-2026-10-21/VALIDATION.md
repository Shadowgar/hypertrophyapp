# Appearance design verification

**21 October 2026 · Static design artifacts only.** These checks do not establish implemented preference persistence, device-following behavior, keyboard accessibility, whole-application coverage or release acceptance.

[Appearance overview](README.md) · [Machine-readable evidence and hashes](validation.json) · [Source manifest](source-manifest.json)

## Preservation and scope

- All six maps have the same 23 semantic keys. Every dark value matches the prior neutral-dark palette exactly. The three new light maps are deliberate semantic values, not inverted colors.
- Eighteen light SVGs were compared element by element with the six corresponding source layouts and their retained dark SVGs. Element order, text, geometry, typography and all attributes except fill/stroke match. Before/after set fields therefore retain their original positions and meaning.
- The eighteen dark source SVG/PNG pairs match baseline `bc609cb1c35e24062f782e6682b93187e1893974` byte for byte. Paired boards embed those existing dark PNGs directly. No dark source asset is regenerated.
- Twelve new Settings SVGs have title/description metadata, the exact requested option labels, independent groups and visible Save/Restore controls. Their PNG dimensions match 390 × 844 mobile or 1440 × 900 desktop. Appearance rows and both actions are 48 px high; family rows/cards are larger.
- Twenty-six boards provide eighteen screen pairs, six Settings pairs, one three-light-palette board and one six-appearance status board. All 86 SVG/PNG artifacts have recorded hashes. The original 64 mockups, earlier audit/evidence, workflow documents and Figma board remain untouched.

Offline documentation check: 356 Markdown files; zero new active-link failures; 28 existing baseline exceptions retained. External URLs were not fetched by that check. Staged whitespace check is part of publication verification.

## Rendered checks

An isolated local Chromium/Playwright process rendered static files only. Libre Baskerville, DM Sans and IBM Plex Sans were loaded and awaited from the same local font files used in the prior neutral comparison. No app build, API, database or live account is involved. Font sources/licensing are recorded in the [earlier typography review](../theme-comparison-2026-10-21/TYPOGRAPHY.md). Native SVGs require the named fonts installed for matching appearance; PNGs are canonical for visual review.

Across **30 new frames and 999 text nodes**, no sampled text contrast is below 4.5:1 and no text bounding box extends outside the SVG viewport. Minimum measured text contrast is **5.10:1**. The new light-screen minima are Graphite 5.24:1, Charcoal 5.10:1 and Classic WorkoutApp 5.19:1. New Settings frames have a minimum of 5.10:1 across both appearances.

The sampler compares computed sRGB text fill with the latest preceding filled rectangle/circle containing the rendered text-bounds center, including nested transforms. It does not certify every glyph, rounded edge, overlap, anti-aliasing condition or device. An independent `gpt-6-astra` reviewer directly inspected all eighteen light screens, all twelve Settings frames and the palette/status boards; no visible overlap or conflated choice groups were found. Parent review also inspected representative final PNGs.

## Semantic contrast samples

Control and focus minima below consider adjacent canvas, panel and selected/elevated surfaces. They describe the neutral `border_control` and `focus` roles; decorative borders and brand-colored card accents are not claimed as the sole state indicator. Selected radios and explicit labels supply redundant indication.

| Appearance | Action label | Neutral control outline, minimum | Focus, minimum | Status text, minimum |
|---|---:|---:|---:|---:|
| Graphite Light | 6.68:1 | 3.83:1 | 5.40:1 | 6.10:1 |
| Graphite Dark | 9.09:1 | 3.73:1 | 8.44:1 | 7.46:1 |
| Charcoal Light | 15.52:1 | 3.73:1 | 12.21:1 | 5.74:1 |
| Charcoal Dark | 13.63:1 | 3.79:1 | 11.20:1 | 6.07:1 |
| Classic WorkoutApp Light | 6.52:1 | 3.80:1 | 5.23:1 | 6.05:1 |
| Classic WorkoutApp Dark | 5.10:1 | 3.58:1 | 7.36:1 | 7.55:1 |

Saved, warning and error have explicit words/icons plus separate status color roles. The failed-save specimen represents definite failure; a timeout or lost response needs the separate **Save not confirmed** behavior in the preference specification. No specimen is evidence of a real persisted save.

## Limits and unresolved decisions

All Settings images select Follow Device Settings and show synthetic device-resolved modes. Explicit Light/Dark interactions, system changes, account synchronization, preview cancellation, concurrent saves, retries, first-paint behavior, keyboard operation, screen readers, forced colors, text zoom and tablet reflow remain untested design requirements. Hover/pressed mappings and complete chart/browser-native control coverage remain shared-component qualification work after layout approval.

The three families are retained at the owner's direction. Overall layout and typography are not selected; this isolated Settings editor uses provisional DM Sans. Existing representative screens keep their prior typography. No application coding, dependency change, build, migration, merge, production deployment or user-data mutation occurred.
