"""OpenAI-compatible inference; no guessed vendor-specific APIs."""

import os
from urllib.parse import urlparse
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


def settings(provider):
    url_key, default_url, key, model_key, default_model = PROVIDERS[provider]
    return (
        os.getenv(url_key, default_url).rstrip("/"),
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
        configured = bool(url and model and (key or provider == "nightshift"))
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
            "state": "unverified",
            "detail": "No verified interface documentation supplied. No invented API calls are made.",
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
    if not url or not model or (provider == "nvidia" and not key):
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
                headers={"Authorization": f"Bearer {key}"} if key else {},
            )
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
    url, key, model = settings(provider)
    if not url or not model or (provider == "nvidia" and not key):
        raise ValueError("Provider is not configured")
    safe_url(url)
    async with httpx.AsyncClient(timeout=40, follow_redirects=False) as client:
        response = await client.post(
            url + "/chat/completions",
            headers={"Authorization": f"Bearer {key}"} if key else {},
            json={
                "model": model,
                "temperature": 0.2,
                "max_tokens": 600,
                "messages": [
                    {
                        "role": "system",
                        "content": "Give a concise task proposal with constraints and verification criteria. Do not provide chain of thought. No tools are executed by this endpoint.",
                    },
                    {"role": "user", "content": objective},
                ],
            },
        )
    if response.status_code != 200:
        raise ValueError(f"Inference returned HTTP {response.status_code}")
    try:
        return response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError):
        raise ValueError("Invalid inference response") from None
