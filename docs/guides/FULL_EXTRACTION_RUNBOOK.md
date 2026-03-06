# Full Extraction Runbook

This runbook defines deterministic ingestion policy for `reference/` assets across CI and local workflows.

## Modes

| Mode | Command | Purpose | Extraction |
| --- | --- | --- | --- |
| CI | `scripts/reference_ingest.sh ci` | Fast regression check in automation | Metadata-only (`--metadata-only`) |
| Local metadata | `scripts/reference_ingest.sh local-metadata` | Quick local sanity check | Metadata-only (`--metadata-only`) |
| Local full | `scripts/reference_ingest.sh local-full` | Regenerate publishable guides and validate output quality | Full extraction + checksum/non-empty verification |

## Policy

- CI must run in metadata-only mode for speed and reproducibility.
- Local full mode is required before claiming extraction quality completion.
- Full mode requires `pypdf` in the project venv: `apps/api/.venv`.
- `scripts/verify_guides_checksums.py --require-non-empty` is mandatory in full mode.

## Local Full Extraction Workflow

```bash
cd /home/rocco/hypertrophyapp
./scripts/reference_ingest.sh local-full
```

This command:

1. runs `importers/reference_corpus_ingest.py` in full extraction mode,
2. regenerates ingestion quality report artifacts,
3. verifies asset checksums and non-empty excerpts for PDF/XLSX/EPUB guides.

## CI Workflow

```bash
cd /home/rocco/hypertrophyapp
./scripts/reference_ingest.sh ci
```

This command keeps CI lightweight while still validating deterministic catalog/provenance emission.

## Troubleshooting

- `pypdf is required for local-full mode`:
  - install API dependencies in venv: `apps/api/.venv/bin/python -m pip install -r apps/api/requirements.txt`.
- `metadata-only extraction method` or `zero extracted characters` failures:
  - rerun in `local-full` mode and inspect problematic source files in `reference/`.
- checksum mismatch:
  - regenerate artifacts from a clean working tree and rerun full mode.
