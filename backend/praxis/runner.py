"""Policy-checked mission DAG orchestration around the existing verified adapters."""

import asyncio
import hashlib
import json
import time
from . import planning
from .store import now

LABELS = {
    "software": [
        "Generate source and test contract",
        "Compare parser strategies",
        "Independently verify HTTP app",
        "Package source and record skill",
    ],
    "data": [
        "Import CSV and inspect schema",
        "Query statistics and compare anomaly strategies",
        "Verify rows and calibrated detector",
        "Publish evidence report and skill",
    ],
    "research": [
        "Index supplied documents",
        "Retrieve passages and compare evidence",
        "Check numeric conflicts and source coverage",
        "Publish reproducible research bundle",
    ],
    "analytics": [
        "Validate analytical inputs",
        "Execute analytical query",
        "Independently verify calculations",
        "Publish analytical result",
    ],
    "workspace": [
        "Generate record application",
        "Run baseline validation contract",
        "Improve and independently verify CRUD",
        "Package application and reusable skill",
    ],
    "synthesis": [
        "Collect upstream outputs",
        "Resolve evidence references",
        "Verify artifact integrity",
        "Publish consolidated dossier",
    ],
}


def fingerprint(plan):
    return hashlib.sha256(
        json.dumps(plan.model_dump(), sort_keys=True).encode()
    ).hexdigest()


def invoke_plan(engine, mid, mission):
    return asyncio.run(
        planning.make_plan(
            mission,
            lambda: engine.deadlines[mid] - time.monotonic(),
            lambda: engine.check(mid),
            lambda attempt, message: engine.store.event(
                mid, "inference", message, {"attempt": attempt}
            ),
        )
    )


