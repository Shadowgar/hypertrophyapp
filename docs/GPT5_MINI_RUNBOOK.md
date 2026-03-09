# GPT-5-mini Runbook - Adaptive Coaching

Last updated: 2026-03-07

## Start Sequence

1. Read:
- `docs/AI_CONTINUATION_GOVERNANCE.md`
- `docs/Master_Plan.md`
- `docs/redesign/Adaptive_Coaching_Redesign.md`
- `docs/GPT5_MINI_EXECUTION_BACKLOG.md`

2. Preflight:
```bash
cd /home/rocco/hypertrophyapp
./scripts/mini_preflight.sh
```

3. Select task:
```bash
cd /home/rocco/hypertrophyapp
./scripts/mini_next_task.sh
```

## Ingestion Modes Policy

Use wrapper:
```bash
cd /home/rocco/hypertrophyapp
./scripts/reference_ingest.sh [ci|local-metadata|local-full]
```

- `ci`: metadata-only deterministic smoke
- `local-metadata`: quick local check
- `local-full`: full extraction + checksum/non-empty verification

## Quality Verification

```bash
cd /home/rocco/hypertrophyapp
./scripts/verify_master_plan_audit.sh
./scripts/verify_guides_checksums.py --require-non-empty
```

## Validation

```bash
cd /home/rocco/hypertrophyapp
./scripts/mini_validate.sh
```

## Delivery Rule

Implement one task end-to-end, validate, commit, push, then move to next task.

For coaching logic specifically:
- do not add new meaningful decision logic in routers
- migrate one decision family at a time into `packages/core-engine`
- require a structured decision trace before calling the task complete
