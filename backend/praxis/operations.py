"""Additional registered tools. Each operation executes and verifies its own output."""

import csv
import hashlib
import html
import io
import json
import math
import sqlite3
import statistics
import zipfile
from collections import defaultdict
from uuid import uuid4
from .planning import AnalyticsOptions, WorkspaceOptions
from . import workspace_template


def analytical_rows(raw):
    reader = csv.DictReader(io.StringIO(raw), strict=True)
    fields = reader.fieldnames or []
    rows = list(reader)
    if (
        not 5 <= len(rows) <= 10000
        or len(set(fields)) != len(fields)
        or any(None in row or any(v is None for v in row.values()) for row in rows)
    ):
        raise ValueError(
            "Analytics requires 5–10,000 rectangular CSV rows with unique columns"
        )
    return fields, rows


def finite(value):
    number = float(value)
    if not math.isfinite(number) or abs(number) >= 1e100:
        raise ValueError("Analytical values must be finite and bounded")
    return number


def analytics(e, mid):
    e.step(mid, 0, "running", "Validating actual CSV rows and requested column names")
    m = e.store.get(mid)
    opts = AnalyticsOptions.model_validate(m["active_options"])
    fields, rows = analytical_rows(m["csv_data"])
    source = e.evidence(mid, "Analytical source CSV", m["csv_data"], "input:csv")
    e.step(mid, 0, "completed", f"Validated {len(rows)} supplied rows")
    e.step(
        mid, 1, "running", "Executing requested analytical operation over actual input"
    )
    if opts.operation == "group":
        if opts.group_by not in fields or opts.value_column not in fields:
            raise ValueError("Group operation requires existing columns")
        grouped = defaultdict(list)
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE observations(category TEXT,value REAL)")
            pairs = [
                (row[opts.group_by], finite(row[opts.value_column])) for row in rows
            ]
            db.executemany("INSERT INTO observations VALUES (?,?)", pairs)
            sql = "SELECT category,COUNT(*),SUM(value),AVG(value),MIN(value),MAX(value) FROM observations GROUP BY category ORDER BY category"
            output = [
                dict(zip(["category", "count", "sum", "mean", "min", "max"], record))
                for record in db.execute(sql)
            ]
        for category, value in pairs:
            grouped[category].append(value)
        e.step(mid, 1, "completed", f"SQL computed {len(output)} group aggregates")
        e.step(
            mid,
            2,
            "running",
            "Comparing SQLite output with independent Python grouping",
        )
        for record in output:
            values = grouped[record["category"]]
            if (
                record["count"] != len(values)
                or not math.isclose(
                    record["sum"], math.fsum(values), rel_tol=1e-10, abs_tol=1e-10
                )
                or not math.isclose(
                    record["mean"],
                    statistics.mean(values),
                    rel_tol=1e-10,
                    abs_tol=1e-10,
                )
            ):
                raise ValueError("Group aggregate verification failed")
        result = {
            "operation": "group",
            "group_by": opts.group_by,
            "value_column": opts.value_column,
            "groups": output,
            "sql": sql,
        }
        verified = "SQLite grouped totals and means match independent Python reference"
    else:
        if opts.x_column not in fields or opts.y_column not in fields:
            raise ValueError("Correlation requires existing columns")
        x = [finite(r[opts.x_column]) for r in rows]
        y = [finite(r[opts.y_column]) for r in rows]
        if len(set(x)) < 2 or len(set(y)) < 2:
            raise ValueError(
                "Correlation is undefined for constant columns; choose varying columns"
            )
        r = statistics.correlation(x, y)
        e.step(
            mid, 1, "completed", "Computed Pearson correlation using Python statistics"
        )
        e.step(mid, 2, "running", "Independently evaluating centered dot products")
        mx, my = statistics.mean(x), statistics.mean(y)
        dx, dy = [v - mx for v in x], [v - my for v in y]
        reference = math.fsum(a * b for a, b in zip(dx, dy)) / math.sqrt(
            math.fsum(a * a for a in dx) * math.fsum(b * b for b in dy)
        )
        if not math.isclose(r, reference, rel_tol=1e-10, abs_tol=1e-10):
            raise ValueError("Independent correlation verification failed")
        result = {
            "operation": "correlate",
            "x_column": opts.x_column,
            "y_column": opts.y_column,
            "rows": len(rows),
            "pearson_r": r,
            "reference_r": reference,
            "causation_established": False,
        }
        verified = (
            "Pearson correlation matches independent centered-dot-product reference"
        )
    evidence = e.evidence(
        mid,
        "Executed analytical result",
        json.dumps(result),
        "tool:analytics",
        relationships=[{"type": "derived_from", "target": source["id"]}],
    )
    e.step(mid, 2, "completed", verified)
    e.step(mid, 3, "running", "Writing analytical report and machine-readable output")
    e.artifact(mid, "analytics.json", json.dumps(result, indent=2), "json")
    e.artifact(mid, "analytical-input.csv", m["csv_data"], "csv")
    e.artifact(
        mid,
        "analytics-report.md",
        "# Verified analytics\n\n"
        + m["objective"]
        + "\n\n```json\n"
        + json.dumps(result, indent=2)
        + "\n```\n\nVerification: "
        + verified
        + "\n\nLimitations: association is not causation; source authenticity is not independently established.",
    )
    e.decision(
        mid,
        "Accept measured analytical result",
        ["Grouped SQL aggregation", "Pearson correlation"],
        "Selected requested analytical operation over named input columns",
        [source, evidence],
        verified,
        "Association does not establish causes; sampling and data collection remain unverified.",
    )
    e.step(mid, 3, "completed", "Analytical artifacts persisted")
    return {
        "summary": f"Executed {opts.operation} on {len(rows)} supplied rows.",
        "verification": verified,
        "analytics": result,
        "limitations": [
            "No causal inference",
            "Finite complete numeric values required",
        ],
    }


