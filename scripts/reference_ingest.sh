#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/apps/api/.venv/bin/python}"
MODE="${1:-local-full}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[FAIL] Python executable not found: $PYTHON_BIN"
  exit 1
fi

cd "$ROOT"

run_ingest() {
  local mode_label="$1"
  local metadata_flag="$2"
  echo "[RUN] reference ingestion mode=$mode_label"
  "$PYTHON_BIN" importers/reference_corpus_ingest.py $metadata_flag
  echo "[RUN] ingestion quality report"
  "$PYTHON_BIN" scripts/generate_ingestion_quality_report.py
}

case "$MODE" in
  ci)
    # CI mode is intentionally fast and deterministic: metadata-only ingestion.
    run_ingest "ci" "--metadata-only"
    ;;
  local-metadata)
    run_ingest "local-metadata" "--metadata-only"
    ;;
  local-full)
    # Local full mode requires PDF parser support to regenerate non-empty excerpts.
    "$PYTHON_BIN" -c 'import pypdf' >/dev/null 2>&1 || {
      echo "[FAIL] pypdf is required for local-full mode. Install API requirements first."
      exit 1
    }
    run_ingest "local-full" ""
    echo "[RUN] verify guides checksums"
    "$PYTHON_BIN" scripts/verify_guides_checksums.py --require-non-empty
    ;;
  *)
    echo "Usage: scripts/reference_ingest.sh [ci|local-metadata|local-full]"
    exit 1
    ;;
esac

echo "[PASS] reference ingestion workflow complete for mode=$MODE"
