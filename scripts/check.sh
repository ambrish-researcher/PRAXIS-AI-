#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export npm_config_cache="${npm_config_cache:-/tmp/praxis-npm}"
.venv/bin/python -m pytest backend/tests -q
npm run build --prefix frontend
# Requires scripts/dev.sh running in a separate terminal and Chromium installed.
(cd frontend && npm run test:e2e)
