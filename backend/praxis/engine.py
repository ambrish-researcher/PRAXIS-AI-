import csv
import hashlib
import io
import json
import math
import re
import sqlite3
import statistics
import threading
import time
import zipfile
from pathlib import Path
from uuid import uuid4
from .store import TERMINAL, now
from . import sandbox, templates

TOOLS = [
    {
        "id": "analytics",
        "name": "Grouped analytics and correlation",
        "domain": "data",
        "permission": "local_only",
        "description": "Grouped SQL aggregation or independently verified Pearson correlation over supplied numeric CSV columns.",
    },
    {
        "id": "workspace",
        "name": "Record application builder",
        "domain": "software",
        "permission": "approval_required",
        "description": "Build task, inventory or contact CRUD apps with SQLite persistence. Validate baseline, improve input validation, and verify HTTP CRUD in Docker.",
    },
    {
        "id": "synthesis",
        "name": "Evidence dossier",
        "domain": "research",
        "permission": "local_only",
        "description": "Combine actual upstream results, artifact hashes and provenance into a consolidated report; no invented conclusions.",
    },
    {
        "id": "software",
        "name": "Calculator application builder",
        "domain": "software",
        "permission": "approval_required",
        "description": "Generates a Python HTTP arithmetic app, tests two parser strategies in isolated containers, and exports source. Other application types are unsupported.",
    },
    {
        "id": "data",
        "name": "CSV investigation",
        "domain": "data",
        "permission": "local_only",
        "description": "Numeric CSV statistics, SQL aggregates, robust anomaly detection, controlled calibration and SVG/report artifacts. No causal claims.",
    },
    {
        "id": "research",
        "name": "Source comparison",
        "domain": "research",
        "permission": "local_only",
        "description": "Retrieves passages from supplied documents, compares coverage and conflicting numeric claims. No web browsing or external database access.",
    },
]


class MissionFailure(RuntimeError):
    pass


class Cancelled(RuntimeError):
    pass


def infer_domain(objective):
    text = objective.lower()
    if any(word in text for word in ["dataset", "csv", "anomal", "data analysis"]):
        return "data"
    if any(word in text for word in ["research", "hypothes", "sources", "investigate"]):
        return "research"
    if any(word in text for word in ["build", "calculator", "software", "application"]):
        return "software"
    raise MissionFailure(
        "Cannot identify a supported domain. Choose software, data, or research explicitly."
    )


def robust_flags(values):
    median = statistics.median(values)
    mad = statistics.median(abs(x - median) for x in values)
    if mad == 0:
        return [i for i, x in enumerate(values) if x != median]
    return [i for i, x in enumerate(values) if abs(x - median) / (1.4826 * mad) > 3.5]


def z_flags(values):
    mean, sd = statistics.mean(values), statistics.pstdev(values)
    return [i for i, x in enumerate(values) if sd and abs(x - mean) / sd > 3]


