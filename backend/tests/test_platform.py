import json
import os
import threading
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.praxis.api import create_app
from backend.praxis.engine import Engine, MissionFailure, robust_flags
from backend.praxis.store import Store
from backend.praxis import sandbox

CSV = "day,value\na,10\nb,11\nc,9\nd,10\ne,12\nf,10\ng,11\nh,9\ni,100"
SOURCES = [
    {
        "title": "A",
        "text": "Background on batteries. Battery lifetime = 120 hours. Battery lifetime was measured under controlled load.",
    },
    {
        "title": "B",
        "text": "A different source. Battery lifetime = 90 hours. Battery lifetime depends on temperature.",
    },
]


@pytest.fixture
def client(tmp_path):
    # tmp_path is private by default: mount the task directory itself for sandbox access.
    app = create_app(tmp_path)
    with TestClient(app) as client:
        yield client


def wait(
    client, mid, states={"COMPLETED", "FAILED", "WAITING_FOR_APPROVAL"}, timeout=60
):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        m = client.get("/api/missions/" + mid).json()
        if m["state"] in states:
            return m
        time.sleep(0.05)
    pytest.fail("Mission did not reach expected state")


def launch(client, domain, objective, **extra):
    r = client.post(
        "/api/missions", json={"domain": domain, "objective": objective, **extra}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_data_execution_evidence_artifacts_and_skill_transfer(client):
    mid = launch(
        client,
        "data",
        "Analyze dataset anomalies and compare robust strategies",
        csv_data=CSV,
    )
    m = wait(client, mid)
    assert m["state"] == "COMPLETED", m["error"]
    stats = m["result"]["statistics"]["value"]
    assert stats["count"] == 9
    assert stats["sum"] == 182
    assert stats["anomalies"] == [{"csv_row": 10, "value": 100.0}]
    assert m["experiments"][0]["metrics"]["baseline"]["missed"] == 1
    assert m["experiments"][0]["metrics"]["candidate"]["true_positives"] == 1
    assert all(p["status"] == "completed" for p in m["plan"])
    assert m["decisions"][0]["evidence_ids"][0] == next(
        e["id"] for e in m["evidence"] if e["title"] == "Uploaded CSV"
    )
    report = client.get(f"/api/missions/{mid}/artifacts/report.md")
    assert report.status_code == 200 and "Measurement error" in report.text
    assert client.get(f"/api/missions/{mid}/artifacts/secret.env").status_code == 404
    assert client.get("/api/evidence?q=statistics").json()
    second = launch(
        client,
        "data",
        "Analyze a second dataset for anomalies and independently verify transfer",
        csv_data=CSV.replace("100", "150"),
    )
    m2 = wait(client, second)
    assert m2["state"] == "COMPLETED"
    skills = client.get("/api/skills").json()
    assert len(skills) == 1
    assert [ev["mission_id"] for ev in skills[0]["evaluations"]] == [mid, second]
    assert all(ev["passed"] for ev in skills[0]["evaluations"])
    assert m2["skill_id"] == m["skill_id"]
    events = client.get(f"/api/missions/{mid}/events").json()
    assert {"RUNNING", "EXPERIMENTING", "VERIFYING", "COMPLETED"} <= {
        e["data"].get("state") for e in events
    }
    assert (
        len(client.get(f"/api/missions/{mid}/events?after={events[-2]['seq']}").json())
        == 1
    )


def test_research_exact_quotes_and_numeric_conflicts(client):
    mid = launch(
        client,
        "research",
        "Research battery lifetime evidence and compare conflicting sources",
        sources=SOURCES,
    )
    m = wait(client, mid)
    assert m["state"] == "COMPLETED", m["error"]
    assert len(m["result"]["conflicts"]) == 1
    assert {c["value"] for c in m["result"]["conflicts"][0]["claims"]} == {90, 120}
    assert any(
        r["type"] == "contradicts" for e in m["evidence"] for r in e["relationships"]
    )
    assert client.get(f"/api/missions/{mid}/artifacts/sources.json").json() == [
        {**s, "url": None, "published_at": None} for s in SOURCES
    ]
    assert (
        "not independently establish"
        in client.get(f"/api/missions/{mid}/artifacts/research-report.md").text
    )


def test_software_approval_failure_revision_retest_artifact(client):
    if not sandbox.available():
        pytest.skip("Docker sandbox unavailable")
    mid = launch(
        client,
        "software",
        "Build a functional calculator web application and test arithmetic safely",
    )
    m = wait(client, mid)
    assert m["state"] == "WAITING_FOR_APPROVAL"
    assert m["experiments"] == []
    assert client.post(f"/api/missions/{mid}/approve").status_code == 200
    m = wait(client, mid, {"COMPLETED", "FAILED"})
    assert m["state"] == "COMPLETED", m["error"]
    metrics = m["experiments"][0]["metrics"]
    assert metrics["candidate_passed"] == 8 > metrics["baseline_passed"]
    assert "2 HTTP checks" in m["result"]["verification"]
    data = client.get(f"/api/missions/{mid}/artifacts/calculator-source.zip")
    import io, zipfile

    with zipfile.ZipFile(io.BytesIO(data.content)) as z:
        assert {"server.py", "calculator.py", "index.html", "README.md"} <= set(
            z.namelist()
        )
        assert "ast.parse" in z.read("calculator.py").decode()


@pytest.mark.parametrize(
    "csv",
    [
        "x\n1\n2",
        "x,x\n1,2\n2,3\n3,4\n4,5\n5,6",
        "x\nnan\ninf\nfoo\nbar\nbaz",
        "x,y\n1\n2\n3\n4\n5",
    ],
)
def test_invalid_data_fails_explicitly(client, csv):
    mid = launch(
        client, "data", "Analyze this dataset and verify statistics", csv_data=csv
    )
    m = wait(client, mid)
    assert m["state"] == "FAILED" and m["error"]
    assert not m["result"]


def test_unsupported_software_fails_honestly(client):
    mid = launch(
        client, "software", "Build a banking application with payments and deploy it"
    )
    m = wait(client, mid)
    assert m["state"] == "FAILED"
    assert "only" in m["error"]
    assert not m["artifacts"]


def test_cancellation_and_validation(tmp_path):
    app = create_app(tmp_path, start_worker=False)
    with TestClient(app) as client:
        assert (
            client.post("/api/missions", json={"objective": "short"}).status_code == 422
        )
        mid = launch(
            client, "data", "Analyze dataset statistics and anomalies", csv_data=CSV
        )
        assert client.post(f"/api/missions/{mid}/approve").status_code == 409
        assert client.post(f"/api/missions/{mid}/cancel").json()["state"] == "CANCELLED"
        app.state.engine.run(mid)
        assert client.get(f"/api/missions/{mid}").json()["state"] == "CANCELLED"
        assert client.post(f"/api/missions/{mid}/retry").status_code == 409
        assert client.get("/api/missions/missing").status_code == 404


def test_timeout_dependency_gate_and_recovery(tmp_path, monkeypatch):
    store = Store(tmp_path)
    engine = Engine(store)
    m = store.create(
        {
            "domain": "data",
            "objective": "Analyze dataset statistics",
            "timeout_seconds": 1,
            "csv_data": CSV,
            "sources": [],
        }
    )
    original = engine.adapters["data"]

    def slow(mid):
        time.sleep(1.05)
        engine.check(mid)

    engine.adapters["data"] = slow
    engine.run(m["id"])
    assert store.get(m["id"])["state"] == "FAILED"
    assert "deadline" in store.get(m["id"])["error"]
    engine.adapters["data"] = original
    store.update(m["id"], state="RUNNING")
    engine.start()
    deadline = time.monotonic() + 4
    while store.get(m["id"])["state"] != "COMPLETED" and time.monotonic() < deadline:
        time.sleep(0.03)
    engine.close()
    assert store.get(m["id"])["state"] == "COMPLETED"
    assert any(e["kind"] == "recovery" for e in store.events(m["id"]))
    restored = Store(tmp_path)
    assert restored.get(m["id"])["result"]["statistics"]["value"]["sum"] == 182


def test_auth_origin_and_no_secret_echo(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_API_TOKEN", "test-secret-not-for-browser")
    app = create_app(tmp_path, start_worker=False)
    with TestClient(app) as client:
        assert client.get("/api/missions").status_code == 401
        assert (
            client.get(
                "/api/missions",
                headers={"Authorization": "Bearer test-secret-not-for-browser"},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/missions",
                headers={
                    "Origin": "https://evil.example",
                    "Authorization": "Bearer test-secret-not-for-browser",
                },
                json={"objective": "Analyze dataset safely"},
            ).status_code
            == 403
        )
        assert "test-secret-not-for-browser" not in client.get("/api/health").text


def test_integrations_missing_configuration(client, monkeypatch):
    for name in [
        "NVIDIA_API_KEY",
        "NIGHTSHIFT_API_KEY",
        "NIGHTSHIFT_BASE_URL",
        "NIGHTSHIFT_MODEL",
    ]:
        monkeypatch.delenv(name, raising=False)
    assert (
        client.post("/api/integrations/nvidia/health").json()["state"]
        == "not_configured"
    )
    assert (
        client.post("/api/integrations/nightshift/health").json()["state"]
        == "not_configured"
    )
    assert client.post("/api/integrations/zetaris/health").status_code == 400
    assert (
        client.post(
            "/api/proposals",
            json={"provider": "nvidia", "objective": "Analyze dataset statistics"},
        ).status_code
        == 502
    )


def test_sandbox_timeout_and_environment_isolation(tmp_path, monkeypatch):
    if not sandbox.available():
        pytest.skip("Docker sandbox unavailable")
    tmp_path.chmod(0o755)
    file = tmp_path / "check.py"
    file.write_text(
        'import os, socket\nassert "VERY_SECRET_KEY" not in os.environ\nassert os.getuid() == 65534\ntry:\n open("/work/forbidden", "w")\n raise AssertionError("Writable source")\nexcept OSError: pass\nprint("isolation verified")\n'
    )
    file.chmod(0o644)
    monkeypatch.setenv("VERY_SECRET_KEY", "must-not-leak")
    result = sandbox.run_python(tmp_path, "check.py")
    assert result["exit_code"] == 0, result["output"]
    assert "isolation verified" in result["output"]
    file.write_text("while True: pass\n")
    with pytest.raises(sandbox.SandboxError, match="deadline"):
        sandbox.run_python(tmp_path, "check.py", timeout=0.5)
    with pytest.raises(sandbox.SandboxError, match="cancelled"):
        sandbox.run_python(tmp_path, "check.py", cancelled=lambda: True)


def test_retry_budget_and_dependency_enforcement(tmp_path):
    app = create_app(tmp_path, start_worker=False)
    with TestClient(app) as client:
        mid = launch(
            client, "software", "Build a payment service and deploy to production"
        )
        for attempt in range(1, 4):
            app.state.engine.run(mid)
            assert client.get(f"/api/missions/{mid}").json()["attempts"] == attempt
            assert client.post(f"/api/missions/{mid}/retry").status_code == (
                200 if attempt < 3 else 409
            )
        engine = app.state.engine
        engine.deadlines[mid] = time.monotonic() + 5
        app.state.store.update(
            mid,
            state="RUNNING",
            plan=[
                {"id": "a", "status": "pending", "dependencies": []},
                {"id": "b", "status": "pending", "dependencies": [0]},
            ],
        )
        with pytest.raises(MissionFailure, match="dependency"):
            engine.step(mid, 1, "running", "should not run")


def test_failed_skill_transfer_is_retained(client):
    mid = launch(
        client, "data", "Analyze dataset and learn a robust anomaly skill", csv_data=CSV
    )
    assert wait(client, mid)["state"] == "COMPLETED"
    second = launch(
        client,
        "data",
        "Analyze malformed dataset with the existing strategy",
        csv_data="invalid",
    )
    m = wait(client, second)
    assert m["state"] == "FAILED"
    evaluations = client.get("/api/skills").json()[0]["evaluations"]
    assert [ev["passed"] for ev in evaluations] == [True, False]
    assert any(
        e["kind"] == "skill_loaded"
        for e in client.get(f"/api/missions/{second}/events").json()
    )


def test_sse_replays_persisted_events(client):
    mid = launch(
        client, "data", "Analyze this dataset and verify statistics", csv_data=CSV
    )
    assert wait(client, mid)["state"] == "COMPLETED"
    response = client.get(f"/api/missions/{mid}/events?stream=true")
    payloads = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert payloads[-1]["data"]["state"] == "COMPLETED"
    assert [e["seq"] for e in payloads] == sorted({e["seq"] for e in payloads})


def test_provider_health_checks_model_and_sanitizes_errors(monkeypatch):
    from backend.praxis import integrations
    import asyncio, httpx

    monkeypatch.setenv("NVIDIA_API_KEY", "a-secret")

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, headers):
            assert headers["Authorization"] == "Bearer a-secret"
            return httpx.Response(
                200, json={"data": [{"id": "nvidia/nemotron-3.5-lightning-30b-a3b"}]}
            )

    monkeypatch.setattr(integrations.httpx, "AsyncClient", FakeClient)
    assert asyncio.run(integrations.health("nvidia"))["state"] == "ready"

    async def failure(self, url, headers):
        raise httpx.ConnectError("a-secret in unsafe exception")

    FakeClient.get = failure
    result = asyncio.run(integrations.health("nvidia"))
    assert result["state"] == "unavailable" and "a-secret" not in json.dumps(result)
