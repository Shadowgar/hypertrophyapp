# Training Atlas — visual gallery

**Revision 2 — dark mode, 21 October 2026, requested by the owner.** All mobile and desktop frames in this gallery use the revised dark palette.

**Original Astra alternative · proposed · owner review required.** All records are fictional. No application implementation.

[Full mobile gallery — 26 frames](MOBILE.md) · [Full desktop gallery — 6 frames](DESKTOP.md) · [Interaction specification](direction.md) · [Compare directions](../../COMPARISON.md)

## Working set, before and after save

| Before save | After server acknowledgement |
|---|---|
| ![Before save: stable fields and one Save action](m10-set-before-save.png) | ![After save: confirmed receipt and rest while the input stays in place](m11-set-after-ack-rest.png) |

[Detailed current-to-proposed logging flow](../../FLOW-REVIEW.md). Confirmation changes status and set number; it does not add a new block above the fields. Pending, retry, correction and undo are separate states.

## Desktop execution

![Desktop after-save composition, with one composer and separate session context](d04-workout-after-ack.png)

[Open desktop workflow and remaining desktop sketches](DESKTOP.md). PNGs display directly on GitHub. The galleries provide alt text, written descriptions and visible-text transcripts. Native SVGs remain editable. The optional [static HTML gallery](index.html) can be downloaded with its adjacent assets and opened locally; it is not a deployed site or interactive app.