class Engine:
    def __init__(self, store):
        self.store = store
        self.stop = threading.Event()
        self.worker = None
        self.deadlines = {}
        self.step_offsets = {}
        self.artifact_scopes = {}
        from .operations import analytics, workspace, synthesis

        self.adapters = {
            "analytics": lambda mid: analytics(self, mid),
            "workspace": lambda mid: workspace(self, mid),
            "synthesis": lambda mid: synthesis(self, mid),
            "software": self.software,
            "data": self.data,
            "research": self.research,
        }

    def start(self):
        # One worker process only. Recover interrupted missions with an explicit audit event.
        for m in self.store.list():
            if m["state"] == "WAITING_FOR_APPROVAL" and not m.get("compiled_plan"):
                self.store.update(m["id"], state="CREATED", approved=False)
                self.store.event(
                    m["id"],
                    "recovery",
                    "Migrating legacy approval to a schema-validated plan; fresh user approval is required",
                )
                continue
            if m["state"] not in TERMINAL | {"CREATED", "WAITING_FOR_APPROVAL"}:
                self.store.update(
                    m["id"],
                    state="FAILED" if m["attempts"] >= 3 else "CREATED",
                    error="Recovery budget exhausted" if m["attempts"] >= 3 else None,
                )
                self.store.event(
                    m["id"],
                    "recovery",
                    "Worker restarted; mission will re-run from immutable inputs",
                )
        self.worker = threading.Thread(target=self.loop, daemon=True)
        self.worker.start()

    def close(self):
        self.stop.set()
        if self.worker:
            self.worker.join(timeout=30)

    def loop(self):
        while not self.stop.wait(0.15):
            for mission in reversed(self.store.list()):
                if self.stop.is_set():
                    return
                if mission["state"] == "CREATED":
                    self.run(mission["id"])

    def check(self, mid):
        if self.stop.is_set():
            raise MissionFailure(
                "Worker shutdown interrupted this mission; retry after restart"
            )
        if self.store.get(mid)["state"] == "CANCELLED":
            raise Cancelled()
        if time.monotonic() > self.deadlines[mid]:
            raise MissionFailure("Mission deadline exceeded")

    def state(self, mid, state, message):
        with self.store.lock:
            self.check(mid)
            self.store.update(mid, state=state)
            self.store.event(mid, "state", message, {"state": state})

    def step(self, mid, index, status, detail):
        self.check(mid)
        index += self.step_offsets.get(mid, 0)
        plan = self.store.get(mid)["plan"]
        if status == "running" and any(
            plan[d]["status"] != "completed" for d in plan[index]["dependencies"]
        ):
            raise MissionFailure("Plan dependency is not complete")
        plan[index].update(status=status, detail=detail)
        self.store.update(mid, plan=plan)
        self.store.event(
            mid, "task", detail, {"task": plan[index]["id"], "status": status}
        )

    def evidence(self, mid, title, content, locator, **extra):
        return self.store.append(
            mid,
            "evidence",
            {
                "id": uuid4().hex,
                "title": title,
                "content": content,
                "locator": locator,
                "observed_at": now(),
                "sha256": hashlib.sha256(content.encode()).hexdigest(),
                "uncertainty": "Observed output; interpretation is bounded by the supplied input.",
                "relationships": [],
                **extra,
            },
        )

    def decision(
        self, mid, action, alternatives, explanation, evidence, result, uncertainty
    ):
        return self.store.append(
            mid,
            "decisions",
            {
                "id": uuid4().hex,
                "objective": self.store.get(mid)["objective"],
                "selected_action": action,
                "alternatives": alternatives,
                "explanation": explanation,
                "constraints": [
                    "Offline inputs",
                    "Bounded execution",
                    "No causal inference",
                    "No unapproved external effects",
                ],
                "evidence_ids": [e["id"] for e in evidence],
                "execution_result": result,
                "verification_result": "See linked measured evidence",
                "uncertainty": uncertainty,
            },
        )

    def artifact(self, mid, name, content, kind="text"):
        self.check(mid)
        folder = self.store.root / "artifacts" / mid
        folder.mkdir(parents=True, exist_ok=True)
        name = self.artifact_scopes.get(mid, "") + name
        path = folder / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content)
        entry = {
            "name": name,
            "kind": kind,
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        self.store.append(mid, "artifacts", entry)
        return path

    def run(self, mid):
        from .runner import run

        return run(self, mid)

    def sandbox_test(self, mid, folder, filename):
        for attempt in range(2):
            self.check(mid)
            try:
                result = sandbox.run_python(
                    folder,
                    filename,
                    timeout=min(20, max(0.1, self.deadlines[mid] - time.monotonic())),
                    cancelled=lambda: self.stop.is_set()
                    or self.store.get(mid)["state"] == "CANCELLED",
                )
                self.store.event(mid, "tool", f"Sandbox executed {filename}", result)
                return result
            except sandbox.SandboxError:
                if attempt or not sandbox.available():
                    raise
                self.store.event(
                    mid, "retry", "Sandbox infrastructure retry (budget: 1)"
                )

    def skill(self, mid, domain, name, procedure, evaluation, limitations):
        self.check(mid)
        existing = next(
            (
                s
                for s in self.store.skills()
                if s.get("procedure", {}).get("adapter") == procedure.get("adapter")
            ),
            None,
        )
        ev = {"mission_id": mid, "at": now(), **evaluation}
        if existing:
            if existing["procedure"] != procedure:
                existing["version"] += 1
                existing["procedure"] = procedure
                existing["history"].append(
                    {
                        "version": existing["version"],
                        "action": "verified procedure revision",
                        "at": now(),
                        "mission_id": mid,
                    }
                )
            existing["evaluations"].append(ev)
            existing["history"].append(
                {
                    "version": existing["version"],
                    "action": "transfer evaluation",
                    "at": now(),
                    "mission_id": mid,
                }
            )
            skill = existing
            self.store.event(
                mid,
                "skill",
                "Existing strategy applied to a second mission and independently evaluated",
                {"skill_id": skill["id"], "passed": ev["passed"]},
            )
        else:
            skill = {
                "id": uuid4().hex,
                "name": name,
                "domain": domain,
                "version": 1,
                "purpose": name,
                "preconditions": "Supported inputs; bounded local workflow",
                "procedure": procedure,
                "tests": evaluation["tests"],
                "evidence_missions": [mid],
                "evaluations": [ev],
                "limitations": limitations,
                "verified": evaluation["passed"],
                "history": [
                    {
                        "version": 1,
                        "action": "created from measured experiment",
                        "at": now(),
                        "mission_id": mid,
                    }
                ],
            }
        if mid not in skill["evidence_missions"]:
            skill["evidence_missions"].append(mid)
        self.store.save_skill(skill)
        self.store.update(mid, skill_id=skill["id"])
        return skill

    def software(self, mid):
        self.step(
            mid,
            0,
            "running",
            "Writing calculator source and an eight-case arithmetic/safety contract",
        )
        folder = self.store.root / "work" / mid
        folder.mkdir(parents=True, exist_ok=True)
        folder.chmod(0o755)
        # Ancestors must be traversable by the unprivileged container UID.
        for name, text in {
            "calculator.py": templates.BASELINE,
            "test_calculator.py": templates.TESTS,
            "server.py": templates.SERVER,
            "index.html": templates.HTML,
            "test_http.py": templates.HTTP_TEST,
        }.items():
            (folder / name).write_text(text)
            (folder / name).chmod(0o644)
        self.step(
            mid,
            0,
            "completed",
            "Source generated; tests specify arithmetic correctness and rejection of code execution",
        )
        self.state(
            mid,
            "EXPERIMENTING",
            "Comparing a simple summation parser with a restricted AST evaluator",
        )
        self.step(
            mid,
            1,
            "running",
            "Measuring baseline parser against the arithmetic contract",
        )
        baseline = self.sandbox_test(mid, folder, "test_calculator.py")
        try:
            before = json.loads(baseline["output"].strip().splitlines()[-1])
        except (ValueError, IndexError):
            raise MissionFailure("Sandbox did not produce valid test results")
        evidence_before = self.evidence(
            mid,
            "Baseline test execution",
            json.dumps(baseline),
            "sandbox:test_calculator.py:baseline",
        )
        diagnosis = "Summation parser does not implement subtraction, multiplication, division or parentheses. Use a restricted syntax tree evaluator."
        self.store.event(mid, "diagnosis", diagnosis)
        (folder / "calculator.py").write_text(templates.CALCULATOR)
        candidate = self.sandbox_test(mid, folder, "test_calculator.py")
        try:
            after = json.loads(candidate["output"].strip().splitlines()[-1])
        except (ValueError, IndexError):
            raise MissionFailure("Candidate produced no valid test report")
        accepted = (
            candidate["exit_code"] == 0 and after["passed"] == after["total"] == 8
        )
        evidence_after = self.evidence(
            mid,
            "Candidate test execution",
            json.dumps(candidate),
            "sandbox:test_calculator.py:candidate",
            relationships=[{"type": "compares_with", "target": evidence_before["id"]}],
        )
        self.store.append(
            mid,
            "experiments",
            {
                "id": uuid4().hex,
                "hypothesis": "Restricted AST evaluation satisfies the full arithmetic contract",
                "baseline": "Summation parser",
                "candidates": ["Restricted AST parser"],
                "procedure": "Execute identical eight-case contract in two isolated containers",
                "metrics": {
                    "baseline_passed": before["passed"],
                    "candidate_passed": after["passed"],
                    "total": after["total"],
                },
                "results": [before, after],
                "accepted": accepted,
                "acceptance_criteria": "8/8 cases, including unsafe-expression rejection",
                "failure_analysis": diagnosis,
                "verification_status": "passed" if accepted else "failed",
            },
        )
        if not accepted:
            raise MissionFailure("Generated calculator failed its correctness contract")
        self.decision(
            mid,
            "Use the restricted AST evaluator",
            ["Summation parser", "Restricted AST evaluator"],
            diagnosis,
            [evidence_before, evidence_after],
            "8 arithmetic and safety cases passed",
            "Fixed template generation; not general software synthesis.",
        )
        self.step(
            mid,
            1,
            "completed",
            f"Contract improved from {before['passed']}/8 to {after['passed']}/8",
        )
        self.state(
            mid,
            "VERIFYING",
            "Testing the delivered HTTP app independently of parser unit tests",
        )
        self.step(
            mid,
            2,
            "running",
            "Starting the generated HTTP server inside a network-isolated container",
        )
        http = self.sandbox_test(mid, folder, "test_http.py")
        if http["exit_code"] != 0:
            raise MissionFailure("Generated app HTTP smoke test failed")
        self.evidence(
            mid, "HTTP verification", json.dumps(http), "sandbox:test_http.py"
        )
        self.step(
            mid,
            2,
            "completed",
            "Generated HTML served and HTTP calculation returned 20",
        )
        self.step(
            mid,
            3,
            "running",
            "Packaging verified source and recording transferable strategy",
        )
        (folder / "README.md").write_text(
            "Run: python server.py\nOpen http://127.0.0.1:8080 in your own development machine.\nStandard-library only. Supports bounded arithmetic; no eval or shell.\nTests run in PRAXIS Docker sandbox with /work mounted read-only.\n"
        )
        bundle = io.BytesIO()
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in folder.iterdir():
                archive.write(file, file.name)
        self.artifact(mid, "calculator-source.zip", bundle.getvalue(), "archive")
        self.artifact(
            mid,
            "verification.json",
            json.dumps(
                {"baseline": before, "candidate": after, "http": http}, indent=2
            ),
            "json",
        )
        self.skill(
            mid,
            "software",
            "Safe arithmetic web application",
            {
                "adapter": "software",
                "strategy": "restricted_ast",
                "verification": "arithmetic_contract_and_http",
            },
            {
                "passed": accepted and http["exit_code"] == 0,
                "tests": ["8 arithmetic/safety cases", "2 HTTP checks"],
                "score": after["passed"],
            },
            "Calculator apps only; no arbitrary project generation or dependency installation.",
        )
        self.step(
            mid, 3, "completed", "Source archive, test evidence, and skill persisted"
        )
        return {
            "summary": "Generated and verified a functional calculator web application.",
            "verification": "8/8 contract cases; 2 HTTP checks passed",
            "limitations": [
                "Supports calculator objectives only",
                "No external deployment",
                "Fixed strategy adapter, not unrestricted AI coding",
            ],
        }

    def data(self, mid):
        self.step(
            mid,
            0,
            "running",
            "Parsing the supplied CSV and retaining source provenance",
        )
        raw = self.store.get(mid)["csv_data"]
        if not raw:
            raise MissionFailure("Data investigation requires CSV content")
        try:
            reader = csv.DictReader(io.StringIO(raw), strict=True)
            fields = reader.fieldnames
            rows = list(reader)
        except csv.Error:
            raise MissionFailure("Malformed CSV")
        if (
            not fields
            or len(fields) > 40
            or len(set(fields)) != len(fields)
            or any(not f or len(f) > 100 for f in fields)
        ):
            raise MissionFailure(
                "CSV requires 1–40 unique named columns (at most 100 characters per name)"
            )
        if not 5 <= len(rows) <= 10000 or any(
            None in row or any(v is None for v in row.values()) for row in rows
        ):
            raise MissionFailure("CSV requires 5–10,000 rectangular data rows")
        numeric = {}
        for field in fields:
            try:
                values = [float(row[field]) for row in rows]
                if all(math.isfinite(x) and abs(x) < 1e100 for x in values):
                    numeric[field] = values
            except (ValueError, TypeError):
                continue
        if not numeric:
            raise MissionFailure(
                "No complete finite numeric columns found; missing-value imputation is unsupported"
            )
        source = self.evidence(
            mid,
            "Uploaded CSV",
            raw,
            "input:csv",
            uncertainty="User-supplied data; origin and collection quality are not independently validated.",
        )
        self.artifact(mid, "input.csv", raw, "csv")
        self.step(
            mid,
            0,
            "completed",
            f"Imported {len(rows)} rows; {len(numeric)} numeric columns",
        )
        self.step(
            mid,
            1,
            "running",
            "Executing SQL aggregates and calibrating anomaly strategies on labeled fixtures",
        )
        self.state(
            mid,
            "EXPERIMENTING",
            "Comparing mean/stddev and median/MAD under an extreme observation",
        )
        calibration = [10.0, 11.0, 9.0, 10.0, 12.0, 10.0, 11.0, 9.0, 100.0]
        baseline, candidate = z_flags(calibration), robust_flags(calibration)
        expected = {8}
        score = lambda flags: {
            "true_positives": len(set(flags) & expected),
            "false_positives": len(set(flags) - expected),
            "missed": len(expected - set(flags)),
        }
        accepted = set(candidate) == expected
        self.store.append(
            mid,
            "experiments",
            {
                "id": uuid4().hex,
                "hypothesis": "Median/MAD resists contamination that masks an extreme value in small samples",
                "baseline": "Mean/stddev; |z| > 3",
                "candidates": ["Median/MAD; robust z > 3.5"],
                "procedure": "Run both detectors on explicitly synthetic labeled calibration data; not a benchmark of uploaded data",
                "metrics": {"baseline": score(baseline), "candidate": score(candidate)},
                "results": {
                    "calibration_values": calibration,
                    "expected_indices": [8],
                    "baseline_indices": baseline,
                    "candidate_indices": candidate,
                },
                "accepted": accepted,
                "acceptance_criteria": "Detect labeled extreme with zero false positives",
                "failure_analysis": "A single extreme inflates mean/stddev; robust detection can still mislabel multimodal or constant data.",
                "verification_status": "passed" if accepted else "failed",
            },
        )
        if not accepted:
            raise MissionFailure("Detector calibration failed")
        stats = {}
        with sqlite3.connect(":memory:") as db:
            for index, (field, values) in enumerate(numeric.items()):
                self.check(mid)
                table = f"col_{index}"
                db.execute(f"CREATE TABLE {table}(row_number INTEGER, value REAL)")
                db.executemany(
                    f"INSERT INTO {table} VALUES (?, ?)", enumerate(values, 2)
                )
                count, minimum, maximum, mean, total = db.execute(
                    f"SELECT COUNT(*), MIN(value), MAX(value), AVG(value), SUM(value) FROM {table}"
                ).fetchone()
                flags = robust_flags(values)
                stats[field] = {
                    "count": count,
                    "min": minimum,
                    "max": maximum,
                    "mean": mean,
                    "sum": total,
                    "median": statistics.median(values),
                    "mad": statistics.median(
                        abs(v - statistics.median(values)) for v in values
                    ),
                    "anomalies": [
                        {"csv_row": i + 2, "value": values[i]} for i in flags
                    ],
                    "query": f"SELECT COUNT(*), MIN(value), MAX(value), AVG(value), SUM(value) FROM {table}",
                }
        summary = self.evidence(
            mid,
            "Executed statistics and anomaly rows",
            json.dumps(stats),
            "tool:sqlite-and-mad",
            relationships=[{"type": "derived_from", "target": source["id"]}],
        )
        self.decision(
            mid,
            "Apply median/MAD detector",
            ["Mean/stddev", "Median/MAD"],
            "Selected on measured synthetic calibration with explicit labels, then applied to uploaded rows.",
            [source, summary],
            f"Computed statistics on {len(rows)} supplied rows",
            "Anomalies are candidates for inspection, not proven errors. MAD=0 flags all nonmedian values. No causes can be established from univariate data.",
        )
        self.step(
            mid,
            1,
            "completed",
            "SQL aggregates and both calibration strategies executed",
        )
        self.state(
            mid,
            "VERIFYING",
            "Checking SQL aggregates against independent Python calculations and held-out calibration",
        )
        self.step(
            mid,
            2,
            "running",
            "Verifying row counts, aggregate totals, and strategy transfer on held-out data",
        )
        for field, values in numeric.items():
            if (
                stats[field]["count"] != len(values)
                or not math.isclose(
                    stats[field]["mean"],
                    statistics.mean(values),
                    rel_tol=1e-10,
                    abs_tol=1e-10,
                )
                or not math.isclose(
                    stats[field]["sum"], math.fsum(values), rel_tol=1e-10, abs_tol=1e-10
                )
            ):
                raise MissionFailure("Independent aggregate verification failed")
        heldout = [20.0, 21.0, 19.0, 22.0, 20.0, 21.0, 18.0, 20.0, 200.0]
        verified = robust_flags(heldout) == [8]
        if not verified:
            raise MissionFailure("Held-out detector verification failed")
        self.evidence(
            mid,
            "Independent verification",
            json.dumps(
                {
                    "rows_checked": len(rows),
                    "aggregate_match": True,
                    "heldout_fixture": heldout,
                    "heldout_expected": [8],
                    "heldout_actual": robust_flags(heldout),
                }
            ),
            "verification:python-reference",
        )
        self.step(
            mid,
            2,
            "completed",
            "SQL/Python aggregates agree; held-out detector fixture passed",
        )
        self.step(
            mid, 3, "running", "Rendering the report and chart from computed values"
        )
        lines = [
            "# CSV investigation",
            "",
            f"Objective: {self.store.get(mid)['objective']}",
            f"Input SHA-256: {source['sha256']}",
            f"Rows: {len(rows)}",
            "",
            "## Findings",
        ]
        for field, s in stats.items():
            lines += [
                f"- {field}: mean={s['mean']:.6g}, median={s['median']:.6g}, min={s['min']:.6g}, max={s['max']:.6g}; {len(s['anomalies'])} candidate anomalies.",
                f"  CSV row numbers and values: {json.dumps(s['anomalies'])}",
            ]
        lines += [
            "",
            "## Competing explanations",
            "Measurement error, rare valid events, and a mixed population remain plausible. This dataset alone cannot distinguish them. Inspect source records and collection procedures before changing data.",
            "",
            "## Method and limitations",
            "Median absolute deviation, robust z > 3.5. If MAD is zero, all values different from the median are flagged. Synthetic calibration labels are not ground truth for the uploaded dataset. SQL means verified independently in Python. Missing/nonfinite numeric columns are excluded; no imputation. Chart displays the first 200 observations.",
        ]
        self.artifact(mid, "report.md", "\n".join(lines))
        self.artifact(mid, "statistics.json", json.dumps(stats, indent=2), "json")
        self.artifact(
            mid,
            "reproduce.py",
            'import csv, statistics\nwith open("input.csv") as f:\n rows=list(csv.DictReader(f))\nfor key in rows[0]:\n try:\n  v=[float(r[key]) for r in rows]\n  m=statistics.median(v); mad=statistics.median(abs(x-m) for x in v)\n  flags=[i+2 for i,x in enumerate(v) if (x != m if mad == 0 else abs(x-m)/(1.4826*mad)>3.5)]\n  print(key, {"count":len(v),"mean":statistics.mean(v),"median":m,"anomaly_csv_rows":flags})\n except ValueError: pass\n',
        )
        field = next(iter(numeric))
        values = numeric[field][:200]
        low, high = min(values), max(values)
        points = " ".join(
            f"{35 + i * 730 / max(1, len(values) - 1):.2f},{235 - 190 * (v - low) / (high - low or 1):.2f}"
            for i, v in enumerate(values)
        )
        self.artifact(
            mid,
            "chart.svg",
            f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="280" viewBox="0 0 800 280"><title>First numeric column; first 200 rows in source order</title><rect width="800" height="280" fill="#101a1b"/><path d="M35 35V235H765" stroke="#688479" fill="none"/><polyline points="{points}" fill="none" stroke="#c2f28b" stroke-width="2"/><text x="35" y="265" fill="#ddd" font-family="sans-serif">Observations in source order · see statistics.json for units and column</text></svg>',
            "image",
        )
        self.skill(
            mid,
            "data",
            "Robust CSV anomaly investigation",
            {"adapter": "data", "strategy": "median_mad", "threshold": 3.5},
            {
                "passed": verified,
                "tests": [
                    "SQL/Python aggregate comparison on current input",
                    "Held-out detector fixture",
                ],
                "rows_verified": len(rows),
            },
            "Univariate detection, not causal diagnosis; constant/multimodal data requires expert review.",
        )
        self.step(
            mid,
            3,
            "completed",
            "Source CSV, statistics, reproducible procedure, chart and report saved",
        )
        return {
            "summary": f"Investigated {len(rows)} rows across {len(numeric)} numeric columns.",
            "verification": "SQL aggregates independently checked; held-out detector fixture passed",
            "statistics": stats,
            "limitations": [
                "No causal inference",
                "Source authenticity is unverified",
                "Calibration uses synthetic data",
            ],
        }

    def research(self, mid):
        self.step(
            mid,
            0,
            "running",
            "Indexing supplied sources and preserving exact text with provenance",
        )
        m = self.store.get(mid)
        if len(m["sources"]) < 2:
            raise MissionFailure(
                "Research requires at least two supplied sources with title and text"
            )
        terms = set(re.findall(r"[a-z]{4,}", m["objective"].lower())) - {
            "research",
            "investigate",
            "compare",
            "sources",
            "their",
            "this",
            "that",
            "with",
            "from",
            "about",
            "question",
            "what",
            "does",
            "evidence",
        }
        documents = []
        for source in m["sources"]:
            self.check(mid)
            evidence = self.evidence(
                mid,
                source["title"],
                source["text"],
                source.get("url") or "input:document",
                published_at=source.get("published_at"),
                uncertainty="Supplied source; authorship, independence, and factual accuracy are unverified.",
            )
            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+|\n+", source["text"])
                if s.strip()
            ]
            scored = sorted(
                [
                    (
                        len(terms & set(re.findall(r"[a-z]{4,}", sentence.lower()))),
                        sentence,
                    )
                    for sentence in sentences
                ],
                key=lambda item: item[0],
                reverse=True,
            )
            documents.append(
                {
                    "evidence_id": evidence["id"],
                    "title": source["title"],
                    "passages": [
                        {"score": score, "text": sentence}
                        for score, sentence in scored[:3]
                        if score > 0
                    ],
                    "text": source["text"],
                }
            )
        self.step(mid, 0, "completed", f"Indexed {len(documents)} supplied sources")
        self.step(
            mid,
            1,
            "running",
            "Comparing keyword-ranked retrieval against source-order retrieval",
        )
        self.state(
            mid,
            "EXPERIMENTING",
            "Measuring relevant-term coverage; this is a retrieval proxy, not truth",
        )

        def coverage(passages):
            words = set(re.findall(r"[a-z]{4,}", " ".join(passages).lower()))
            return len(terms & words)

        first = [re.split(r"(?<=[.!?])\s+|\n+", d["text"])[0] for d in documents]
        ranked = [p["text"] for d in documents for p in d["passages"][:1]]
        before, after = coverage(first), coverage(ranked)
        self.store.append(
            mid,
            "experiments",
            {
                "id": uuid4().hex,
                "hypothesis": "Keyword ranking improves relevant-term coverage over first-sentence extraction",
                "baseline": "First sentence per source",
                "candidates": ["Keyword overlap ranking"],
                "procedure": "Compare unique objective terms covered at one passage per source",
                "metrics": {"first_sentence_terms": before, "ranked_terms": after},
                "accepted": after >= before and after > 0,
                "acceptance_criteria": "Coverage must be positive and no lower than baseline",
                "failure_analysis": "Lexical coverage can miss synonyms and does not measure factual support.",
                "verification_status": "passed"
                if after >= before and after > 0
                else "rejected",
            },
        )
        selected = ranked if after >= before else first
        selected_strategy = "keyword_ranked" if after >= before else "first_sentence"
        if not selected or max(before, after) == 0:
            raise MissionFailure(
                "Supplied sources contain no lexical evidence for this objective; add relevant documents"
            )
        self.step(
            mid,
            1,
            "completed",
            f"Retrieval measured: {before} baseline terms; {after} ranked terms",
        )
        self.state(
            mid,
            "VERIFYING",
            "Checking selected quotations and contradictory numeric claims",
        )
        self.step(
            mid,
            2,
            "running",
            "Verifying quotations are exact substrings and comparing metric=value claims",
        )
        # Deliberately narrow grammar: the UI explains that arbitrary semantic contradictions are not detected.
        claims = {}
        for d in documents:
            for metric, value, unit in re.findall(
                r"([A-Za-z][A-Za-z _-]{1,40})\s*[:=]\s*(-?\d+(?:\.\d+)?)\s*(%|ms|seconds|kg|USD)?",
                d["text"],
            ):
                key = (metric.strip().lower(), (unit or "").lower())
                claims.setdefault(key, []).append(
                    {
                        "value": float(value),
                        "evidence_id": d["evidence_id"],
                        "title": d["title"],
                    }
                )
        conflicts = [
            {"metric": key[0], "unit": key[1], "claims": values}
            for key, values in claims.items()
            if len({v["value"] for v in values}) > 1
        ]
        for conflict in conflicts:
            ev = self.evidence(
                mid,
                f"Potential contradiction: {conflict['metric']}",
                json.dumps(conflict),
                "tool:numeric-claim-comparison",
                relationships=[
                    {"type": "contradicts", "target": claim["evidence_id"]}
                    for claim in conflict["claims"]
                ],
                uncertainty="Different measurement times, populations, or units may explain the disagreement. Human review is required.",
            )
        quotes_verified = all(any(p in d["text"] for d in documents) for p in selected)
        if not quotes_verified:
            raise MissionFailure("Quote provenance verification failed")
        evidence = self.evidence(
            mid,
            "Retrieval and conflict analysis",
            json.dumps(
                {
                    "documents": [
                        {k: v for k, v in d.items() if k != "text"} for d in documents
                    ],
                    "conflicts": conflicts,
                    "quotations_verified": quotes_verified,
                }
            ),
            "tool:research-analysis",
            relationships=[
                {"type": "derived_from", "target": d["evidence_id"]} for d in documents
            ],
        )
        self.decision(
            mid,
            "Report source-qualified findings with unresolved conflicts",
            ["Treat all sources as agreement", "Compare and retain uncertainty"],
            "Exact quotations are traceable; conflicting numeric claims are retained rather than resolved without evidence.",
            [evidence],
            f"{len(selected)} quotes checked; {len(conflicts)} potential metric conflicts",
            "No live source retrieval, semantic entailment, source independence check, or general truth verification.",
        )
        self.step(
            mid,
            2,
            "completed",
            f"Exact quotations verified; {len(conflicts)} potential contradictions retained",
        )
        self.step(
            mid, 3, "running", "Writing a cited report and reproducible source bundle"
        )
        lines = [
            "# Source-grounded research",
            "",
            f"Question: {m['objective']}",
            "",
            "## Retrieved evidence",
        ]
        for d in documents:
            lines += [f"### {d['title']} [{d['evidence_id'][:8]}]"]
            shown = (
                [p["text"] for p in d["passages"]]
                if selected_strategy == "keyword_ranked"
                else [re.split(r"(?<=[.!?])\s+|\n+", d["text"])[0]]
            )
            lines += ["> " + text for text in shown] or ["No matching passages."]
        lines += [
            "",
            "## Competing hypotheses",
            "- The supplied reports are consistent within different contexts.",
            "- The supplied reports contain unresolved measurement disagreements.",
            f"Observed potential numeric conflicts: {len(conflicts)}. The current corpus cannot establish which source is correct.",
            "",
            "## Potential contradictions",
            json.dumps(conflicts, indent=2),
            "",
            "## Conclusion and limits",
            "The quotations above establish what the supplied documents say. They do not independently establish that the claims are true. Numeric contradictions are detected only for matching metric=value or metric: value statements with identical units. Differences in time or population require review. No causal or general semantic inference was performed.",
        ]
        self.artifact(mid, "research-report.md", "\n".join(lines))
        self.artifact(mid, "sources.json", json.dumps(m["sources"], indent=2), "json")
        self.artifact(
            mid,
            "analysis.json",
            json.dumps(
                {
                    "terms": sorted(terms),
                    "selected_strategy": selected_strategy,
                    "documents": documents,
                    "conflicts": conflicts,
                },
                indent=2,
            ),
            "json",
        )
        self.artifact(
            mid,
            "reproduce.py",
            'import json,re\nsources=json.load(open("sources.json"))\nanalysis=json.load(open("analysis.json"))\nterms=set(analysis["terms"])\nfor source in sources:\n sentences=re.split(r"(?<=[.!?])\\s+|\\n+",source["text"])\n ranked=sorted(sentences,key=lambda s:len(terms & set(re.findall(r"[a-z]{4,}",s.lower()))),reverse=True)\n print(source["title"], ranked[:3])\n',
        )
        self.step(
            mid,
            3,
            "completed",
            "Cited report, exact sources, analysis and reproduction script persisted",
        )
        return {
            "summary": f"Compared {len(documents)} sources and identified {len(conflicts)} potential numeric contradictions.",
            "verification": "Selected quotations match supplied text exactly",
            "conflicts": conflicts,
            "limitations": [
                "Supplied-source research only",
                "Keyword retrieval; no semantic or factual verification",
                "Conclusions remain source-qualified",
            ],
        }