def workspace(e, mid):
    opts = WorkspaceOptions.model_validate(e.store.get(mid)["active_options"])
    config = {
        **opts.model_dump(),
        "field": {"tasks": "status", "inventory": "quantity", "contacts": "email"}[
            opts.kind
        ],
    }
    e.step(
        mid,
        0,
        "running",
        f"Generating a {opts.kind} application with SQLite persistence and HTTP CRUD",
    )
    folder = e.store.root / "work" / mid / "workspace"
    folder.mkdir(parents=True, exist_ok=True)
    folder.chmod(0o755)
    encoded = repr(json.dumps(config))
    document = workspace_template.HTML.replace(
        "__TITLE__", html.escape(opts.title)
    ).replace(
        "__CONFIG_JSON__",
        json.dumps(config)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026"),
    )

    def write(name, content):
        p = folder / name
        p.write_text(content)
        p.chmod(0o644)

    for name, content in {
        "index.html": document,
        "test_crud.py": workspace_template.TEST.replace("__CONFIG__", encoded),
        "verify_persistence.py": workspace_template.VERIFY.replace(
            "__CONFIG__", encoded
        ),
    }.items():
        write(name, content)
    baseline = workspace_template.SERVER.replace("__CONFIG__", encoded).replace(
        "__STRICT__", "False"
    )
    write("server.py", baseline)
    e.step(
        mid,
        0,
        "completed",
        "Application, CRUD contract and independent persistence test generated",
    )
    e.step(
        mid,
        1,
        "running",
        "Testing baseline CRUD and input validation in the isolated sandbox",
    )
    e.state(
        mid,
        "EXPERIMENTING",
        "Measuring input correctness before enabling stricter validation",
    )
    before = e.sandbox_test(mid, folder, "test_crud.py")
    try:
        before_metrics = json.loads(before["output"].strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise ValueError("Baseline sandbox produced no usable test report")
    first = e.evidence(
        mid,
        "Record application baseline contract",
        json.dumps(before),
        "sandbox:workspace-baseline",
    )
    e.step(
        mid,
        1,
        "completed",
        f"Baseline passed {before_metrics['passed']}/{before_metrics['total']} CRUD/validation cases",
    )
    e.step(
        mid,
        2,
        "running",
        "Enabling strict field/type validation and independently testing persistence",
    )
    e.store.event(
        mid,
        "diagnosis",
        "Baseline CRUD accepts invalid input; add name, field allowlist and typed-value validation",
    )
    write("server.py", baseline.replace("STRICT = False", "STRICT = True"))
    after = e.sandbox_test(mid, folder, "test_crud.py")
    try:
        after_metrics = json.loads(after["output"].strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise ValueError("Candidate sandbox produced no usable test report")
    accepted = (
        after["exit_code"] == 0
        and after_metrics["passed"] == after_metrics["total"] == 7
    )
    e.store.append(
        mid,
        "experiments",
        {
            "id": uuid4().hex,
            "hypothesis": "Strict record validation preserves CRUD and rejects invalid or unknown input",
            "baseline": "CRUD with permissive input validation",
            "candidates": ["Typed input validation with an explicit field allowlist"],
            "procedure": "Run the same seven HTTP cases before and after validation changes in separate isolated containers",
            "metrics": {
                "baseline_passed": before_metrics["passed"],
                "candidate_passed": after_metrics["passed"],
                "total": 7,
            },
            "results": [before_metrics, after_metrics],
            "accepted": accepted,
            "acceptance_criteria": "7/7 CRUD and rejection cases; independent persistence restart test",
            "failure_analysis": "Permissive baseline accepts invalid fields and values. Candidate must reject these without breaking CRUD.",
            "verification_status": "passed" if accepted else "failed",
        },
    )
    if not accepted:
        raise ValueError("Generated record application failed its correctness contract")
    e.state(
        mid,
        "VERIFYING",
        "Independently verifying SQLite persistence across server restart",
    )
    persistence = e.sandbox_test(mid, folder, "verify_persistence.py")
    if persistence["exit_code"] != 0:
        raise ValueError("Independent generated-app persistence verification failed")
    second = e.evidence(
        mid,
        "Verified record application",
        json.dumps({"contract": after, "persistence": persistence}),
        "sandbox:workspace-candidate",
        relationships=[{"type": "improves", "target": first["id"]}],
    )
    e.step(
        mid,
        2,
        "completed",
        "7/7 HTTP contract cases and independent persistence verification passed",
    )
    e.step(
        mid,
        3,
        "running",
        "Packaging verified source and recording the reusable record-app strategy",
    )
    write(
        "README.md",
        f"# {opts.title}\n\nRun `python server.py` with Python 3.12+. Open the local app on port 8080. SQLite records persist in workspace.sqlite; do not expose this unauthenticated generated app publicly.\n\nKind: {opts.kind}. Fixed, application-owned templates; no arbitrary model code.\n",
    )
    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in folder.iterdir():
            archive.write(path, path.name)
    e.artifact(mid, "workspace-source.zip", bundle.getvalue(), "archive")
    e.artifact(
        mid,
        "workspace-verification.json",
        json.dumps(
            {
                "baseline": before_metrics,
                "candidate": after_metrics,
                "persistence": persistence,
            },
            indent=2,
        ),
        "json",
    )
    e.decision(
        mid,
        "Use strictly validated record storage",
        ["Permissive record storage", "Typed record validation"],
        "Measured invalid-input failures justify stricter validation; independent restart test checks real persistence",
        [first, second],
        "7/7 HTTP cases plus persistence and HTML checks passed",
        "Bounded tasks/inventory/contact schemas only; not arbitrary app generation.",
    )
    e.skill(
        mid,
        "software",
        "Verified record-management application",
        {
            "adapter": "workspace",
            "strategy": "validated_crud",
            "kind_support": ["tasks", "inventory", "contacts"],
        },
        {
            "passed": True,
            "tests": [
                "7 HTTP CRUD/validation cases",
                "SQLite restart persistence",
                "HTML served",
            ],
        },
        "Local single-user generated apps; no authentication or production deployment included.",
    )
    e.step(
        mid,
        3,
        "completed",
        "Source ZIP and independently verified reusable strategy saved",
    )
    return {
        "summary": f"Built a working {opts.kind} record application with SQLite persistence.",
        "verification": "7/7 CRUD contract cases; independent restart persistence and HTML checks passed",
        "limitations": [
            "Tasks/inventory/contacts schemas only",
            "Generated app is local single-user software; not a public deployment",
        ],
    }


def synthesis(e, mid):
    m = e.store.get(mid)
    e.step(mid, 0, "running", "Collecting actual completed upstream tool outputs")
    task = next(t for t in m["execution_graph"] if t["id"] == m["active_task"])
    upstream = {key: m.get("task_results", {})[key] for key in task["depends_on"]}
    e.step(mid, 0, "completed", f"Collected {len(upstream)} measured tool outputs")
    e.step(mid, 1, "running", "Resolving evidence provenance and remaining uncertainty")
    evidence = list(m["evidence"])
    if not evidence:
        raise ValueError("Synthesis requires actual evidence")
    e.step(mid, 1, "completed", f"Resolved {len(evidence)} evidence records")
    e.step(mid, 2, "running", "Recomputing upstream artifact hashes")
    for artifact in m["artifacts"]:
        path = e.store.root / "artifacts" / mid / artifact["name"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
            raise ValueError("Upstream artifact hash mismatch")
    e.step(
        mid,
        2,
        "completed",
        "All upstream artifact digests match their stored manifests",
    )
    e.step(
        mid,
        3,
        "running",
        "Writing a consolidated evidence dossier without unsupported inference",
    )
    dossier = {
        "objective": m["objective"],
        "upstream_results": upstream,
        "evidence": [
            {
                "id": v["id"],
                "title": v["title"],
                "locator": v["locator"],
                "sha256": v["sha256"],
                "uncertainty": v["uncertainty"],
            }
            for v in evidence
        ],
        "limitations": list(
            dict.fromkeys(
                x for r in upstream.values() for x in r.get("limitations", [])
            )
        ),
    }
    e.artifact(mid, "dossier.json", json.dumps(dossier, indent=2), "json")
    report = ["# Mission evidence dossier", "", m["objective"], ""]
    for key, result in upstream.items():
        report += [
            f"## {key}",
            result["summary"],
            "Verification: " + result["verification"],
            "",
        ]
    report += ["## Provenance"] + [
        f"- [{v['id'][:8]}] {v['title']} — {v['locator']}" for v in evidence
    ]
    report += ["", "## Remaining limitations"] + [
        "- " + limit for limit in dossier["limitations"]
    ]
    e.artifact(mid, "dossier.md", "\n".join(report))
    e.step(mid, 3, "completed", "Consolidated source-qualified dossier persisted")
    return {
        "summary": f"Assembled {len(upstream)} actual tool results into an evidence dossier.",
        "verification": "Upstream results resolved and every upstream artifact hash independently verified",
        "limitations": dossier["limitations"],
    }
