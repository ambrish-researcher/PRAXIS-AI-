import asyncio
import json
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from .store import Store, TERMINAL
from .engine import Engine, TOOLS
from . import integrations, sandbox


class Source(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=50000)
    url: str | None = Field(default=None, max_length=2000)
    published_at: str | None = Field(default=None, max_length=100)

    @field_validator("url")
    @classmethod
    def valid_url(cls, value):
        if value:
            p = urlparse(value)
            if (
                p.scheme not in {"http", "https"}
                or not p.hostname
                or p.username
                or p.password
            ):
                raise ValueError(
                    "Source URL must be HTTP(S) without credentials; URLs are provenance labels, not fetched"
                )
        return value


class MissionSpec(BaseModel):
    objective: str = Field(min_length=10, max_length=4000)
    domain: Literal["auto", "software", "data", "research"] = "auto"
    csv_data: str = Field(default="", max_length=1_000_000)
    sources: list[Source] = Field(default_factory=list, max_length=20)
    timeout_seconds: int = Field(default=120, ge=1, le=300)


class Proposal(BaseModel):
    objective: str = Field(min_length=10, max_length=4000)
    provider: Literal["nvidia", "nightshift"]


def create_app(root=None, start_worker=True):
    store = Store(root or os.getenv("PRAXIS_DATA_DIR", ".praxis"))
    engine = Engine(store)

    @asynccontextmanager
    async def lifespan(app):
        if start_worker:
            engine.start()
        yield
        engine.close()

    app = FastAPI(title="PRAXIS Mission Engine", version="0.1.0", lifespan=lifespan)
    app.state.store, app.state.engine = store, engine
    origins = ["http://127.0.0.1:5173", "http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.middleware("http")
    async def protect(request: Request, call_next):
        # Local single-user default. Optional bearer authentication for nonlocal deployment.
        # Never expose this development service publicly without an API token and HTTPS.
        token = os.getenv("PRAXIS_API_TOKEN")
        origin = request.headers.get("origin")
        if request.method != "GET" and origin and origin not in origins:
            return JSONResponse({"detail": "Origin denied"}, status_code=403)
        if token and request.url.path != "/api/health" and request.method != "OPTIONS":
            provided = request.headers.get("authorization", "").removeprefix("Bearer ")
            if not secrets.compare_digest(provided, token):
                return JSONResponse(
                    {"detail": "Authentication required"}, status_code=401
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    def get(mid):
        try:
            return store.get(mid)
        except KeyError:
            raise HTTPException(404, "Mission not found") from None

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "storage": "sqlite",
            "worker": bool(engine.worker and engine.worker.is_alive()),
            "sandbox": sandbox.available(),
        }

    @app.get("/api/capabilities")
    def capabilities():
        return {
            "tools": TOOLS,
            "planner": "Deterministic capability adapters; optional inference proposal endpoint",
            "limits": [
                "No arbitrary shell execution",
                "No live web research",
                "Local single-user service; no multi-tenant isolation",
            ],
        }

    @app.get("/api/missions")
    def list_missions():
        return store.list()

    @app.post("/api/missions", status_code=201)
    def create(spec: MissionSpec):
        if sum(len(s.text) for s in spec.sources) > 300000:
            raise HTTPException(422, "Combined sources exceed 300,000 characters")
        if len([m for m in store.list() if m["state"] not in TERMINAL]) >= 20:
            raise HTTPException(429, "At most 20 nonterminal missions are allowed")
        return store.create(spec.model_dump())

    @app.get("/api/missions/{mid}")
    def mission(mid: str):
        return get(mid)

    @app.post("/api/missions/{mid}/approve")
    def approve(mid: str):
        with store.lock:
            m = get(mid)
            if m["state"] != "WAITING_FOR_APPROVAL":
                raise HTTPException(409, "Mission is not waiting for approval")
            store.event(
                mid,
                "approval",
                "User approved generated code execution in network-isolated, resource-limited Docker containers",
            )
            return store.update(mid, approved=True, state="CREATED")

    @app.post("/api/missions/{mid}/cancel")
    def cancel(mid: str):
        with store.lock:
            m = get(mid)
            if m["state"] in TERMINAL:
                raise HTTPException(409, "Mission is already terminal")
            store.event(mid, "cancel", "Cancellation requested by user")
            return store.update(mid, state="CANCELLED")

    @app.post("/api/missions/{mid}/retry")
    def retry(mid: str):
        with store.lock:
            m = get(mid)
            if m["state"] != "FAILED" or m["attempts"] >= 3:
                raise HTTPException(
                    409,
                    "Only failed missions with remaining retry budget may be retried",
                )
            store.event(mid, "retry", "User requested a bounded mission retry")
            return store.update(mid, state="CREATED", error=None)

    @app.get("/api/missions/{mid}/events")
    async def events(
        mid: str, after: int = 0, stream: bool = False, request: Request = None
    ):
        get(mid)
        if not stream:
            return store.events(mid, after)

        async def feed():
            cursor = after
            while True:
                if await request.is_disconnected():
                    return
                rows = store.events(mid, cursor)
                for event in rows:
                    cursor = event["seq"]
                    yield f"id: {cursor}\ndata: {json.dumps(event)}\n\n"
                if store.get(mid)["state"] in TERMINAL and not rows:
                    return
                yield ": keepalive\n\n"
                await asyncio.sleep(0.5)

        return StreamingResponse(
            feed(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/missions/{mid}/artifacts/{name}")
    def artifact(mid: str, name: str):
        m = get(mid)
        if name not in {a["name"] for a in m["artifacts"]} or Path(name).name != name:
            raise HTTPException(404, "Artifact not found")
        file = store.root / "artifacts" / mid / name
        if not file.is_file():
            raise HTTPException(404, "Artifact file unavailable")
        return FileResponse(file, filename=name, media_type="application/octet-stream")

    @app.get("/api/skills")
    def skills():
        return store.skills()

    @app.get("/api/evidence")
    def evidence(q: str = ""):
        return [
            {**e, "mission_id": m["id"]}
            for m in store.list()
            for e in m["evidence"]
            if q.lower() in (e["title"] + " " + e["content"]).lower()
        ]

    @app.get("/api/integrations")
    def integration_status():
        return integrations.status()

    @app.post("/api/integrations/{provider}/health")
    async def integration_health(provider: str):
        if provider not in integrations.PROVIDERS:
            raise HTTPException(
                400, "No verified health interface implemented for this integration"
            )
        return await integrations.health(provider)

    @app.post("/api/proposals")
    async def proposal(spec: Proposal):
        try:
            return {
                "proposal": await integrations.suggest_plan(
                    spec.provider, spec.objective
                ),
                "executed": False,
            }
        except (ValueError, __import__("httpx").HTTPError):
            raise HTTPException(
                502,
                "Inference unavailable; check server-side provider configuration and health",
            ) from None

    return app


app = create_app()
