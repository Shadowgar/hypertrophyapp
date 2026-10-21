# Static design validation

**Design assets only. These checks do not qualify an application implementation.**

- 208 SVG/PNG pairs: 154 canonical screens, 30 theme variants and 24 boards. PNG dimensions match SVG canvases; all SVGs parse and include review title/description.
- Chromium rendered 8,203 text nodes using the bundled DM Sans. Sampled text/background contrast minimum **4.82:1**; zero samples below 4.5:1.
- No text bounding box outside its SVG viewport; no pairwise text-box overlap in the final rendered set.
- Identical composer/status/field/action rectangles across eight working-set states at each viewport. Keyboard-open before/after rectangles also match. Exact coordinates are in [VALIDATION.json](VALIDATION.json).
- Home, before Save, after Save and desktop after Save variants retain identical text/geometry/non-color SVG attributes across all six palettes. Settings intentionally changes radio selection and resolved-device copy while using the same component layout.
- All six 23-role token maps equal the prior reviewed maps exactly. Main surface channels remain neutral (equal RGB channels).
- [Detailed render samples](RENDER-CHECKS.json) and [summary/geometry/token checks](VALIDATION.json) are included.

## Semantic contrast checks

| Appearance | Primary action text | Essential control outline minimum | Focus minimum | Status text minimum |
|---|---:|---:|---:|---:|
| graphite-light | 6.68:1 | 3.83:1 | 5.4:1 | 6.1:1 |
| graphite-dark | 9.09:1 | 3.73:1 | 8.44:1 | 7.46:1 |
| charcoal-light | 15.52:1 | 3.73:1 | 12.21:1 | 5.74:1 |
| charcoal-dark | 13.63:1 | 3.79:1 | 11.2:1 | 6.07:1 |
| classic-workoutapp-light | 6.52:1 | 3.8:1 | 5.23:1 | 6.05:1 |
| classic-workoutapp-dark | 5.1:1 | 3.58:1 | 7.36:1 | 7.55:1 |

Control/focus minima use canvas, surface, raised, selected and input backgrounds. Decorative fine borders are excluded from essential-control claims. Contrast sampling uses rendered text centers and preceding filled shapes; it is not a comprehensive WCAG audit. Color is accompanied by words/icons, and charts have a matching table.

## Visual inspection and scope

Direct image inspection covered the unified Home/Week/workout/History board; mobile and desktop logging; keyboard-open before/after; correction and starting-load boards; workload review; the theme selector; the six-palette status/focus board; and representative light and dark frames. Automated text/geometry checks cover the entire export set. This is self-review, not an independent external review.

The existing audit was not repeated. No application code, API, database, migration, server startup, production service, build or deployment was touched. Rendering read local SVGs through browser setContent. No real user records were loaded into these designs.

The offline repository documentation checker examined 367 Markdown files against baseline ff3b515: zero new active-link failures, with 28 existing baseline exceptions retained. External URLs were not fetched by that checker. Static checks do not establish focus/scroll stability, real software-keyboard behavior, screen-reader usability, request latency, timer suspension correctness, retry reconciliation, durable storage or domain regression safety. Those require a separately approved implementation and qualification.
