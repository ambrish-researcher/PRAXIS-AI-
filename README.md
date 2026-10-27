# PRAXIS

An evidence-grounded local mission workspace with real execution, measured experiments, persistent audit records, and an interactive 3D intelligence graph.

This is a working **bounded research preview**, not the complete general-purpose autonomous intelligence platform described in the master directive. The planner selects explicit capability adapters. Optional model inference proposes plans; model output is not silently executed.

## Run

Prerequisites: Linux/macOS development shell, Python 3.12+, `uv`, Node 22.12+ (tested with 24), npm, local Docker daemon, and Chromium for browser tests. The cloud environment already has these tools. The sandbox uses the local Unix Docker socket and therefore requires Linux-style Docker socket access.

```bash
cd /workspace/PRAXIS-AI-
bash scripts/setup.sh
bash scripts/dev.sh
```

The API listens on port 8000 and the frontend on port 5173, both bound to loopback. On your own machine, open the frontend locally. The onboarding UI does not provide a localhost web preview. Stop the script with Ctrl+C. Run only **one** API worker against a data directory.

The environment was implemented in the selected `ambrish-researcher/PRAXIS-AI-` checkout (with trailing hyphen), rather than creating a second repository for the slightly different name in the directive. No Git worktree is needed: every cloud task already has an isolated environment.

## What works

| Workflow | Actual execution | Boundaries |
| --- | --- | --- |
| Software | Generates a calculator HTTP application, executes an eight-case arithmetic/safety contract in Docker, diagnoses a limited summation parser, revises it to a restricted AST evaluator, retests, independently checks the HTTP app, and exports a source ZIP | Calculator objectives only; template synthesis, not general AI code generation. Approval required before execution. |
| Data | Imports CSV, executes SQLite aggregates, compares z-score and median/MAD detection on labeled calibration data, checks uploaded-data aggregates independently in Python, tests a held-out fixture, and exports an SVG chart, JSON statistics, report, and reproduction script | 5–10,000 rows; max 1 MB; 1–40 unique columns; complete finite numeric columns. No imputation or causal inference. Calibration is explicitly synthetic, not an uploaded-data ground-truth benchmark. |
| Research | Indexes supplied documents, retrieves exact passages, measures lexical coverage of two retrieval strategies, compares matching numeric claims, verifies quotations, and exports source-qualified findings and reproduction files | At least two supplied sources; no live web browsing. Keyword ranking is not semantic entailment. Contradictions use matching `metric = number` / `metric: number` syntax and identical units; authenticity and truth remain unverified. |

All three workflows persist state, task dependencies, events, evidence provenance, decision explanations, experiments, and downloadable artifacts. Software/data strategies persist as versioned skills; subsequent missions load the procedure and independently evaluate transfer, including recording failures. This is procedural reuse, **not model fine-tuning**.

The interface includes an original interactive 3D landing sculpture, mission command center, live execution stream, data-connected graph with orbit/zoom/filter/selection, experiment laboratory, evidence search, decision inspector, skill history, and integration status. Keyboard-accessible node lists and WebGL failure fallback preserve access to mission data. Rendering is lazy-loaded, pixel-ratio-capped, throttled to 30 fps, paused offscreen, and respects reduced motion.

## Verify

With `scripts/dev.sh` running in another terminal:

```bash
bash scripts/check.sh
```

Or separately:

```bash
.venv/bin/python -m pytest backend/tests -q
npm --cache /tmp/praxis-npm run build --prefix frontend
cd frontend
npm --cache /tmp/praxis-npm run test:e2e
```

Browser tests use `/usr/bin/chromium`; set `CHROMIUM_PATH` for another system installation. No browser binary download is required in this cloud environment. See [validation](docs/validation.md) for observed results, and [demo](docs/demo.md) for reproducible acceptance flows.

## Configuration and integrations

[.env.example](.env.example) lists server-side settings. It is documentation, **not automatically sourced**. Export required variables before starting the API. Never commit real values or put inference keys in frontend variables.

- **NVIDIA Nemotron:** OpenAI-compatible `/models` discovery and `/chat/completions` client. Default model: `nvidia/nemotron-3.5-lightning-30b-a3b`. A real health request checks whether this exact configured model is listed; availability is not assumed. Configure `NVIDIA_API_KEY`, optionally `NVIDIA_BASE_URL` and `NVIDIA_MODEL`. Allow the configured HTTPS destination through environment networking; the default is `integrate.api.nvidia.com`.
- **Meterless Nightshift:** configurable OpenAI-compatible base URL, key, and model. Cloud loopback does not reach the user's Windows service. A remote endpoint must use authorized HTTPS access. An unauthenticated loopback development endpoint is permitted.
- **Meterless Agent Engine:** no verified API documentation or credentials were supplied, and no vendor SDK/interface was available in the repository. Status is explicitly unverified. No invented integration is implemented.
- **Zetaris:** live connector not implemented or verified. CSV exports are supported as ordinary data inputs. A live connector needs installation-specific supported SQL/JDBC/REST documentation, connection details, and authorized network access. No undocumented endpoints are called.

`GET /api/integrations` reports configuration metadata without secrets. `POST /api/integrations/nvidia/health` and `POST /api/integrations/nightshift/health` run real discovery only when configured. `POST /api/proposals` accepts `{ "provider": "nvidia", "objective": "..." }` and returns an inference proposal; this does not execute it. Inference is optional and is not wired into the deterministic mission planner.

No live sponsor inference was verified in this environment: required keys/URLs were absent. Missing-configuration behavior and synthetic HTTP responses are tested separately and do not count as live integration verification.

## Safety and persistence

SQLite and mission artifacts live in `.praxis/` by default, configurable with `PRAXIS_DATA_DIR`. This directory is ignored by Git but contains user-provided data: treat it as private. Stop the service before copying the directory for backup; do not assume SQLite WAL files can be discarded while running.

Generated tests execute with no network, no capabilities, non-root UID, read-only root/source mounts, bounded CPU/memory/PIDs/time, and no application credentials passed into the container. There is **no host execution fallback** when Docker is unavailable. The image is pinned by digest. Docker is a trusted administrator prerequisite, not a multi-tenant security boundary for hostile code. Only application-owned template tests execute today; no shell or arbitrary user code is accepted.

Approval is required for software test execution. Cancel/retry actions are explicit API operations; cancellation terminates active sandbox execution. Mission and tool budgets are bounded. Interrupted nonterminal missions are recovered from immutable inputs after an abrupt worker restart; graceful shutdown may mark an active mission failed and require a manual retry. Completed records survive restart.

This is a **local single-user development service**, not an Internet deployment. Both services bind loopback. Optional `PRAXIS_API_TOKEN` protects API access for API clients; the current browser UI does not supply bearer tokens. Multi-user identity, authorization, quotas, PostgreSQL/distributed workers, production TLS/reverse proxy, and remote deployment are not implemented.

See [architecture](docs/architecture.md) and [remaining work](docs/limitations.md). No NVIDIA ASPIRE performance comparison is claimed.
