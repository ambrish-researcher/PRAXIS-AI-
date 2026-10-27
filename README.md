# PRAXIS — evidence-grounded intelligence

PRAXIS turns an objective into a validated tool plan, executes real operations, compares strategies, verifies outputs, and saves transferable procedures. The original bounded preview is extended rather than replaced.

## Run the complete local application

```bash
cd /workspace/PRAXIS-AI-
bash scripts/setup.sh
bash scripts/dev.sh
```

Prerequisites: Python 3.12+, uv, Node 22.12+ (tested on 24), npm, local Linux Docker daemon, and system Chromium for browser tests. The frontend uses port 5173; FastAPI uses port 8000. Both development services bind loopback. One API process owns the SQLite queue. Do not use multiple API workers with the same data directory. Each cloud task already has an isolated checkout; do not create a Git worktree unless requested.

## Intelligence and execution

- **NVIDIA Nemotron / Meterless Nightshift planning:** model-generated mission specifications are validated against a strict Pydantic schema, registered tool IDs, allowed options, supplied input columns and acyclic dependencies. The default NVIDIA model is `nvidia/nemotron-3.5-lightning-30b-a3b`; successful inference is never assumed. Provider output is data, not executable code or commands.
- **Controlled adaptation:** two plan-validation attempts; at most one execution replan after an actual failure. A replan must change failed-tool options, preserve completed tasks and tool scope, and satisfy policy again. Tool verifiers remain fixed, independent of the model. Model-written success criteria describe intent; the enforced acceptance gates are the tool contracts and artifact-integrity checks.
- **Honest fallback:** automatic planning uses NVIDIA when configured and records transport failures before falling back offline. Explicit provider mode fails with a clear error instead of pretending inference occurred. Offline mode composes registered workflows from supplied inputs.
- **Durability:** mission state, dependency steps, real events, provenance, experiment results, decisions, skills and artifacts persist under `.praxis/` (ignored by Git). Cancellation, timeouts, approval gates, bounded retries and interrupted-worker recovery remain enabled.

## Registered tools

| Tool | Executed work and independent checks |
| --- | --- |
| `software` | Calculator HTTP app: generate source, run 8 arithmetic/safety cases in Docker, diagnose baseline parser failure, revise, retest, separately verify HTTP output, export ZIP. |
| `workspace` | Task, inventory or contact CRUD app: SQLite persistence, typed record schemas, seven actual HTTP CRUD/rejection cases before and after validation improvement, separate server-restart persistence check, source ZIP. |
| `data` | CSV schema inspection, SQLite aggregates, median/MAD anomalies, measured synthetic strategy calibration, independent Python aggregate checks and held-out fixture, chart/report/reproduction artifacts. |
| `analytics` | Grouped SQL aggregates or Pearson correlation on named CSV columns. Separate Python grouping or centered-dot-product calculations verify outputs. |
| `research` | Exact passage retrieval over supplied sources, lexical strategy comparison, provenance checks and narrowly defined numeric-claim conflicts. No live web research or truth verification. |
| `synthesis` | Combine real upstream outputs into an evidence dossier, independently verify artifact hashes, and compare exact `<column> total` source claims with computed CSV totals. Numeric agreement does not establish source authority or unit equivalence. |

The UI includes an original physically lit interactive 3D landing sculpture, responsive mission command center, validated tool DAG/contract, live execution stream, real-data intelligence graph with orbit/zoom/selection/focus/filtering, experiments, evidence search, auditable decisions and skill evaluations. The renderer reuses its context/camera across mission updates, caps rendering quality/frame rate, pauses offscreen, disposes resources, respects reduced motion and preserves keyboard-accessible node inspection.

## Fast judge demonstration

