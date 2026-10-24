# PR #110 finding-by-finding disposition

Initial review target `a3f5760badfe2d5fbc76fcb12b026286a256e4f9` was verified before edits. All nine PR threads, including previously resolved CodeQL, were rechecked. The fixes below are verified; thread replies/resolution are applied after verification and publication. Final external thread state is reported in the PR qualification comment.

| Finding / thread suffix | Fixing commit | Relevant verification |
|---|---|---|
| Source-text persistence / vbpEw (previously resolved) | `d0cdaf9` | Authored/generic technique retry-reload tests; source reconstructed from API; CodeQL independently reported. |
| Preference foreign key / vbrWB | `b9adac1` | Two FK failures reproduced; three cleanup cases on PostgreSQL and SQLite, four profile tests, isolated additive-upgrade preservation. |
| Legacy appearance text / vbrWH | `721b1fd`, `aa43248` | Thirty loaded route/appearance samples, actual hover, text/ancestor backgrounds and six rendered focus/control boundaries. Palette/default unchanged. |
| Uncertain correction receipt binding / vb19x | `3dfcfb5`, `8f349d3` | Seven initial recovery cases; real mobile/desktop before/after-commit close/reload exact retry; database correction parents retained. |
| History mixed mass units / vb190 | `721b1fd` | Both-unit/round-trip tests across receipts, chart/tooltip/PR/volume/summary and unchanged cm; actual saved-unit chart replay retains canonical analytics hash. |
| Uncertain undo permits more writes / vcYtx | `1226fb3` | Ten focused recovery/legacy cases; actual mobile/desktop before/after commit, write/navigation locks, reload and Today404; exactly three server undo actions for six attempts, all receipt rows preserved. |
| Definitive obsolete correction / vcslR | `d068582` | Exact409/confirmed404 refresh; ambiguous responses remain frozen; real other-device correction→stale rejection→replacement edit→lost response→exact retry and database chain. |
| RPE/RIR counterpart / vcslU | `d068582` | Both-scale component transitions and frozen retry; real registered Customized API test rejects omitted counterpart, accepts explicit null switches, preserves three history rows and consent. |
| Other route mass summaries / vcslZ | `c517e5b` |33 focused Home/Week/Check-In cases; real saved kg→lb→kg route checks, exact Home bodyweight values, unchanged canonical profile hash and explicit canonical Check-In entry. |

[Original correction/appearance evidence](README.md) · [Undo follow-up](undo-followup/README.md) · [Latest correction/unit follow-up](compatibility-followup/README.md).

The final application source is `d068582`; the final package commit may contain only evidence/docs. The whole local web suite passes 269 tests/47 files, plus build/TypeScript and lint (zero errors, eight existing warnings). Earlier runtime captures retain earlier revisions. Global CI failures are never waived, and managed security export remains incomplete as documented. Issue #103 remains partial; no merge, deployment, production migration, live-data operation or broader Home/onboarding implementation occurred.
