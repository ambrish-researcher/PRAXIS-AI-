"""No host execution fallback. Docker is a trusted administrator prerequisite."""

import os
import subprocess
import time
from uuid import uuid4
from pathlib import Path

IMAGE = os.getenv(
    "PRAXIS_SANDBOX_IMAGE",
    "python:3.12-slim@sha256:12316debbfb86890f6b2d825820612741ba527ad5a44e3902759141d572bfe8f",
)


def docker(*args):
    # Pin the local managed daemon; never inherit an unrelated remote context.
    return ["docker", "--host=unix:///var/run/docker.sock", *args]


def clean_env():
    return {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "DOCKER_HOST",
            "DOCKER_CONTEXT",
            "DOCKER_TLS",
            "DOCKER_TLS_VERIFY",
            "DOCKER_CERT_PATH",
        }
    }


def available():
    try:
        p = subprocess.run(
            docker("image", "inspect", IMAGE, "--format", "{{.Id}}"),
            capture_output=True,
            text=True,
            timeout=8,
            env=clean_env(),
        )
        return p.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


class SandboxError(RuntimeError):
    pass


def run_python(directory, filename, timeout=20, cancelled=lambda: False):
    directory = Path(directory).resolve()
    if "/" in filename or filename.startswith("."):
        raise SandboxError("Invalid executable path")
    if not available():
        raise SandboxError(
            "Local Docker daemon and sandbox image required; host execution is disabled"
        )
    name = "praxis-" + uuid4().hex
    cmd = docker(
        "run",
        "--rm",
        "--name",
        name,
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=32",
        "--memory=128m",
        "--cpus=0.5",
        "--user=65534:65534",
        "--tmpfs=/tmp:rw,noexec,nosuid,size=16m",
        "--mount",
        f"type=bind,src={directory},dst=/work,readonly",
        "--workdir=/work",
        "-e",
        "HTTP_PROXY=",
        "-e",
        "HTTPS_PROXY=",
        "-e",
        "ALL_PROXY=",
        "-e",
        "http_proxy=",
        "-e",
        "https_proxy=",
        "-e",
        "all_proxy=",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        IMAGE,
        "python",
        "-I",
        "-B",
        filename,
    )
    # Only trusted template tests run here; user input is never executed as code.
    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=clean_env()
    )
    started = time.monotonic()
    try:
        while True:
            if cancelled():
                raise SandboxError("Execution cancelled")
            if time.monotonic() - started > timeout:
                raise SandboxError(f"Sandbox deadline exceeded ({timeout}s)")
            try:
                output, _ = p.communicate(timeout=0.1)
                return {
                    "exit_code": p.returncode,
                    "output": output.decode(errors="replace")[:20000],
                    "duration_ms": round((time.monotonic() - started) * 1000),
                    "isolated": True,
                }
            except subprocess.TimeoutExpired:
                continue
    finally:
        subprocess.run(
            docker("rm", "-f", name), capture_output=True, timeout=10, env=clean_env()
        )
        if p.poll() is None:
            p.kill()
        p.communicate()
