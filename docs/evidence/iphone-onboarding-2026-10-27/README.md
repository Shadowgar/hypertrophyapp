# iPhone onboarding and first scheduling repair

Owner-authorized bounded implementation, Issues #105/#103; base
`d905397d8def962077384781501072dbf669786c`. No merge, deployment, production data
or release-control writes. Approved unified UI and existing backend decision owners.

## Plan and checkpoint

- Reproduce and protect both password forms, browser navigation, reload/re-login,
  blank/saved/established continuation, safe setup review/edit and date preview.
- Keep guarded first initialization, explicit Customized consent, exact program/
  dates/account/revision boundaries. Preview never activates.
- Test regressions before corrections; use verified disposable PostgreSQL and
  synthetic browser accounts. Final candidate: full web checks, applicable API,
  browser desktop/mobile WebKit, scoped Codex Security and immutable-head CI.
- One focused PR related to #105; keep #103/#105 open; stop before merge/deploy.

The earlier temporary worktree disappeared between turns. Its uncommitted changes
and logs are unavailable. This recovery uses the persistent worktree
`/home/rocco/hypertrophyapp-worktrees/iphone-onboarding`, branch
`fix/iphone-onboarding-scheduling`; no earlier results qualify the recovered patch.
Commit checkpoints during recovery. Next: recover failing regressions, implement
and verify the bounded corrections, then complete final qualification and PR.

Read-only live baseline on 2026-10-27: main d905397, public API/web 891228f,
publisher false. Timer was observed active, differing from the earlier inactive
observation; neither control was changed. Production checkout debug log is
pre-existing modified runtime work and is untouched.
