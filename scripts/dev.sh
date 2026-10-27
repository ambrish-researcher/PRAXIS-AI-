#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export npm_config_cache="${npm_config_cache:-/tmp/praxis-npm}"
# One API worker owns the SQLite mission queue. Do not use --workers > 1.
.venv/bin/python -m uvicorn backend.praxis.api:app --host 127.0.0.1 --port 8000 &
api_pid=$!
npm run dev --prefix frontend -- --port 5173 &
web_pid=$!
cleanup() { kill "$api_pid" "$web_pid" 2>/dev/null || true; wait "$api_pid" "$web_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
wait -n "$api_pid" "$web_pid"
