# FERRAVIS UI qualification — October 29–30, 2026

Qualified production-built source: `38db151b1ce3584d539ab92f344a7f843db7f095`.
Baseline: `8693ede061428b5202ca3661092b5d030d372bca`. This is evidence for
unmerged PR #129, not deployment or physical-device acceptance. Issues #103 and
#105 remain open. [Working identity and limited name review](brand.md).

## Behavior and preserved authority

`TodayPage` retains the existing scheduling clock, soreness payload, date rollover,
daily Skip key and workout refresh. `SorenessDialog` owns presentation and input
interaction only. Its native modal makes the background inert and fits the visual
viewport/safe areas. The header, inputs and notes scroll within the body; actions
stay in a persistent footer, with bounded scrolling for lengthy error/status text.
It restores body scroll and visible focus on exit. A delayed workout refresh
cannot steal focus from a visible control the athlete has already selected.
Pending actions use a synchronous guard against duplicate writes. Escape follows
the existing explicit Skip action; saving/skipping retain their original dates.

The login-only CSS override removes the shared minimum form height and automatic
action margin. Other setup forms keep their layout. Public labels, original
vector/raster assets, metadata, manifest and email copy use FERRAVIS; program,
API, database, auth, storage, environment and service identifiers remain intact.
Complete historical onboarding-questionnaire editing was outside PR #127 and is
not added here. No workout algorithm or source library changes are included.

## Production artifact and qualification

