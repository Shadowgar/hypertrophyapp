#!/usr/bin/env bash
set -euo pipefail

timestamp="$(date +%Y%m%d_%H%M%S)"
mkdir -p ./infra/backups

docker compose exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-hypertrophy}" "${POSTGRES_DB:-hypertrophy}" \
  > "./infra/backups/hypertrophy_${timestamp}.sql"

echo "Backup written: ./infra/backups/hypertrophy_${timestamp}.sql"
