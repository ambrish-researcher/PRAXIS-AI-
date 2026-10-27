import asyncio
import json
import time
import pytest
from fastapi.testclient import TestClient
from backend.praxis.api import create_app
from backend.praxis.planning import MissionPlan, PlanningError, offline_plan, policy
from backend.praxis import integrations, sandbox

CSV = "region,revenue,orders\nEast,10,1\nWest,20,2\nEast,30,3\nWest,40,4\nEast,50,5\nWest,60,6"


def wait(client, mid, states={"COMPLETED", "FAILED", "WAITING_FOR_APPROVAL"}):
    deadline = time.monotonic() + 70
    while time.monotonic() < deadline:
        m = client.get("/api/missions/" + mid).json()
        if m["state"] in states:
            return m
        time.sleep(0.03)
    pytest.fail("Mission did not finish")


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as c:
        yield c


def create(client, **overrides):
    spec = {
        "objective": "Investigate revenue data and compare verified results",
        "domain": "data",
        "csv_data": CSV,
        "planning_mode": "offline",
        **overrides,
    }
    response = client.post("/api/missions", json=spec)
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.parametrize(
    "options,expected",
    [
        (
            {"operation": "group", "group_by": "region", "value_column": "revenue"},
            {"East": 90.0, "West": 120.0},
        ),
        ({"operation": "correlate", "x_column": "revenue", "y_column": "orders"}, None),
    ],
)
def test_composed_analytics_and_manifest(client, options, expected):
    mid = create(client, analytics_options=options)
    m = wait(client, mid)
    assert m["state"] == "COMPLETED", m["error"]
    assert [t["tool"] for t in m["execution_graph"]] == [
        "data",
        "analytics",
        "synthesis",
    ]
    assert all(t["status"] == "completed" for t in m["execution_graph"])
    result = m["task_results"]["analytics"]["analytics"]
    if expected:
        assert {g["category"]: g["sum"] for g in result["groups"]} == expected
    else:
        assert (
            result["pearson_r"] == pytest.approx(1)
            and not result["causation_established"]
        )
    manifest = client.get(f"/api/missions/{mid}/artifacts/mission-manifest.json").json()
    assert len(manifest["artifacts"]) >= 8
    assert any(a["name"] == "synthesis--dossier.md" for a in m["artifacts"])
    assert len(m["plan"]) == 12 and all(p["status"] == "completed" for p in m["plan"])


@pytest.mark.parametrize("kind", ["tasks", "inventory", "contacts"])
def test_generated_record_app_improvement_and_verification(client, kind):
    if not sandbox.available():
        pytest.skip("Sandbox not available")
    mid = create(
        client,
        domain="software",
        objective=f"Build a {kind} record management application with persistent records",
        csv_data="",
        workspace_options={"kind": kind, "title": f"{kind.title()} Studio"},
    )
    m = wait(client, mid)
    assert m["state"] == "WAITING_FOR_APPROVAL"
    assert m["compiled_plan"]["tasks"][0]["tool"] == "workspace"
    assert client.post(f"/api/missions/{mid}/approve").status_code == 200
    m = wait(client, mid, {"COMPLETED", "FAILED"})
    assert m["state"] == "COMPLETED", m["error"]
    metrics = m["experiments"][0]["metrics"]
    assert metrics["candidate_passed"] == 7 > metrics["baseline_passed"]
    assert "persistence" in m["result"]["verification"]
    assert (
        client.get(f"/api/missions/{mid}/artifacts/workspace-source.zip").status_code
        == 200
    )


def plan(tasks):
    return {
        "objective_summary": "Analyze supplied revenue data using only supported operations",
        "success_criteria": ["Verify all calculations independently"],
        "constraints": ["No arbitrary commands"],
        "tasks": tasks,
    }


def task(id="analyze", tool="data", **kwargs):
    return {
        "id": id,
        "tool": tool,
        "purpose": "Analyze actual supplied rows",
        "depends_on": [],
        "options": {},
        **kwargs,
    }


@pytest.mark.parametrize(
    "tasks",
    [
        [task(tool="shell")],
        [task(options={"command": "curl https://evil.example"})],
        [task(depends_on=["missing"])],
        [
            task(id="a", depends_on=["b"]),
            task(id="b", tool="research", depends_on=["a"]),
        ],
        [task(id="a"), task(id="a", tool="research")],
        [task(id="a"), task(id="b")],
    ],
)
def test_plan_rejects_unknown_tools_commands_cycles_and_duplicates(tasks):
    with pytest.raises(ValueError):
        MissionPlan.model_validate(plan(tasks))


