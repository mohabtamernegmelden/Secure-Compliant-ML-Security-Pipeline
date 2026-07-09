#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  echo "No .env file found. Copy .env.production.example to .env and fill in production values." >&2
  exit 1
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --log-level info
