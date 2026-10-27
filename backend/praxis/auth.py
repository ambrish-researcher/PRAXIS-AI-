"""Small single-user demo gate. Not a multi-tenant identity system."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from fastapi import HTTPException


class DemoAuth:
    def __init__(self):
        self.secret = os.getenv(
            "PRAXIS_SESSION_SECRET", ""
        ).encode() or secrets.token_bytes(32)
        self.lock = threading.Lock()
        self.failures = {}

    @property
    def password(self):
        return os.getenv("PRAXIS_DEMO_PASSWORD", "")

    def valid(self, token):
        try:
            payload, signature = token.split(".")
            expected = hmac.new(
                self.secret, payload.encode(), hashlib.sha256
            ).hexdigest()
            if not secrets.compare_digest(signature, expected):
                return False
            data = json.loads(
                base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
            )
            return data["expires"] > time.time()
        except (ValueError, TypeError, KeyError, UnicodeError):
            return False

    def login(self, password, client):
        if not self.password:
            raise HTTPException(409, "Password login is not configured")
        with self.lock:
            current = time.monotonic()
            attempts = [t for t in self.failures.get(client, []) if current - t < 600]
            if len(attempts) >= 5:
                raise HTTPException(429, "Too many attempts; retry after ten minutes")
            if not secrets.compare_digest(password.encode(), self.password.encode()):
                self.failures[client] = [*attempts, current]
                if len(self.failures) > 1024:
                    self.failures.pop(next(iter(self.failures)))
                raise HTTPException(401, "Incorrect demo password")
            self.failures.pop(client, None)
        payload = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "expires": int(time.time()) + 21600,
                        "nonce": secrets.token_hex(16),
                    }
                ).encode()
            )
            .decode()
            .rstrip("=")
        )
        return (
            payload
            + "."
            + hmac.new(self.secret, payload.encode(), hashlib.sha256).hexdigest()
        )
