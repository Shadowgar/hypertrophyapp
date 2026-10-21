# Palette details

**Proposed original themes, inspired by the requested visual references.** All dominant surface colors are neutral grey.

[Comparison overview](README.md)

![Three palettes with hex labels and separate field-focus, action, success, pending, warning and failure specimens](boards/palettes.png)

| Role | 1 · Graphite | 2 · Charcoal | 3 · Black/red |
|---|---|---|---|
| canvas | `#111111` | `#212121` | `#101010` |
| surface | `#191919` | `#292929` | `#191919` |
| surface raised | `#242424` | `#333333` | `#232323` |
| surface selected | `#2D2D2D` | `#3B3B3B` | `#303030` |
| border subtle | `#3D3D3D` | `#454545` | `#3B3B3B` |
| border control | `#858585` | `#969696` | `#858585` |
| text primary | `#F0F0F0` | `#ECECEC` | `#F5F5F5` |
| text secondary | `#BDBDBD` | `#C0C0C0` | `#C2C2C2` |
| text muted | `#A0A0A0` | `#AAAAAA` | `#A3A3A3` |
| accent text | `#79B8FF` | `#ECECEC` | `#FF858B` |
| action fill | `#79B8FF` | `#ECECEC` | `#C9383F` |
| action text | `#111111` | `#212121` | `#FFFFFF` |
| focus | `#A5CEFF` | `#FFFFFF` | `#FFABB0` |
| success text | `#8ED6A2` | `#8ED6A2` | `#8ED6A2` |
| warning text | `#EBC17A` | `#EBC17A` | `#EBC17A` |
| error text | `#FF969B` | `#FF969B` | `#FF969B` |
| info text | `#A6CAFF` | `#A6CAFF` | `#A6CAFF` |
| status surface | `#242424` | `#333333` | `#232323` |
| input fill | `#191919` | `#292929` | `#191919` |
| disabled fill | `#2D2D2D` | `#3B3B3B` | `#303030` |
| disabled text | `#A0A0A0` | `#AAAAAA` | `#A3A3A3` |
| selection fill | `#79B8FF` | `#ECECEC` | `#C9383F` |
| selection text | `#111111` | `#212121` | `#FFFFFF` |

## Semantic use

Week data bars use neutral control-outline tones for legibility; passive labels in the red theme remain neutral. Fine borders separate decorative cards. Editable fields use a stronger neutral outline. The primary action keeps its original position; secondary effort selection remains neutral so it does not compete with Save. Neutral elevated surfaces preserve the composer/source/receipt separation. These are semantic assignments, not a single-tint inversion.

Focus specimen: a 3 px ring with 3 px offset surrounds the control without moving it. White focus in Option 2 remains separated from the off-white action by the neutral gap. The specimen is separate from application screens; it does not invent a new workflow state.

Saved, pending, warning and error specimens use distinct explicit words/icons in addition to color. Success green is localized to small text. Errors use light red text on neutral charcoal, separate from Option 3’s solid red primary action. A later implementation still needs keyboard, focus, forced-color and screen-reader qualification.

Nominal sRGB ratios are listed below. The weakest text-pair and border results from the actual rendered subset are described in [verification](VALIDATION.md).

| Pair | 1 | 2 | 3 |
|---|---|---|---|
| primary on canvas | 16.57:1 | 13.63:1 | 17.45:1 |
| secondary on raised | 8.26:1 | 6.94:1 | 8.82:1 |
| muted on selected | 5.27:1 | 4.82:1 | 5.23:1 |
| action label | 9.09:1 | 13.63:1 | 5.1:1 |
| accent on selected | 6.63:1 | 9.48:1 | 5.64:1 |
| input boundary on raised | 4.21:1 | 4.27:1 | 4.26:1 |
| success on selected | 8.06:1 | 6.56:1 | 7.72:1 |
| focus on raised | 9.52:1 | 12.63:1 | 8.76:1 |