1. Enter the workspace and create a mission. Choose **Cross-domain dossier** and **Offline** (or explicit NVIDIA only after configuring and verifying it). The supplied illustrative CSV/documents execute data + research + synthesis, producing actual statistics, source conflicts and a source-to-data comparison.
2. Choose **Build a task board**. Review the validated plan, approve restricted test execution, watch the baseline fail input-validation cases and the candidate pass all seven HTTP checks plus an independent persistence test. Download the tested source.
3. Launch a second data or record-app mission. Skill library shows a separate independent transfer evaluation. Failed transfers are retained. This is procedural reuse, not model fine-tuning.
4. Explore the graph and decision inspector. Evidence, events, metrics and artifact hashes correspond to actual backend records.

See [demo](docs/demo.md), [sprint evidence](docs/sprint.md) and [deployment](docs/deployment.md).

## Providers and credentials

`.env.example` documents settings but is **not automatically loaded**. Export server variables or configure them securely in hosting settings. Never place keys in frontend variables or commit `.env` values.

- NVIDIA: `NVIDIA_API_KEY`, optionally `NVIDIA_BASE_URL` and `NVIDIA_MODEL`. Authorize `integrate.api.nvidia.com` for the default endpoint. `POST /api/integrations/nvidia/health` discovers the exact model; real mission planning then calls inference. No key is currently available in this task, so live inference remains unverified.
- Meterless Nightshift: `NIGHTSHIFT_BASE_URL`, `NIGHTSHIFT_MODEL`, `NIGHTSHIFT_API_KEY`. The official documented runtime requires a real token, including on localhost; `rt-local` is rejected. The adapter normalizes base URL suffixes and sends documented app/scope headers. Cloud loopback cannot reach the user's Windows machine. Model discovery distinguishes unauthorized from offline.
- Meterless Agent Engine: official repository documentation was investigated. Its open engines are local implementation specs/reference/conformance suites, not a hosted Agent Engine API. No undocumented SDK/endpoint is implemented and no conformance claim is made. See the pinned documentation references in `docs/sprint.md`.
- Zetaris: live connector remains modular/pending authoritative installation-specific documentation and reachable infrastructure. CSV exports are ordinary inputs, not a claimed live integration.

Only objective/schema/planning feedback are sent to the planner. Raw CSV rows and source-document text are not sent by this implementation. Inference prompts and schema labels remain untrusted; all execution permissions are enforced server-side.

## Test

With `scripts/dev.sh` running:

```bash
bash scripts/check.sh
```

Or run `.venv/bin/python -m pytest backend/tests -q`, `npm --cache /tmp/praxis-npm run build --prefix frontend`, then `(cd frontend && npm --cache /tmp/praxis-npm run test:e2e)`. Browser tests use `/usr/bin/chromium` unless `CHROMIUM_PATH` is set. See `docs/sprint.md` for current observed outcomes; initial-preview results are retained in `docs/validation.md` as historical evidence.

## Secure deployment and limits

`Dockerfile`, `render.yaml` and `frontend/vercel.json` prepare production web serving and a Vercel same-origin API proxy. Hosted startup requires demo authentication. Optional `PRAXIS_DEMO_PASSWORD` enables rate-limited password login and signed HttpOnly/SameSite sessions; use HTTPS, secure cookies and exact `PRAXIS_ALLOWED_ORIGINS`. This is shared judge/demo access, not multi-tenant identity. API bearer authentication remains available for API clients.

A Render web container can run the persistent planner and data/research tools; the software tools additionally need a Docker-capable execution host. The production web image deliberately does not add a privileged daemon or unsafe fallback. Vercel alone cannot run the platform. Full hosting requirements and current external blockers are explicit in [deployment.md](docs/deployment.md).

PRAXIS remains bounded: approved calculator/record schemas, CSV analytics and supplied-source research. It does not execute unrestricted model code, browse arbitrary sites, prove causal/factual truth, fine-tune a model, or provide production multi-user infrastructure. No performance superiority over NVIDIA ASPIRE is claimed. See [remaining limitations](docs/limitations.md).
