# Programs catalog implementation plan

Owner-authorized Workstream D, 2026-10-26; base `ad789ff983a51c2445fde34c849d3738fcb0311a`. Implements approved PR #108 `33598c3` screens 12/65/67 and the read-only entry boundary of 72. No new design approval, roadmap or training policy.

Architecture: add `/programs/page.tsx` using existing API GETs, program display names and shared semantic theme classes. Display only admitted Phase 1/2 catalog records; legacy generated templates do not become a new Customized offer. `/customize` remains the explicit consent/preview owner. `/week` remains the date/activation owner. Catalog links do not select, activate or replace anything.

- Add focused component regressions for distinct authored phases, actual availability, stored preference versus scheduled plan, no writes, independent catalog loading, error/retry and account/token/request changes.
- Observe the missing route failure; implement the minimum page and rerun tests with one worker.
- Run frontend types/lint/build/full suite in the coordinated build slot. Verify mobile/desktop route navigation and all six appearances with synthetic response fixtures; distinguish this from real-API persistence qualification.
- Record exact evidence, limitations and immutable candidate. Publish focused PR; no merge/deployment.

Review focus: retired-account responses/401; ambiguous failed schedule reads; unknown or missing catalog entries; legacy generated aliases; accessible retry/focus; no profile/preferences/plan writes or histories exposed across accounts. No API/schema/rule/source edits are needed. Existing navigation destinations are inspected separately; defects outside this route are reported before expanding scope.
