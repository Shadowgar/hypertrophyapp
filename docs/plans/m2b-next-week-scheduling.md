# M2B-2 next-week scheduling

Owner-authorized implementation from the 2026-10-15 attached task, based on main `27231cfe98631de7eaebf21e13b60c6d145aeeba`. Implement, qualify, commit, push and open a PR; stop for owner review. No merge, deployment or live migrations.

Extend existing selected-date scheduling to current/next Monday–Sunday weeks in the configured IANA timezone. Keep the allocator, preview/activation digest, user lock, revisions and frozen execution boundaries. Keep Today on the actual local date. No migration is planned.

- [x] Core: test current/next week, DST, rollover, month/year, duplicate and membership rejection; expand explicit date validation.
- [x] API: week-specific context; establish authored successor from a unique saved predecessor and source sequence, reject ambiguous/exhausted/conflicting progression, pin actual source week. Preserve saved future prescriptions, identities, loads and consents. Bind predecessor and spacing dependencies in activation digest. Test no-write preview, stale dependencies/revisions, history isolation, same-count rescheduling, conflicting bindings and Today.
- [x] Web: add current/next controls, selected range and authored block, reload per-week state, invalidate pending previews and asynchronous responses on navigation. Test revisit and stale-response boundaries.
- [ ] Qualification: verified disposable SQLite focus, isolated PostgreSQL schema/concurrency/history checks, authenticated Playwright desktop/mobile, one broader core/API/web qualification and baseline identity comparison. Review API changes for security boundaries.
- [ ] Delivery: record evidence/limitations, commit and push requested branch, open PR, inspect CI/Codex review/threads/mergeability, fix correctness findings; stop unmerged for review.

Review focus: future activation before a current plan exists; predecessor changed after preview; changed current activity after future activation; final source week; Sunday rollover with pending browser responses. Ambiguity produces an explicit reconciliation conflict, never guessed progression.

Local qualification and its exact limits are recorded in [the evidence report](../evidence/2026-10-16-m2b-next-week-scheduling.md). [PR #83](https://github.com/Shadowgar/hypertrophyapp/pull/83) records final-head CI, review fixes, thread status and mergeability. The source checklist above does not grant release acceptance; final-head delivery evidence and owner review remain separate.
