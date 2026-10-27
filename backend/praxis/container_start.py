"""Initialize an attached state directory, then drop privileges before the API starts."""

import os
from pathlib import Path
import sys

if os.getenv("PRAXIS_REQUIRE_AUTH") == "1" and not (
    os.getenv("PRAXIS_DEMO_PASSWORD") or os.getenv("PRAXIS_API_TOKEN")
):
    raise SystemExit(
        "Hosted demo requires PRAXIS_DEMO_PASSWORD or PRAXIS_API_TOKEN; refusing anonymous deployment"
    )
state = Path(os.getenv("PRAXIS_DATA_DIR", "/var/data/praxis"))
state.mkdir(parents=True, exist_ok=True)
if os.geteuid() == 0:
    os.chown(state, 10001, 10001)
    os.chmod(state, 0o700)
    if state.parent == Path("/var/data"):
        os.chmod(state.parent, state.parent.stat().st_mode | 0o001)
    os.setgroups([])
    os.setgid(10001)
    os.setuid(10001)
os.umask(0o077)
port = int(os.getenv("PORT", "8000"))
if not 1 <= port <= 65535:
    raise SystemExit("Invalid PORT")
os.execvp(
    sys.executable,
    [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.praxis.api:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ],
)