[Hosted native ARM64 run 40825000117](https://github.com/Shadowgar/hypertrophyapp/actions/runs/40825000117)
built exact source `38db151` with pinned Node 24.22.2. Runtime export artifact
`12875754973` has SHA-256
`f24a4b11fd5e27ce17a48b4d0def15192763b3cd6586698fc2626af239bfef39`.
The exported application is the actual Next.js production build. It ran without
source edits or development watchers in executable tmpfs on the matching ARM64
Node/Alpine base, with verified 1.5 GiB memory and two-CPU limits. Its compiled
API rewrite is explicitly `http://127.0.0.1:55438`; normal builds retain
`http://api:8000`. This test artifact is not a deployment artifact.

The `/version` and proxied `/api/health` both reported the qualified source.
Browser-only fixtures intercepted API requests and blocked other origins. Real
onboarding used separately verified loopback PostgreSQL, schema 0026, synthetic
accounts, synthetic signing configuration and disabled SMTP. No production
account was created, modified or deleted. An operator-scheduled host reboot
removed temporary fixtures; affected checks were rerun on a fresh verified
cluster. Private recovery evidence from the original reset rehearsal was retained.

| Check | Verified result |
|---|---|
| Combined source CI | [40824946178](https://github.com/Shadowgar/hypertrophyapp/actions/runs/40824946178): API 1,044 passed / 123 explicit skips; web 526 passed in 74 files; lint, types, production build, tooling and documentation passed. |
| Focus/date/draft regressions | Initial 9 soreness tests and 26 date/draft checks passed; final focus/keyboard regressions passed in the 17-test focused selection and full CI. |
| Native runtime | ARM64, Node 24.22.2, Next 16.4.1, Sharp 0.35.5/musl, startup, guest routes, matching revisions and zero server actions passed. |
| Chromium and WebKit | Each passed 1440×900, 390×844, 1440×600 and 844×390; no page/runtime errors beyond the deliberately intercepted save failure. |
| Input/footer behavior | Keyboard, desktop wheel, mobile touch controls, Chromium native touch scrolling, body/background lock, Tab wrap, save retry and duplicate-write guard passed. |
| Keyboard-sized viewport | Portrait 340px and landscape 180px visual regions retained inputs/actions and visible pending/error state. These are simulations, not a physical iPhone keyboard. |
| Focus after close | Today/resumed workout receives visible focus; held asynchronous progress cannot steal a newly focused repetitions control. |
| Draft isolation | Both engines reject old-owner drafts with the same email and a new UUID and reject legacy unowned drafts; old-owner positive controls prove the fixture is populated. |
| Real Authored onboarding | Both engines: registration, password visibility, back/forward/reload/close/sign-out/resume, Full Body Phase 1 selection, one setup write and date preview; no activation write. |
| Customized disabled | Both engines: setup saves once, disabled state is visible, no candidate/accept/activation write. |
| Customized enabled | Both engines: synthetic equipment profile and preview; acceptance starts unchecked and disabled, checkbox toggling works, no accept write, forged premature activation returns 409, active plan list remains empty. |
| Recovery interface | Both engines: generic request acknowledgement, password visibility, invalid-token 400, accessible retry/new-link path and return to login. SMTP disabled; real mailbox delivery was not tested. Valid recovery/concurrency/revocation is covered by the separate API tests. |
| Assets | Original vector and five valid PNGs; browser title, manifest, accessible brand and decoded icons verified in both engines. |

WebKit harness corrections were supported by actual browser observations:
Page Down did not scroll in that runner, while Arrow Down did; Playwright rejects
mouse wheel in mobile WebKit; React's passive cleanup follows dialog removal.
The final harness checks native key scrolling and waits for actual body/focus
restoration. It does not manufacture a successful scroll or weaken the application
assertions. Mobile WebKit touch dragging and real screen-reader usability remain
physical-device acceptance, not inferred from desktop automation.

Earlier failures are retained in the private engineering evidence: the initial
web run had 15 URL-fixture mismatches and one intentional focus-target snapshot
delta; the corrected suite passed. Independent review then reproduced delayed
focus theft and 180px footer clipping before their fixes. Lint has nine existing
hook-dependency warnings. Explicit skips do not establish source-fidelity or
private integration acceptance; full protected-main qualification remains required
following separately authorized integration.

## Before and after

Measurements are CSS pixels. Original captures use synthetic fixtures on the
baseline source; final captures use the qualified production artifact. Images
are unedited. The [file manifest](screenshots.json) records sizes and hashes.

| Measurement | Before | Chromium after | WebKit after |
|---|---:|---:|---:|
| Desktop recovery-to-Sign-in gap | 250.39 | 16 | 16 |
| Mobile/landscape login gap | 110.39 | 16 | 16 |
| Save bottom at 1440×600 | 780.19, outside viewport | 571 | 571 |
| Save bottom at 844×390 | 780.19, outside viewport | 369 | 369 |
| Save bottom at 390×844 | 780.19 | 815 | 815 |

| Surface | Before | After |
|---|---|---|
| Desktop login/branding | [Baseline](screenshots/before-desktop-login.png) | [FERRAVIS](screenshots/after-desktop-login.png) |
| Mobile login/branding | [Baseline](screenshots/before-mobile-login.png) | [FERRAVIS](screenshots/after-mobile-login.png) |
| Short desktop soreness | [Clipped](screenshots/before-short-desktop-soreness.png) | [Persistent footer](screenshots/after-short-desktop-soreness.png) |
| Landscape soreness | [Clipped](screenshots/before-landscape-soreness.png) | [Persistent footer](screenshots/after-landscape-soreness.png) |
| Mobile soreness | [Baseline](screenshots/before-mobile-soreness.png) | [Scrollable body](screenshots/after-mobile-soreness.png) |

Full Chromium/WebKit screenshots, measurements and real API write/response
summaries are retained in `ferravis-prelaunch-evidence/ui`, outside Git. Subsequent
qualification-harness and evidence-only commits do not change the application
runtime sources; final PR checks bind those final immutable heads independently.
The browser build's embedded revision remains `38db151` and is not relabeled.

## Owner's fresh iPhone acceptance, after authorized release/reset

1. Verify the approved live revision. Use a fresh browser context or clear only
   this application's origin storage; confirm zero accounts before registration.
2. Register once; check Show/Hide Password and recovery. Confirm FERRAVIS title,
   icon and navigation in portrait/landscape and home-screen launch.
3. Select Authored or Customized deliberately. Complete setup, leave/return and
   sign out/in. Confirm no old answers, account data or unintended active plan.
4. Review dates before explicit activation. For Customized, verify exact-version
   consent and activation remain separate, explicit actions.
5. Open Today; use the physical keyboard and touch-scroll notes/inputs. Confirm
   Save/Skip, pending/error feedback, focus and background position remain usable.
6. Complete gym/performance acceptance before closing #103 or #105.

Account-owned drafts reject a different UUID, including reused email. A fresh
context additionally removes neutral guest choices, appearance preferences and
the existing date-only soreness Skip marker; compatibility storage names remain.
