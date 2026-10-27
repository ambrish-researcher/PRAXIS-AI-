"""OpenAI-compatible inference; no guessed vendor-specific APIs."""

import os
import time
from urllib.parse import urlparse, urlunparse
import httpx

PROVIDERS = {
    "nvidia": (
        "NVIDIA_BASE_URL",
        "https://integrate.api.nvidia.com/v1",
        "NVIDIA_API_KEY",
        "NVIDIA_MODEL",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
    ),
    "nightshift": (
        "NIGHTSHIFT_BASE_URL",
        "",
        "NIGHTSHIFT_API_KEY",
        "NIGHTSHIFT_MODEL",
        "",
    ),
}


def normalize_meterless(value):
    if "://" not in value:
        value = "http://" + value
    parsed = urlparse(value)
    path = parsed.path.rstrip("/")
    for suffix in ("/chat/completions", "/models", "/healthz"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    if path.endswith("/v1"):
        path = path[:-3]
    return urlunparse(parsed._replace(path=path + "/v1"))


def provider_headers(provider, key, chat=False):
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    if provider == "nightshift":
        headers["meterless-app"] = "praxis"
        if chat:
            headers["meterless-scope"] = "user"
    return headers


def settings(provider):
    url_key, default_url, key, model_key, default_model = PROVIDERS[provider]
    base = os.getenv(url_key, default_url).rstrip("/")
    if provider == "nightshift" and base:
        base = normalize_meterless(base)
    return (
        base,
        os.getenv(key),
        os.getenv(model_key, default_model),
    )


def safe_url(url):
    p = urlparse(url)
    if (
        p.username
        or p.password
        or p.query
        or p.fragment
        or p.scheme not in {"http", "https"}
    ):
        raise ValueError(
            "Configure an HTTP(S) base URL without embedded credentials, query, or fragment"
        )
    if p.scheme == "http" and p.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Remote integrations require HTTPS")
    return url


def status():
    items = []
    for provider in PROVIDERS:
        url, key, model = settings(provider)
        configured = bool(
            url
            and model
            and key
            and not (provider == "nightshift" and key == "rt-local")
        )
        items.append(
            {
                "id": provider,
                "state": "configured" if configured else "not_configured",
                "model": model,
                "detail": "Health check required"
                if configured
                else "Set server-side URL, model and API key as required. Cloud localhost is not your Windows host.",
            }
        )
    items += [
        {
            "id": "meterless_agent_engine",
            "state": "documented",
            "detail": "Official Meterless repository reviewed: open engines are local implementation specs, not a hosted Agent Engine API. Nightshift uses its documented authenticated OpenAI-compatible runtime contract. No engine conformance or live runtime claim.",
        },
        {
            "id": "zetaris",
            "state": "not_configured",
            "detail": "Supported SQL access is available through exported CSV. A live connector requires installation-specific JDBC/REST documentation and reachable credentials; not implemented.",
        },
    ]
    return items


async def health(provider):
    url, key, model = settings(provider)
    if (
        not url
        or not model
        or (not key or (provider == "nightshift" and key == "rt-local"))
    ):
        return {
            "state": "not_configured",
            "detail": "Missing server-side configuration",
        }
    try:
        safe_url(url)
        async with httpx.AsyncClient(
            timeout=15, follow_redirects=False, trust_env=True
        ) as client:
            response = await client.get(
                url + "/models",
                headers=provider_headers(provider, key),
            )
        if response.status_code in {401, 403}:
            return {
                "state": "unauthorized",
                "detail": f"Model discovery returned HTTP {response.status_code}; configure an authorized runtime token",
            }
        if response.status_code != 200:
            return {
                "state": "unavailable",
                "detail": f"Model discovery returned HTTP {response.status_code}",
            }
        models = {m["id"] for m in response.json().get("data", [])}
        return {
            "state": "ready" if model in models else "model_unverified",
            "detail": "Configured model is listed"
            if model in models
            else "Configured model was not listed",
        }
    except (httpx.HTTPError, ValueError, KeyError):
        return {
            "state": "unavailable",
            "detail": "Connection, TLS, or model discovery failed. Check server configuration; credentials are never returned.",
        }


async def suggest_plan(provider, objective):
    text, _ = await complete(
        provider,
        "Give a concise task proposal with constraints and verification criteria. Do not provide chain of thought. No tools are executed by this endpoint.",
        objective,
    )
    return text


class InferenceError(ValueError):
    """Deliberately sanitized; response bodies and credentials never enter audit logs."""


def configured(provider):
    url, key, model = settings(provider)
    return bool(
        url and model and key and not (provider == "nightshift" and key == "rt-local")
    )


async def complete(provider, system, content, max_tokens=1200, timeout=40):
    url, key, model = settings(provider)
    if not configured(provider):
        missing = (
            "NVIDIA_API_KEY"
            if provider == "nvidia"
            else "NIGHTSHIFT_BASE_URL, NIGHTSHIFT_MODEL and NIGHTSHIFT_API_KEY (real runtime token)"
        )
        raise InferenceError(
            f"{provider} inference is not configured: set {missing} securely in server environment settings"
        )
    try:
        safe_url(url)
        started = time.monotonic()
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=False, trust_env=True
        ) as client:
            response = await client.post(
                url + "/chat/completions",
                headers=provider_headers(provider, key, chat=True),
                json={
                    "model": model,
                    "temperature": 0.15,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": content},
                    ],
                },
            )
        if response.status_code != 200:
            raise InferenceError(
                f"{provider} inference returned HTTP {response.status_code}; check endpoint policy, model access and credential authorization"
            )
        body = response.json()
        text = body["choices"][0]["message"]["content"]
        if not isinstance(text, str) or not text.strip() or len(text) > 30000:
            raise InferenceError(
                f"{provider} inference returned an empty or oversized response"
            )
        usage = body.get("usage", {})
        return text, {
            "model": model,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "usage": {
                k: v
                for k, v in usage.items()
                if k in {"prompt_tokens", "completion_tokens", "total_tokens"}
                and isinstance(v, int)
            },
        }
    except InferenceError:
        raise
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        raise InferenceError(
            f"{provider} inference failed: connection, TLS, timeout or invalid response; no tool was executed by the provider"
        ) from None
