# Observed validation

Validated in this cloud instance on 2026-10-27. These results do not establish publication, fresh-task snapshot restoration, production readiness or live sponsor access.

## Reproduction

`bash scripts/setup.sh` completed with the locked Python/npm dependencies, production frontend build, and digest-verified sandbox image. The script was rerun after initial installation to confirm repeatability. `bash scripts/dev.sh` restarted the API/frontend; persisted mission history remained available.

With those services running, `bash scripts/check.sh` completed with exit status 0:

- **17 backend tests passed**, 0 failed, 0 skipped. Includes actual data SQL calculations/artifacts, research quotation provenance/conflicts, software approval → sandbox execution → parser diagnosis/revision → contract/HTTP verification, successful skill transfer, retained failed transfer, malformed inputs, unsupported objectives, cancellation, timeout, dependency gate, three-attempt retry budget, worker restart recovery, persisted SSE replay, authentication/origin checks, missing provider configuration, mocked model discovery/error sanitization, and real sandbox UID/read-only/secret-exclusion/timeout/cancellation checks.
- **3 Chromium browser end-to-end tests passed**, 0 failed, 0 skipped. Covers landing/workspace, CSV execution and artifact download, experiments, actual graph rendering/selection/orbit pixel changes, searchable evidence, skill-transfer evaluation, software approval/execution, mobile supplied-source research, reduced motion, no horizontal overflow, and missing provider health state.
- **TypeScript check and Vite production build passed.** Three.js is split into a lazy scene chunk/vendor chunk. Fonts are bundled locally.
- **npm audit: 0 vulnerabilities**, including development dependencies, after updating Vite to 7.3.7.
- **git diff --check passed.**

The backend suite emits one upstream Starlette TestClient deprecation warning about httpx; tests execute and pass. Chromium tests emit Node color-environment warnings, unrelated to test outcomes.

## Current-instance functional evidence

`GET /api/health` returned `status=ok`, `worker=true`, `sandbox=true`, `storage=sqlite`. Eight actual browser-created missions were persisted by final validation, with completed software, data and research domains. Repeated tests create additional ordinary mission records; they are not seeded completion fixtures. Local `.praxis` state is ignored by Git.

The generated calculator candidate passed 8/8 arithmetic/safety cases after the limited summation baseline failed the richer contract. A separate container started the delivered HTTP app, verified its HTML and checked `(2+3)*4 == 20` through an actual HTTP request. The downloadable ZIP contains the tested source, not placeholder artifacts.

CSV statistics are computed against supplied rows, not invented values. Synthetic detector calibration and held-out fixtures are clearly labeled. The source report retains limitations about anomalies and causes. Research comparisons quote exact supplied source text and retain numeric disagreements without claiming which source is true.

## Integrations

Actual local health requests for NVIDIA and Nightshift returned `not_configured / Missing server-side configuration`. No external sponsor inference request succeeded or was represented as tested. Model discovery behavior is unit-tested with explicitly mocked HTTP responses; those do not count as live service verification. Meterless Agent Engine has no verified interface supplied; live Zetaris connector is unimplemented.

## Visual inspection

Desktop landing/workspace, experiment, graph and 390px mobile screenshots were captured and inspected during development. The original metallic sculpture renders, the real mission graph responds to orbit controls and node selection, and mobile layouts have no page-level horizontal overflow. Screenshot output is local ignored test output (`frontend/test-results` when using the check script). This is visual/functional inspection, not a cross-device GPU benchmark or accessibility certification.

## Delivery scope

Install/start configuration fields were saved to the cloud environment draft for user review; saving does not apply or publish a snapshot. The implementation is a local commit, not pushed or externally deployed. Review and save changes in environment settings, then publish through the product if desired. Fresh-task restoration of local-only commits has not been independently verified.

See `limitations.md` for exact remaining work toward the broader master directive, including general model-driven planning, broader coding/research, live sponsor connectors and production operations.