def test_nvidia_plan_repair_then_actual_tool_execution(client, monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-only-key")
    calls = []

    async def completion(provider, system, content, **kwargs):
        calls.append(json.loads(content))
        # Invalid plan first, valid plan second. These are explicit test doubles, not live inference.
        raw = plan([task(tool="shell")]) if len(calls) == 1 else plan([task()])
        return json.dumps(raw), {
            "model": "test-nemotron",
            "latency_ms": 1,
            "usage": {"total_tokens": 1},
        }

    monkeypatch.setattr(integrations, "complete", completion)
    mid = create(client, planning_mode="nvidia", domain="auto")
    m = wait(client, mid)
    assert m["state"] == "COMPLETED", m["error"]
    assert m["planner"]["source"] == "nvidia" and m["planner"]["attempts"] == 2
    assert calls[1]["previous_validation_errors"]
    assert "East,10" not in json.dumps(calls)
    assert m["result"]["statistics"]["revenue"]["sum"] == 210


def test_explicit_missing_provider_no_fake_execution(client, monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    mid = create(client, planning_mode="nvidia")
    m = wait(client, mid)
    assert m["state"] == "FAILED" and "NVIDIA_API_KEY" in m["error"]
    assert not m["artifacts"] and not m["experiments"]


def test_auto_provider_failure_falls_back_honestly(client, monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-only")

    async def fail(*args, **kwargs):
        raise integrations.InferenceError("nvidia inference returned HTTP 403")

    monkeypatch.setattr(integrations, "complete", fail)
    mid = create(client, planning_mode="auto")
    m = wait(client, mid)
    assert m["state"] == "COMPLETED" and m["planner"]["source"] == "offline"
    assert "403" in m["planner"]["detail"] and m["planner"]["fallback"]


def test_actual_execution_failure_triggers_one_scope_preserving_replan(
    client, monkeypatch
):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-only")
    calls = []

    async def completion(provider, system, content, **kwargs):
        payload = json.loads(content)
        calls.append(payload)
        opts = (
            {"operation": "correlate", "x_column": "constant", "y_column": "revenue"}
            if len(calls) == 1
            else {"operation": "group", "group_by": "region", "value_column": "revenue"}
        )
        return json.dumps(
            plan([task(id="analysis", tool="analytics", options=opts)])
        ), {"model": "test-nemotron", "latency_ms": 1}

    monkeypatch.setattr(integrations, "complete", completion)
    csv = (
        "region,revenue,constant\nEast,10,1\nWest,20,1\nEast,30,1\nWest,40,1\nEast,50,1"
    )
    mid = create(client, planning_mode="nvidia", csv_data=csv)
    m = wait(client, mid)
    assert m["state"] == "COMPLETED", m["error"]
    assert m["replan_count"] == 1
    assert calls[1]["failure_feedback"]["task"]["id"] == "analysis"
    assert m["result"]["analytics"]["operation"] == "group"
    assert any(
        e["kind"] == "diagnosis" and "constant" in e["message"]
        for e in client.get(f"/api/missions/{mid}/events").json()
    )


def test_plan_approval_is_bound_to_specification(client):
    mid = create(
        client,
        domain="software",
        objective="Build a calculator app and verify arithmetic",
        csv_data="",
    )
    m = wait(client, mid)
    assert m["state"] == "WAITING_FOR_APPROVAL"
    app = client.app
    changed = m["compiled_plan"]
    changed["tasks"][0]["purpose"] = "Changed after approval"
    client.post(f"/api/missions/{mid}/approve")
    app.state.store.update(mid, compiled_plan=changed)
    m = wait(client, mid, {"FAILED", "COMPLETED"})
    assert m["state"] == "FAILED" and "Approval does not match" in m["error"]


@pytest.mark.parametrize(
    "url,expected",
    [
        ("127.0.0.1:8088", "http://127.0.0.1:8088/v1"),
        ("http://localhost:8088/v1/chat/completions", "http://localhost:8088/v1"),
        ("https://runtime.example/v1/models", "https://runtime.example/v1"),
        ("https://runtime.example/healthz", "https://runtime.example/v1"),
    ],
)
def test_meterless_documented_url_normalization(url, expected):
    assert integrations.normalize_meterless(url) == expected


def test_meterless_documented_headers_and_auth(monkeypatch):
    import httpx

    monkeypatch.setenv(
        "NIGHTSHIFT_BASE_URL", "https://runtime.example/v1/chat/completions"
    )
    monkeypatch.setenv("NIGHTSHIFT_MODEL", "meterless/auto")
    monkeypatch.setenv("NIGHTSHIFT_API_KEY", "rt-local")
    assert not integrations.configured("nightshift")
    monkeypatch.setenv("NIGHTSHIFT_API_KEY", "test-real-token")
    calls = []

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, headers):
            calls.append((url, headers))
            return httpx.Response(401)

        async def post(self, url, headers, json):
            calls.append((url, headers))
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": '{"ok":true}'}}],
                    "usage": {"total_tokens": 4},
                },
            )

    monkeypatch.setattr(integrations.httpx, "AsyncClient", Client)
    assert asyncio.run(integrations.health("nightshift"))["state"] == "unauthorized"
    text, meta = asyncio.run(integrations.complete("nightshift", "system", "hello"))
    assert text == '{"ok":true}'
    assert calls[0][0] == "https://runtime.example/v1/models"
    assert calls[1][0] == "https://runtime.example/v1/chat/completions"
    assert all(headers["meterless-app"] == "praxis" for _, headers in calls)
    assert calls[1][1]["meterless-scope"] == "user"
