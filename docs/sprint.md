# Hackathon sprint — implementation record

The existing application is preserved and extended. Backend milestone: 38 tests passed, including original workflow regression checks and new real execution tests.

## Implemented in the first milestone

- NVIDIA/Nightshift inference now supplies a schema-validated mission specification, registered tool choices and a dependency DAG. Model output is never interpreted as a shell command or arbitrary code.
- At most two structured-plan attempts; schema, input availability, dependency cycles, duplicated tools and unsupported options are checked before execution. One scope-preserving model replan is allowed after an actual tool failure, only when failed-tool options change and completed work remains intact.
- Explicit provider mode fails honestly when unavailable. Automatic mode records an inference transport failure and retains offline workflows. Missing NVIDIA credentials are visible, not represented as successful inference.
- Existing calculator/data/research tools still execute their independent contracts. Additional tools implement grouped SQL analysis, independently checked Pearson correlation, and real generated task/inventory/contact CRUD applications.
- Generated record apps use application-owned templates, typed options and SQLite. Actual isolated HTTP tests compare permissive versus strict validation; an independent server-restart test verifies persistence. Approval is bound to the validated plan digest.
- Cross-tool synthesis assembles measured outputs and provenance into a dossier. Artifact SHA-256 digests are independently recomputed before mission completion.

## Integration investigation

Official Meterless repository inspected at commit `1742dec56a66e58eef9dda2d2b865823758ca8cd`:

- https://github.com/Meterless/Meterless/blob/1742dec56a66e58eef9dda2d2b865823758ca8cd/docs/agent-ready/add-meterless-provider.md
- https://github.com/Meterless/Meterless/blob/1742dec56a66e58eef9dda2d2b865823758ca8cd/engines/README.md

The Nightshift adapter now normalizes documented URL suffixes, requires a real token (rejecting `rt-local`), sends `meterless-app: praxis` and `meterless-scope: user` on chat requests, and distinguishes unauthorized discovery from offline state. The open engines are local implementation specifications with references/conformance suites, not a documented hosted Agent Engine API. No engine conformance or live runtime claim is made. A separate request to the supplied meterless.ai page was blocked by outbound policy (CONNECT 403); GitHub docs were accessible.

Live NVIDIA inference remains blocked by absent server-side `NVIDIA_API_KEY`. A secure requirement and `integrate.api.nvidia.com` destination were saved to the environment draft; this does not supply the secret or publish runtime settings. Nightshift has no configured reachable URL/model/token. Zetaris remains modular/pending because its authoritative installation-specific interface is unverified.

## Verified final sprint slice

The working judge path is now a cross-domain revenue dossier or an approved generated record application, plus independent skill transfer. The default illustrative dossier computes CSV revenue total **1797**, retains supplied conflicting claims **1797** and **1800**, and records numeric differences **0** and **3**, without claiming source authority or causation.

The UI now exposes actual validated planner provenance, tool dependencies, execution-contract checks, per-tool progress, record-app and cross-domain presets, provider choice and analytical options. The physically lit 3D sculpture and graph retain motion/accessibility controls. Graph rendering no longer recreates its context on every event and recovers from stale intersection observations after viewport restoration.

Production preparation includes a Vercel HTTPS same-origin API proxy, Render persistent-service blueprint, combined production Docker image, rate-limited private-demo password login, signed HttpOnly sessions, exact-origin checks, and a non-root persistent-volume initializer. These configuration files do not mean a public service was deployed. The Render tier/disk in the blueprint may incur charges when a user applies it.

A real production-container smoke test passed: production HTML, anonymous API denial, session login, a completed CSV mission with independently verified sum **182**, and artifact download. The API process ran as UID **10001** against a mounted persistent state directory. Sandbox health was correctly **false** in that web-only container; no software-execution success was claimed there. A separate production-bundle Chromium login smoke test loaded the authenticated workspace and verified its HttpOnly cookie.

Final validation results are recorded below after completion. Initial failed browser checks led to concrete fixes for selector scope, graph lifecycle/visibility and generated-app approval timing. A non-root volume smoke failure led to explicit code/read permissions and dedicated state-directory initialization. No failed check was hidden or described as a pass.

## Final checks

- **43 Python backend tests passed**, zero failed/skipped, including the privacy regression proving invalid raw cell values do not reach inference replanning feedback. The sole warning is an upstream Starlette TestClient/httpx deprecation.
- **5 Chromium end-to-end flows passed**: original data/graph/evidence/transfer, calculator approval/improvement, mobile research/reduced motion, cross-domain dossier, and record-app HTTP/persistence improvement. All application output checks use actual backend execution, not UI completion fixtures.
- **3 Node proxy/security tests passed** with explicitly mocked upstream transport: HTTPS destination/path constraints, cookie/stream forwarding, configuration refusal and sanitized failures. These are not live Vercel deployment tests.
- **TypeScript / production build passed** and **npm audit reports zero vulnerabilities** including development dependencies.
- **Production Docker build and authenticated container functional smoke passed**; **production-bundle Chromium password login smoke passed**. The mounted persistent directory and non-root API process were verified. No privileged runner was added.
- Actual local NVIDIA and Nightshift health requests both returned `not_configured / Missing server-side configuration`. No live inference, hosted preview or public deployment success is claimed.

Code was committed incrementally and pushed with ordinary non-force pushes to `praxis-implementation`. `main` is unchanged. The install/start instructions and secure NVIDIA key requirement are saved in the environment draft; users must enter the key securely and review/save/publish settings through the product. Draft persistence does not apply credentials or create a public deployment.
