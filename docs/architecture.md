# PRAXIS execution architecture

React/TypeScript/Three.js → same-origin API → FastAPI → one durable SQLite mission worker → registered tool adapters → independent verifiers → evidence/artifacts/skills.

## Planning boundary

`planning.py` defines strict task/mission schemas. NVIDIA or documented Nightshift transport returns JSON tool proposals, not executable code. Allowed task IDs, typed tool options, actual input columns, unique tools and an acyclic dependency graph are validated. The planner sees objective/input schema and sanitized feedback, not raw document text or CSV rows. `integrations.py` retains server-side credentials, TLS checks and redirect protection. Explicit-provider failure is visible; automatic planning can record a transport failure and fall back offline.

`runner.py` topologically orders validated tasks, constructs four internal verification stages per adapter, and executes only registered functions. Approval is tied to the entire plan digest before any generated-code testing. A real failure may trigger one model replan; completed tasks and tool scope must remain intact, failed-tool options must change, and the new proposal is revalidated. No model-authored criteria can disable the fixed tool verifiers.

## Tools and independent checks

- `engine.py`: preserved calculator synthesis/improvement, CSV investigation, source research and skill persistence.
- `operations.py`: grouped SQL/reference-Python analytics, statistics/reference-dot-product correlation, typed record-app generation, and measured upstream dossier synthesis.
- `templates.py` / `workspace_template.py`: reviewed application-owned code. Model strings are encoded as typed configuration/data. Generated apps are tested in the restricted Docker sandbox; no arbitrary model commands are accepted.
- `sandbox.py`: local Docker daemon, digest-pinned Python image, no network, read-only source/root, dropped capabilities, non-root UID, process/memory/CPU limits, cancellation and timeout. No host execution fallback.
- `store.py`: SQLite WAL, mission JSON, append-only event stream, versioned procedures/evaluations. One process per database; this is not a distributed lease system.

Every selected tool must complete its independent contract. All artifact digests are recomputed before overall completion. Dossiers retain source-qualified uncertainty and can compare exact `<column> total` claims with actual CSV aggregates; numeric agreement is not a factual-authority or causal proof.

## Durable observability

CREATED → ANALYZING → validated PLANNING → approval when required → RUNNING / EXPERIMENTING → VERIFYING → COMPLETED, FAILED or CANCELLED. All states and tool events originate in actual backend operations. Per-task DAG status, detailed dependency steps, parsed plan provenance, measured experiments, source hashes, concise decision rationales and skill evaluations persist. Interrupted nonterminal work restarts from immutable input, and legacy approval waits are upgraded to a validated plan requiring fresh approval. Completed history is retained.

## Browser experience

`MissionIntelligence.tsx` renders the actual validated contract and tool graph. `Universe.tsx` retains its WebGL context, camera and controls across data updates, disposes replaced geometry, caps pixel ratio/frame rate, pauses offscreen and respects reduced motion. Node selection, hover, focus and active-task pulses refer to real records. Visibility recovers after programmatic scroll/viewport restoration; user interaction wakes rendering. Keyboard node lists remain available without WebGL.

## Hosted demo boundary

`auth.py` provides shared-password demo access with rate-limited login, signed expiring HttpOnly/SameSite sessions and exact-origin mutation checks. This is not multi-tenant identity. Production startup requires authentication, initializes its dedicated persistent directory, drops to UID 10001, and applies a private data-file umask before the API starts. The Vercel serverless proxy forwards API/session/artifact streams to a fixed configured HTTPS backend without provider credentials in the bundle.

The production web image supports persistent planner/data/research operations. Standard Render web hosting does not supply the local Docker executor used by the software tools. Full generated-software execution requires an authorized Docker-capable Linux host; no unimplemented remote runner is represented as available. See deployment.md.