def run(engine, mid):
    from .engine import MissionFailure, Cancelled

    store = engine.store
    m = store.get(mid)
    engine.deadlines[mid] = time.monotonic() + m["timeout_seconds"]
    engine.step_offsets[mid] = 0
    counted = False
    try:
        engine.state(
            mid,
            "ANALYZING",
            "Understanding objective and checking available input/tool capabilities",
        )
        if m.get("compiled_plan") and m.get("approved"):
            plan = planning.policy(
                planning.MissionPlan.model_validate(m["compiled_plan"]), m
            )
            meta = m["planner"]
            if m.get("approval_plan_hash") != fingerprint(plan):
                raise MissionFailure(
                    "Approval does not match this plan; submit the mission again for review"
                )
        else:
            plan, meta = invoke_plan(engine, mid, m)
        engine.check(mid)
        graph = [{**t.model_dump(), "status": "pending"} for t in plan.ordered()]
        store.update(
            mid, compiled_plan=plan.model_dump(), planner=meta, execution_graph=graph
        )
        store.event(
            mid,
            "plan",
            "Validated executable mission specification",
            {
                "source": meta["source"],
                "task_count": len(graph),
                "plan_hash": fingerprint(plan),
                "detail": meta.get("detail", ""),
            },
        )
        requires_approval = any(t.tool in {"software", "workspace"} for t in plan.tasks)
        if requires_approval and not m["approved"]:
            engine.state(
                mid,
                "WAITING_FOR_APPROVAL",
                "Review the validated plan: generated application tests require network-isolated Docker execution",
            )
            return
        store.update(
            mid,
            attempts=m["attempts"] + 1,
            evidence=[],
            decisions=[],
            experiments=[],
            artifacts=[],
            result=None,
            error=None,
        )
        counted = True
        engine.state(
            mid,
            "PLANNING",
            "Compiling validated task dependencies and independent verification checkpoints",
        )
        build_steps(engine, mid, plan)
        plan_ev = engine.evidence(
            mid,
            "Validated mission plan",
            json.dumps(plan.model_dump()),
            "planner:" + meta["source"],
            uncertainty="AI plans are proposals, not verified results. Every selected tool has a fixed independent verifier.",
        )
        results = {}
        completed = set()
        revision = 0
        while len(completed) < len(plan.tasks):
            ready = next(
                t
                for t in plan.ordered()
                if t.id not in completed and set(t.depends_on) <= completed
            )
            position = next(i for i, t in enumerate(plan.ordered()) if t.id == ready.id)
            engine.step_offsets[mid] = position * 4
            engine.artifact_scopes[mid] = (
                "" if len(plan.tasks) == 1 else ready.id + "--"
            )
            current = store.get(mid)
            graph = current["execution_graph"]
            for item in graph:
                if item["id"] == ready.id:
                    item["status"] = "running"
            store.update(
                mid,
                execution_graph=graph,
                active_task=ready.id,
                active_options=ready.options,
            )
            domain = {
                "software": "software",
                "workspace": "software",
                "research": "research",
            }.get(ready.tool, "data")
            store.update(mid, domain=domain)
            prior = next(
                (
                    s
                    for s in store.skills()
                    if s.get("procedure", {}).get("adapter") == ready.tool
                    and s["verified"]
                ),
                None,
            )
            store.update(mid, skill_id=prior["id"] if prior else None)
            if prior:
                store.event(
                    mid,
                    "skill_loaded",
                    "Loaded verified executable strategy before execution",
                    {"skill_id": prior["id"], "procedure": prior["procedure"]},
                )
            engine.state(mid, "RUNNING", f"Executing {ready.tool}: {ready.purpose}")
            try:
                result = engine.adapters[ready.tool](mid)
                engine.check(mid)
                if (
                    not isinstance(result, dict)
                    or not result.get("verification")
                    or any(
                        p["status"] != "completed"
                        for p in store.get(mid)["plan"][position * 4 : position * 4 + 4]
                    )
                ):
                    raise MissionFailure(
                        "Tool did not satisfy its independent verification checkpoints"
                    )
                results[ready.id] = result
                completed.add(ready.id)
                graph = store.get(mid)["execution_graph"]
                for item in graph:
                    if item["id"] == ready.id:
                        item.update(status="completed", result=result)
                store.update(mid, execution_graph=graph, task_results=results)
                engine.decision(
                    mid,
                    f"Accept verified {ready.tool} output",
                    [t.tool for t in plan.tasks],
                    ready.purpose,
                    [plan_ev],
                    result["verification"],
                    "Independent tool checks establish bounded correctness, not unlimited capability or factual truth.",
                )
            except (MissionFailure, ValueError) as exc:
                engine.check(mid)
                store.event(
                    mid,
                    "diagnosis",
                    str(exc),
                    {"task": ready.id, "replan_budget_remaining": 1 - revision},
                )
                # One model revision after an actual failure, without changing completed work or escalating permission.
                if meta["source"] not in {"nvidia", "nightshift"} or revision:
                    raise
                revised_input = {
                    **m,
                    "planning_mode": meta["source"],
                    "failure_feedback": {
                        "task": ready.model_dump(),
                        "error": str(exc),
                        "completed_task_ids": sorted(completed),
                        "previous_plan": plan.model_dump(),
                    },
                }
                revised, new_meta = invoke_plan(engine, mid, revised_input)
                old = {t.id: t for t in plan.tasks}
                new = {t.id: t for t in revised.tasks}
                if (
                    set(old) != set(new)
                    or any(old[k].tool != new[k].tool for k in old)
                    or any(old[k] != new[k] for k in completed)
                    or old[ready.id].options == new[ready.id].options
                ):
                    raise MissionFailure(
                        "Replan rejected: must preserve completed tasks, tool scope and change failed tool options"
                    )
                plan = revised
                revision += 1
                store.update(
                    mid,
                    compiled_plan=plan.model_dump(),
                    execution_graph=[
                        {
                            **t.model_dump(),
                            "status": "completed" if t.id in completed else "pending",
                            "result": results.get(t.id),
                        }
                        for t in plan.ordered()
                    ],
                )
                build_steps(engine, mid, plan, completed)
                store.event(
                    mid,
                    "replan",
                    "Accepted one bounded execution replan after measured failure",
                    {
                        "revision": revision,
                        "plan_hash": fingerprint(plan),
                        "inference": new_meta,
                    },
                )
        engine.artifact_scopes[mid] = ""
        engine.step_offsets[mid] = 0
        engine.state(
            mid,
            "VERIFYING",
            "Independently checking the complete mission artifact manifest",
        )
        manifest = verify_manifest(store, mid)
        engine.artifact(
            mid, "mission-manifest.json", json.dumps(manifest, indent=2), "json"
        )
        engine.artifact(
            mid,
            "mission-plan.json",
            json.dumps({"plan": plan.model_dump(), "planner": meta}, indent=2),
            "json",
        )
        if len(results) == 1:
            result = next(iter(results.values()))
        else:
            result = {
                "summary": f"Executed and verified {len(results)} dependency-aware tool operations.",
                "verification": "All selected tools completed their independent checks; all artifact hashes verified.",
                "limitations": list(
                    dict.fromkeys(
                        x for r in results.values() for x in r.get("limitations", [])
                    )
                ),
                "tasks": results,
            }
        store.update(mid, result=result, active_task=None, replan_count=revision)
        engine.state(
            mid,
            "COMPLETED",
            "Mission results, evidence and artifact integrity verified",
        )
    except Cancelled:
        store.event(mid, "cancelled", "Worker acknowledged cancellation")
    except Exception as exc:
        message = (
            str(exc)
            if isinstance(exc, (MissionFailure, ValueError))
            else f"Internal {type(exc).__name__}; inspect sanitized server diagnostics"
        )
        if store.get(mid)["state"] != "CANCELLED":
            current = store.get(mid)
            graph = current.get("execution_graph", [])
            for task in graph:
                if task["status"] == "running":
                    task["status"] = "failed"
            store.update(
                mid,
                state="FAILED",
                error=message,
                attempts=m["attempts"] + 1 if not counted else current["attempts"],
                execution_graph=graph,
            )
            store.event(mid, "failure", message)
            if current.get("skill_id"):
                skill = next(
                    (s for s in store.skills() if s["id"] == current["skill_id"]), None
                )
                if skill:
                    skill["evaluations"].append(
                        {
                            "mission_id": mid,
                            "at": now(),
                            "passed": False,
                            "tests": ["Workflow verification"],
                            "failure": message,
                        }
                    )
                    store.save_skill(skill)
    finally:
        engine.deadlines.pop(mid, None)
        engine.step_offsets.pop(mid, None)
        engine.artifact_scopes.pop(mid, None)


def build_steps(engine, mid, plan, completed=None):
    completed = completed or set()
    ordered = plan.ordered()
    ends = {t.id: i * 4 + 3 for i, t in enumerate(ordered)}
    steps = []
    for i, task in enumerate(ordered):
        for j, label in enumerate(LABELS[task.tool]):
            idx = i * 4 + j
            steps.append(
                {
                    "id": f"task-{idx}",
                    "label": label,
                    "tool_task": task.id,
                    "dependencies": [ends[d] for d in task.depends_on]
                    if j == 0
                    else [idx - 1],
                    "status": "completed" if task.id in completed else "pending",
                }
            )
    engine.store.update(mid, plan=steps)


def verify_manifest(store, mid):
    manifest = []
    for a in store.get(mid)["artifacts"]:
        path = store.root / "artifacts" / mid / a["name"]
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != a["sha256"]
        ):
            raise planning.PlanningError("Artifact integrity verification failed")
        manifest.append(a)
    if not manifest:
        raise planning.PlanningError("Tool produced no deliverables")
    return {
        "mission_id": mid,
        "verified_at": now(),
        "artifacts": manifest,
        "verification": "Every artifact hash independently recomputed before completion",
    }
