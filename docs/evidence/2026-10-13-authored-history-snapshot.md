# Authored history response snapshot qualification

Issue: [#80](https://github.com/Shadowgar/hypertrophyapp/issues/80). Base `40a10ccf28e227bd06cd2c7623df5abba7b7bd2a`; branch `perf/authored-history-snapshot`. Owner-authorized performance correction and review PR; no merge or production deployment.

## Runtime change

`load_authored_history_snapshot` retains the existing `_all_groups` owner-filtered receipts, effective corrections, chronology and exposure summaries. It computes the existing comparison keys once and stores an immutable cohort index. Today, Progress and Summary lazily create one local snapshot in `_attach_authored_load_feedback`; projections require matching user, occurrence owner and database session. No global/session cache or stored advice is introduced.

Each projection still resolves its current context and summary, applies its own inclusive performed-date cutoff, replaces its current exposure and uses the unchanged chronology/order and core decision/warm-up owners. Command, correction, undo and immutable retry paths do not reuse read-response snapshots. No prescriptions, scheduling, rules, source artifacts or schema change.

## Measured PostgreSQL comparison

PostgreSQL 16 in a loopback-only disposable tmpfs container, no mounted production persistence. Database/user identity and existing revision `0022_authored_load_states` were verified before imports. Explicit cleared test environments; no production access. Three synthetic users each have 25, 100 or 250 historical authored workouts, six distinct source slots, two working receipts per historical exposure and one partial working receipt per current slot. These are qualification fixtures, not importer or training-outcome claims.

Pre-change measurements ran before product edits. Final measurements used the same persisted fixture IDs and evidence; every full endpoint response (including recommendation IDs/revisions, reason codes, traces and warm-up guidance) equals its saved pre-change JSON. One warm-up request per case, three measured sequential requests, median wall time through FastAPI TestClient. No other test/build ran during measurement. SQL counts include endpoint database statements; history counts identify the two `_all_groups` SELECTs.

| Historical workouts | Endpoint | Median before ms | Median after ms | Total SQL before/after | History SQL before/after | Full reconstructions before/after |
|---:|---|---:|---:|---|---|---|
| 25 | today | 1523.66 | 979.12 | 23/13 | 12/2 | 6/1 |
| 25 | progress | 1475.97 | 887.77 | 16/6 | 12/2 | 6/1 |
| 25 | summary | 1451.89 | 902.02 | 17/7 | 12/2 | 6/1 |
| 100 | today | 3597.11 | 1423.65 | 23/13 | 12/2 | 6/1 |
| 100 | progress | 3602.35 | 1331.58 | 16/6 | 12/2 | 6/1 |
| 100 | summary | 3580.34 | 1221.94 | 17/7 | 12/2 | 6/1 |
| 250 | today | 7753.57 | 2168.02 | 23/13 | 12/2 | 6/1 |
| 250 | progress | 7735.18 | 2119.04 | 16/6 | 12/2 | 6/1 |
| 250 | summary | 7708.16 | 2132.44 | 17/7 | 12/2 | 6/1 |

At 250 historical workouts, full-history exposure summaries per response drop from 9,036 to 1,506; current-context summaries remain per exercise by design. Regression instrumentation also proves historical comparison keys are computed once (six historical groups plus three current keys, rather than repeated full-history hashing).

Reproduction: use the committed `apps/api/tests/benchmark_authored_history_snapshot.py` with an explicitly verified disposable PostgreSQL target and private output directory. It refuses SQLite, mismatched DB/user/port, missing isolated flags, missing 0022 and output outside `CI_TEST_ROOT`. For the `before` run, use this branch's fixture/benchmark scripts with `PYTHONPATH` pointing to the base checkout's `apps/api` and `packages/core-engine`, and `PROGRAMS_DIR`/knowledge pointing to that base. For `after`, point those paths to this branch. Keep the same DB and output directory; invoke `--phase before` then `--phase after`, each with `--output <private-root> --samples 3`. Supply `DATABASE_URL=TEST_DATABASE_URL`, `M2A_POSTGRES_ISOLATED=1`, `M2A_MIGRATED_DATABASE=1`, `TEST_DATABASE_PORT`, isolated log/test roots and a synthetic JWT key in a cleared environment. Do not inherit Compose/default production settings. Fixture credentials and full response JSON remain private; only metrics are published.

## Correctness and qualification

New tests cover all three multi-exercise routes, exact pre-optimization algorithm equivalence, incomplete/warm-up-only/corrected/voided receipts, changed variant/equipment/source slot, unknown actual RPE, earlier/later/legacy dates, user/session mismatch, fresh advice after correction/undo, immutable retries and no prescription mutation. The test-only oracle freezes the original projection traversal from this base (function SHA-256 `655cf0550f41c71453620124d1626c9294c274c0a6dd87342a0764e4a2768649`); unchanged receipt/core/wrapping owners are reused.

Initial once-per-response tests failed on the base with three full reconstructions, then passed. The hashing regression failed before indexing (21 keys instead of 9), then passed. Final 17 snapshot PostgreSQL cases passed, including the frozen pre-change oracle. Existing 41 load and 34 warm-up PostgreSQL cases also passed against the final cohort index. Independent final production source review found no blocker. Broader core qualification passed 600 cases with the same four baseline failures. Broader API/web qualification runs once; final results and isolated authenticated Playwright smoke are recorded in the PR.

## Limits

Measurements are three warm-cache samples on one host with synthetic Phase 1 histories. They establish the reported reduction in this environment, not production percentiles, concurrency throughput or universal speedup. Phase 2 behavior remains covered by existing warm-up tests. Per-exercise current-context summarization and core decisions still run; the shared snapshot is not a new database isolation or transactional-read guarantee. No history pagination or broader projection redesign is included. Accepted baseline failures remain failures; no unrelated CI/security cleanup. No migration or deployment is authorized by this record.
