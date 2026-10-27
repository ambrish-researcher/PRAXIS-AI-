#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/praxis-uv}"
export npm_config_cache="${npm_config_cache:-/tmp/praxis-npm}"
uv venv --allow-existing .venv
uv pip sync --python .venv/bin/python backend/requirements.lock
npm ci --prefix frontend
npm run build --prefix frontend
# Networkless execution uses a digest-pinned standard Python image.
env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
  docker --host=unix:///var/run/docker.sock pull python:3.12-slim@sha256:12316debbfb86890f6b2d825820612741ba527ad5a44e3902759141d572bfe8f
