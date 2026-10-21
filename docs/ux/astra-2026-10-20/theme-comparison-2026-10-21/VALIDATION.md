# Static comparison verification

**21 October 2026.** Verification applies only to these static artifacts, not application behavior, accessibility conformance or training calculations.

[Comparison overview](README.md) · [Machine-readable checks and artifact hashes](validation.json) · [Source manifest](source-manifest.json)

## Scope and preservation

The twelve source SVGs match baseline commit `dacfd67000fd71bf9ba8b0bba03aaa086f34248d` byte for byte. Each of the 36 palette variants was compared element by element against its source: identical element order, wording, geometry, attributes and typography after excluding only `fill` and `stroke`. Four additional typography variants match their Option 2 source after excluding only `font-family`. No original SVG/PNG, audit, evidence capture, flow specification or Figma frame is changed.

All 40 individual PNGs have the expected 390 × 844 or 1440 × 900 dimensions. Fifteen comparison PNG boards provide twelve three-theme screen comparisons, two separate typography boards and one palette/status/focus board. PNGs and SVGs have recorded hashes. No application code, dependency, service, database or deployment is involved.

Offline documentation check: 347 Markdown files, zero new active-link failures; the same 28 pre-existing baseline exceptions remain. External URLs were not fetched by that check. Git whitespace check passed.

## Rendered checks

An isolated Chromium/Playwright process rendered local static content only. Libre Baskerville, DM Sans and IBM Plex Sans were loaded from explicit local font data; each requested family/weight was awaited before capture. No network or live API responses are part of this render. The font binaries' hashes are recorded; official sources and licenses are linked in [typography provenance](TYPOGRAPHY.md).

The 40 individual frames contain **1,448 text nodes**. No text bounding box extends beyond its root SVG viewport. The sampled text contrast minima are:

| Set | Frames | Text nodes | Lowest sampled contrast |
|---|---:|---:|---:|
| 1 · Graphite | 12 | 439 | 6.63:1 |
| 2 · Charcoal | 12 | 439 | 6.16:1 |
| 3 · Black/red | 12 | 439 | 5.10:1 |
| Separate sans-heading experiment | 4 | 131 | At least 6.16:1 |

The sampler uses rendered text bounds and the most recent preceding filled rectangle/circle containing its center, accounting for nested transforms. It does not prove every glyph, rounded corner, overlap, focus interaction or device rendering is accessible. Text size is preserved from the existing layouts; this pass does not qualify enlarged-text behavior.

## Semantic colors and visual inspection

| Pair | 1 | 2 | 3 |
|---|---:|---:|---:|
| Input outline / inside | 4.76:1 | 4.92:1 | 4.76:1 |
| Input outline / adjacent raised surface | 4.21:1 | 4.27:1 | 4.26:1 |
| Week data bar / track | 4.76:1 | 4.92:1 | 4.76:1 |
| Focus ring / adjacent raised surface | 9.52:1 | 12.63:1 | 8.76:1 |
| Weakest status text / status surface | 7.46:1 | 6.07:1 | 7.55:1 |

Fine decorative borders are deliberately quieter and are not claimed to meet the control-outline threshold. Status words/icons carry meaning in addition to color. Focus is a separate specimen, not a runtime-tested state. Neutral background/elevated/selected/status surfaces have equal RGB channels. Week bars use neutral visible fills. In option 3 passive labels remain neutral; red is reserved for selected/action treatments and links.

An independent `gpt-6-astra` reviewer visually inspected all twelve screen boards, both typography boards and the palette specimen. After review, the Week bar fills were strengthened and passive red labels were neutralized; the affected boards were re-rendered and rechecked. No new clipping or spacing defects were observed. **B Home's tight “Next decision”/“Open Week” spacing is inherited and deliberately not redesigned in this theme-only pass.**

The original PNGs used system fallback fonts. The new comparisons load the named fonts consistently, so their text metrics can differ from historical exports even though source font declarations and layout coordinates remain fixed. The controlled typography boards compare actual Libre Baskerville against actual DM Sans. Native SVGs need these fonts installed; the PNGs are the canonical review appearance.

Keyboard navigation, screen readers, browser zoom, forced colors, real devices, timer behavior, saves, retries and live-data persistence were not tested. No new UX audit or application tests were run. Owner approval remains required before any full-package styling or implementation.
