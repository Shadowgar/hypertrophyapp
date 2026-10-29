# FERRAVIS UI qualification — 2026-10-29

Owner scope: public FERRAVIS identity, accessible soreness collection, and
login-specific spacing. Base: `8693ede061428b5202ca3661092b5d030d372bca`.
Implementation and qualification are separate from merge, deployment, reset and
release acceptance. Issues #103 and #105 remain open for physical-iPhone, gym and
performance acceptance. [Working identity and limited name review](brand.md).

## Behavior and boundaries

`TodayPage` retains the existing scheduling-clock lookup, soreness payload,
date-rollover handling, daily Skip key and workout refresh. The new
`SorenessDialog` owns presentation and input interaction only. A native modal
makes the background inert; the dialog bounds itself to the visual viewport and
safe areas. Inputs/notes scroll within the body, with actions and status/error
text in the persistent footer. Body scroll position/styles and focus are restored
on exit. Pending actions disable both controls and use a synchronous guard
against repeated activation. Escape follows the existing explicit Skip action.

The login form has a local CSS override for the shared minimum height and
auto-margin action placement. Other setup forms retain the existing layout.
Public names and original brand assets change; program names, runtime policy,
API/database/auth/storage identifiers and the production domain are preserved.

## Baseline and regression evidence

Chromium baseline captures used the original source with synthetic API fixtures
at 1440×900, 390×844, 1440×600 and 844×390. Desktop recovery-to-Sign-in spacing was
250.39px; mobile/landscape spacing was 110.39px. The soreness Save button bottom
was 780.19px at all four sizes, placing it below the 600px and 390px usable
viewports. The new login assertion fails on that baseline. The two new soreness
tests fail on the original missing dialog semantics and repeated save writes.

All browser fixture requests stay on the dedicated loopback web origin; API
requests are intercepted and off-origin requests aborted. No production API,
account or database is used. Unit suites use mocked fetch. Native production
build and browser results will be recorded here after the parent-coordinated
build slot. Partial development captures are not final qualification.

## Qualification status

| Check | Result |
|---|---|
| Focused soreness/Today/date tests | 9 passed after recovery. |
| Local-day rechecks and account/draft/storage boundaries | 26 passed. |
| Raster assets | Five PNGs: correct dimensions, CRC-valid chunks and complete decompression; vector/raster visually inspected. |
| Initial full web run | 508 passed / 16 failed: 15 fixture URL-shape failures from the explicit loopback override; one intentional focus-target snapshot change. |
| Corrected affected-file run | 33 passed with `/api` fixture URL shape; only the two intentional Today heading attributes changed in the snapshot. |
| Full corrected web suite | 524 passed across 74 files, two workers; no failed/skipped tests. |
| Lint | Exit 0; no errors, nine existing hook-dependency warnings. |
| TypeScript | Exit 0 after removing an unsupported test-only `getByRole` option; initial diagnostic retained. |
| Patched native production build and Chromium/WebKit | Pending scheduled qualification. |
| Disposable-API onboarding through date preview | Parent-coordinated qualification pending. |

The interrupted development run reported Watchpack `ENODEV` for an unrelated
unavailable mount and high disk wait, with no memory pressure. Owned development
processes were stopped. The dependency symlink/watcher scope is a possible
contributor, not an established cause of the earlier host restart. Final browser
qualification will use the production build without the development watcher.

Physical iPhone keyboard/touch/background behavior, gym use and broader product
performance remain owner acceptance checks. A simulated reduced visual viewport
does not establish physical-device qualification. Headless tests do not establish
screen-reader usability or commercial trademark clearance.

For the future authorized reset, start the owner’s onboarding test in a fresh
browser context or clear **only this application origin’s local/session storage**.
Account-owned drafts reject a different UUID, including when the email is reused;
legacy unowned drafts are rejected. A fresh context also removes guest choices,
cached appearance preferences and the existing date-only soreness Skip marker.
The rebrand preserves those storage identifiers and their current behavior.
