# PR #110 review dispositions

Review target verified through GitHub before edits: `a3f5760badfe2d5fbc76fcb12b026286a256e4f9`, branch `feat/unified-ux-gym`. All five review threads were fetched, including resolved threads. The earlier CodeQL source-text thread was already resolved; its source fix is `d0cdaf9` and its passing CodeQL run at the target is earlier-revision evidence.

| Finding | Correction | Fixing commit / regression |
|---|---|---|
| Preference foreign key blocks development account cleanup | Explicit user-filtered preference delete in each existing cleanup transaction; no cascade/schema change. Existing enable/auth/confirmation gates preserved. | `b9adac1`; `test_preference_account_cleanup.py`: both routes, disabled defaults, confirmation, target isolation, training reset preservation; PostgreSQL and SQLite. |
| Legacy body/label/section text ignores semantic palettes | Existing typography, placeholder, select-option and focus helpers consume shared semantic colors. Palette values unchanged. | `721b1fd` plus hover fix `aa43248`; rendered multi-route six-appearance evidence in this package. |
| History analytics ignores saved kg/lb | Mass, volume, summary, chart title/aria, PR and tooltip presentation use saved units; canonical payload/chart geometry and cm measurements preserved. | `721b1fd`; `history.units.test.tsx`, both initial units and round-trip preference switches, no refetch/write. |
| Unknown correction can be abandoned by selecting another receipt | One retained recovery snapshot owns original receipt, unit, immutable command and payload; restore even when superseded; disable other edits and keep exact retry accessible. | `3dfcfb5` plus lint fix `8f349d3`; seven `exercise-control.correction.test.tsx` cases, 16 correction/RPE tests after lint fix; final runtime replay in this package. |
| CodeQL source instructions persisted in clear text (previously resolved) | Persist references/unit only; reload current instructions from API. | `d0cdaf9`; generic/Authored technique retry-reload tests. Canonical managed security scan remains incomplete; see SECURITY.md. |

A later recheck found an additional uncertain-undo finding (`PRRT_kwDORciBG86vcYtx`, atlas-runner.tsx). Fixed in `1226fb3`; [undo follow-up](undo-followup/README.md) records the ten recovery/negative-boundary tests and final runtime evidence. The real mobile/desktop before/after-commit, reload and Today-404 replays passed; PostgreSQL confirms preserved originals and exactly three unique undo actions. Verified for thread resolution.

Thread resolution occurs only after the corresponding correction has passed verification. A resolved thread does not waive global CI failures, physical-device acceptance or managed security-export limits.
