# Browser demo deployment

No public deployment URL is claimed until an actual hosting operation succeeds and the deployed full-stack health and functional requests pass.

## Current working demonstration

`bash scripts/dev.sh` runs the complete application in a Linux environment with Python, Node and a local Docker daemon. All six registered tools work there, including approval-gated calculator and record-app tests. The cloud onboarding UI has no port-forwarding/browser-preview tool, so its loopback ports cannot be represented as an accessible public URL.

## Render backend / Vercel frontend

1. Review the Render blueprint (`render.yaml`) on branch `praxis-implementation`. It selects a persistent-disk service tier; applying it may incur hosting charges. No service was purchased or provisioned by writing this file.
2. Configure `PRAXIS_DEMO_PASSWORD` securely. Set `PRAXIS_SESSION_SECRET` to a long random secret (the blueprint can generate it). Set `PRAXIS_ALLOWED_ORIGINS` to the exact HTTPS Render origin and Vercel preview origin, comma-separated. Set `PRAXIS_SECURE_COOKIES=1` for the public demo.
3. Configure `NVIDIA_API_KEY` server-side and authorize `integrate.api.nvidia.com` egress. Optional Nightshift configuration must point to a reachable authorized HTTPS runtime; its token remains on the server. Never use frontend `VITE_*` variables for credentials.
4. The Dockerfile builds the production React frontend and runs a single persistent FastAPI worker with SQLite/artifacts under `/var/data/praxis`. Render exposes the backend's assigned `$PORT`. `GET /api/health` must report a healthy worker.
5. For Vercel, select `frontend` as the project root. Set the server-side function variable `PRAXIS_BACKEND_URL` to the Render HTTPS origin. `frontend/api/[...path].js` proxies same-origin API requests, session cookies, artifact downloads and streaming events. It never embeds provider keys in JavaScript. SSE streams reconnect/poll the durable event log if the function duration limit expires.
6. Verify login, CSV execution, dossier artifacts, NVIDIA plan provenance (only when actual inference succeeds), evidence inspection and logout on the deployed origins.

The production bundle can also be served directly by FastAPI (`PRAXIS_SERVE_WEB=1`), so Render alone can serve UI and API with one origin. Vercel is optional to the working app, not a replacement for the backend.

## Required execution hosting boundary

**A standard Render web container is not the existing Linux Docker execution machine.** This application deliberately has no host-code execution fallback. The current sandbox adapter requires a local Unix Docker socket and the pinned Python image, with per-mission paths visible to that daemon. The supplied production web image does not install a Docker daemon or expose host access.

Therefore Render can host the persistent planner, data/research/analytics/dossier operations and UI. It cannot by itself demonstrate generated-software verification unless the service is given an authorized Docker-capable execution environment. A dedicated Linux VM running the documented repository commands is the fastest complete alternative: Python/Node for the API/UI, a local Docker daemon for restricted task execution, persistent disk, and an HTTPS reverse proxy to the frontend/API. Run one API worker. Configure the demo password, TLS cookies and exact allowed origin before exposing it publicly.

A future authenticated remote sandbox runner would allow the Render worker to delegate those jobs. That adapter is not implemented in this sprint and is not represented as working. No privileged Docker fallback or unsafe model-command execution is enabled to work around hosting constraints.

## Validation commands

```bash
bash scripts/check.sh
# Container build (ordinary hosting environment):
docker build -t praxis-demo .
# Managed cloud: retain the supplied proxy trust without copying session CA into image layers:
BUILDX_CONFIG=/tmp/praxis-buildx docker build --secret id=proxy_ca,src="$CODEX_PROXY_CERT" -t praxis-demo .
```

Run a container with an authorized persistent volume and private demo password supplied through host settings. Avoid placing real passwords in command history or repository files. Data/research readiness does not establish sandbox readiness; inspect both fields in `/api/health`.

## Remaining deployment prerequisites

Vercel/Render account access and deployment credentials have not been supplied to this task, no deployment connector is available, and no external service has been provisioned. The exact public origin therefore cannot be known or tested yet. The NVIDIA key is also absent. These are real external blockers, not fabricated successful integrations. The verified local full-stack demo remains available.
