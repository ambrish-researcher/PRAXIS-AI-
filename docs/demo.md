# Reproducible demo

Start `bash scripts/dev.sh`, enter the workspace, and use the three capability cards. The example fields are editable and contain illustrative inputs, not preloaded success records.

## 1. Software execution and improvement

Select Software and launch the default calculator objective. The backend stops at WAITING_FOR_APPROVAL. Review the sandbox scope and click Approve sandbox execution. In the execution theater, inspect the baseline's actual failed arithmetic cases, the diagnosis, candidate revision, eight-case retest and independent HTTP checks. Experiments displays measured before/after pass counts. Download `calculator-source.zip`, extract it on your development machine, run `python server.py` and test an expression in the generated web app.

The baseline is a legitimate limited summation strategy, not deliberately corrupted code; it cannot meet the richer arithmetic contract. The candidate supports whitelisted arithmetic with no eval. Unsupported application requests fail explicitly.

## 2. Data investigation

Select Data and use `examples/revenue.csv` or edit the CSV field. Launch the mission. Inspect the SQL aggregates, anomaly rows, independent verification evidence and SVG/report downloads. The calibration experiment is synthetic and explicitly labeled. Findings about uploaded observations use their actual values. The report compares possible explanations without claiming causes.

Run another Data mission after changing the values (for example double revenue observations). Skill library now shows the original validation and a transfer evaluation, with a separate mission ID and its independent checks. Submit malformed CSV on a further mission to see a failed transfer retained rather than silently dropped.

## 3. Research

Select Research and use the default source array or `examples/research-sources.json`. The example reports are illustrative, not real published studies. A matching metric has two different lifetime values. Inspect exact quotations, source timestamps, typed contradiction relationships and the report's uncertainty. Download sources, analysis and reproduction script. Run `python reproduce.py` beside `sources.json` and `analysis.json` to reproduce ranked passages.

## 4. Reliability and integrations

Create an unsupported objective to inspect honest failure. Cancel a nonterminal mission. Retry a failed mission up to the three-attempt budget. The automated suite also checks active sandbox cancellation, timeout, restart recovery, durable SSE replay, dependency gates, secret exclusion, read-only execution and missing provider configuration.

Open Integrations and run health checks. With no keys/endpoint configured, they report missing configuration. Configure server variables securely and authorized network access, restart the API, then rerun discovery; a configured badge alone is not readiness. No external model or service results are fabricated.

## Graph and accessibility

Open a completed mission's Intelligence graph. Drag to orbit, scroll to zoom, filter by type, and select a node. The adjacent node list exposes the same evidence through keyboard navigation. Reduced-motion settings stop automatic landing rotation. Mobile navigation exposes all panels without horizontal page overflow.
