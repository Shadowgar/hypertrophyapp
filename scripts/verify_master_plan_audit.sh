#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT_FILE="$ROOT/docs/audits/Master_Plan_Checkmark_Audit.md"

if [[ ! -f "$AUDIT_FILE" ]]; then
  echo "[FAIL] Missing audit file: $AUDIT_FILE"
  exit 1
fi

mapfile -t evidence_tokens < <(grep -o '`[^`][^`]*`' "$AUDIT_FILE" | sed 's/^`//; s/`$//' | sort -u)

if [[ ${#evidence_tokens[@]} -eq 0 ]]; then
  echo "[FAIL] No evidence tokens found in $AUDIT_FILE"
  exit 1
fi

missing=0
for token in "${evidence_tokens[@]}"; do
  # Validate only path-like code spans (paths or globs), not status labels/terms.
  if [[ "$token" != */* ]] && [[ "$token" != *"*"* ]] && [[ "$token" != *"?"* ]] && [[ "$token" != *"["* ]]; then
    continue
  fi
  if [[ "$token" == *" "* ]] || [[ "$token" == *":"* ]] && [[ "$token" != */* ]]; then
    continue
  fi

  candidate="$ROOT/$token"

  if [[ "$token" == *"*"* ]] || [[ "$token" == *"?"* ]] || [[ "$token" == *"["* ]]; then
    if compgen -G "$candidate" > /dev/null; then
      echo "[OK] $token"
    else
      echo "[MISSING] $token"
      missing=1
    fi
    continue
  fi

  if [[ -e "$candidate" ]]; then
    echo "[OK] $token"
  else
    echo "[MISSING] $token"
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  echo "[FAIL] Master plan audit references missing evidence paths."
  exit 1
fi

echo "[PASS] Master plan audit evidence paths verified."
