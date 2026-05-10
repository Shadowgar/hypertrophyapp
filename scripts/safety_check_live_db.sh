#!/usr/bin/env bash
set -euo pipefail
cd /home/rocco/hypertrophyapp

echo "[safety] live users in postgres:"
docker compose exec -T postgres psql -U hypertrophy -d hypertrophy -Atc "select email from users order by created_at desc limit 10;" || true

echo "[safety] If this shows real users, DO NOT run destructive reset commands."
