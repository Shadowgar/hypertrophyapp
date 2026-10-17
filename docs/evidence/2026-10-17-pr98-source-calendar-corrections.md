# PR #98 source-calendar corrections — 2026-10-17

Owner-authorized follow-up to the independent COMMENT review on [PR #98](https://github.com/Shadowgar/hypertrophyapp/pull/98), starting at209e119509220f2186d86873c0fa98502e31f6dc. This updates the same draft, not another preview/lifecycle framework. Scientific review remains separate in #96. [Measured query data](2026-10-17-pr98-source-query-measurements.json).

## Coverage: absence is an observation, not a fabricated rest plan

Rechecked actual #83 at **3f4927b3cdcca1e8655337b30b93894741bfca9c**, still OPEN/unmerged. `neighbor_context` returns None for no dated row, multiple/mismatched rows or empty sessions. `scheduling_context` can return no saved plan and an empty selected-date list; it falls back to editable availability. Neither contract establishes an authoritative off week, external-history completeness or negative-coverage receipt.

The new per-week coverage evidence distinguishes:

| State | Meaning | Consumer completeness |
|---|---|---|
| `dated` | One coherent retained dated source with no unresolved relevant legacy evidence | May contribute to complete observed window; source still unverified |
| `observed_empty` | Account-scoped read found no active plan or execution snapshot in that week and no potentially relevant legacy ambiguity | **Incomplete**, reason `negative_coverage_not_defined_by_pr83` |
| `unknown` | Malformed/missing dated source with retained work, ambiguous legacy evidence or another unresolved source condition | **Incomplete**; reason retained |

Every per-week evidence record has `authoritative=False`; `SourceCalendarPort.source_verified=False` and the outer unverified scheduling boundary remain unchanged. New users and genuinely empty surrounding weeks are represented without fake blank plans and without being conflated with malformed rows. They are **not yet qualified for authoritative negative coverage**. There is no trusted empty-week authority in #83 to implement safely: declaring `complete=True` from no rows would invent that policy. Accepting authoritative absence remains an explicit source-contract integration difference, not a requirement to create three fake plans.

Unrelated old unbound records no longer poison a clean window or change its freshness. An unbound log remains ambiguous if its workout reference intersects retained window sessions, or its creation/amendment/void receipt is at/after the local-window start. A legacy session projection uses the analogous reference/creation/update test. No upper receipt cutoff discards late/backdated amendments. Timestamps bound possible relevance; **they never become performed dates**. Old reused template references remain unresolved even if their receipts are old. This intentionally preserves uncertainty when source identity cannot separate repeated weeks.

## SQL scope and integrity

Source reads execute under the existing User lock and use account+week/local-date predicates, covered plan-key lookup followed by primary-key payload fetch, and occurrence-scoped set/command/session queries. A recursive UNION keeps the connected amendment chain, including voids, ancestors and descendants, independent of receipt dates. Missing/foreign or cross-occurrence parents and cycles fail closed. Repeated exercise occurrences retain distinct identities; frozen snapshots remain frozen after undo.

Unbound ambiguity is two indexed EXISTS checks, not lifetime row loading. Relevant histories are grouped by occurrence once. The reader returns the same source result/freshness after unrelated historical records are added.

`research/m4c3b2b/002_source_read_indexes.sql` proposes11 composite/partial source-read indexes for qualification on disposable copies. Existing state/primary-key/supersedes indexes are reused. Production models, Alembic and indexes were **not changed or migrated**; production index selection/concurrent build/lock qualification remain separately reviewed work. Bootstrap applies this script only after existing disposable identity/marker/empty-target guards.

## Focused PostgreSQL evidence

One fresh resource-bounded PostgreSQL16.13 fixture: **c3b2b97_199386d573**, rolec3b2b_owner,127.0.0.1:32770,256MB memory/0.5CPU/192MB tmpfs. Exact container/DB/user/random-marker verified; ordinary import DB URLs explicitly point at an unused `/tmp` SQLite file, inherited environment cleared. No production service/data operation or destructive SQL. A first invocation accidentally selected the previously stopped disposable manifest and failed connection-refused; the dedicated follow-up runner was corrected before feature verification. It did not fall back to another target.

- Coverage tests first reproduced the old legacy-global-poisoning and lack of absence evidence. New cases cover new account, empty neighbors, malformed dated row, old unrelated/reused receipts, late amendments/voids, legacy session updates and known-occurrence corrections/voids. A connected-cycle negative also failed first and was corrected.
- **99 applicable PostgreSQL/source/ownership/staging/lifecycle/HTTP tests passed in69.75s**, one existing Starlette/httpx TestClient deprecation warning. No unrelated broad/core/web suite run locally.
- Large-history test **passed in10.67s**, with500 old weekly plans,1,500 old occurrences,30,000 bound sets,3,000 old unbound receipts,3,000 commands and3,000 session projections for the same synthetic subject, plus a nonempty current source window. Roughly ten years at three sessions/week; these are storage fixtures, not a copied training program.
- Initial EXPLAIN exposed a579-row plan-table scan despite scoped returned rows. The correction uses a covered `(user_id,week_start,id)` lookup before wide payload fetch. No forced planner switches or production tuning.
- Final reader was remeasured read-only on the existing large fixture without reseeding: **7 source queries,10 rows returned; maximum11 examined scan rows per query** in EXPLAIN ANALYZE. Small-window median23.10ms; large-history median23.94ms; captured full account-read47.76ms. The small baseline came from the same dataset's initial load; final remeasurement retained that baseline. These are warmed disposable measurements, **not production latency guarantees or throughput acceptance**. Index names/SQL planning/execution/row counts are in the JSON artifact.

Original snapshot payload preservation, DST-local dates, repeated slots, frozen placement mismatch, undo freshness, session reset/revoke races, revision replay and complete compact consent remain covered by the99-test subset. No consent or source evidence can activate a workout.

## Hosted CI classification

At original #98 head209e119, [run39058018976](https://github.com/Shadowgar/hypertrophyapp/actions/runs/39058018976) completed RED:

- API **874 passed /8 failed /50 skipped**,552.59s. Eight names match baseline: two adaptive catalog; two Authored/generated total sets; adaptive fourth-exercise guidance; weekly-review adjustment; two missing Phase1 workbook/source cases. No new failure name;25 additional skips are explicit disposable-PG cases without a hosted target.
- Core **719 passed /4 failed**, same working-set normalization/intelligence counts and two rules-runtime coverage assertions.
- Web **173 passed /1 failed**, same ambiguous-link history calendar case. Documentation/container/workflow checks passed; aggregate qualification failed accordingly.

The updated head's hosted classification is recorded in the PR after completion; no broad rerun or inherited failure repair is authorized by this correction. A passing focused subset is not full CI green.

## Remaining source-contract differences

1. Authoritative negative coverage/new-user or off-week admission has no owner in current #83; observed emptiness stays unknown to its spacing policy. Source verification remains off.
2. Old unbound records sharing a current template identity need an accepted mapping/resolution policy; receipt dates cannot settle performed dates.
3. #83 current/next-week resolver, all real lock-participating writers, carryover/started-work rules and production indexes/roles are not integrated by these read-only changes. No source slot/date or Authored prescription changed.

No production migration/deployment/merge/activation, no Authored modification, no scientific signoff fabrication. This correction does not reopen the separate science review or inherited CI repair work.

## Final scoped review

Fresh independent review of209e119..c55ad028 read source/tests/index SQL/bootstrap/plan and pinned #83 identity/neighbor code. No concrete Important, Critical or minor findings. It confirmed that observed absence remains unqualified rather than inventing a rest-week authority; supplied timings/tests were not independently rerun.

Codex Security preflight3pass; fresh advisory **granted / Daybreak Blue**. Exact-range scan **c5a2bb88-0138-448c-9651-289876831b2b** inventories four changed source files. Managed semantic export again hit the unchanged output-parent permission guard. No repair/bypass or sealed security-pass claim; scan is preserved unsealed. Later changes are documentation/evidence only.

Documentation check:0 new active link failures,28 retained baseline exceptions; diff check passed. Protected program/knowledge/runtime-rule trees and production main/auth/models/Alembic/routers/history/#83/web files are unchanged. Owned disposable fixture was stopped after qualification; private synthetic data/measurement files remain outside Git.
