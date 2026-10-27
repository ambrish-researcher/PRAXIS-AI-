"""Small transactional store. The event stream is the durable audit trail."""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.db() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS missions(id TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, mission TEXT, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS skills(id TEXT PRIMARY KEY, body TEXT NOT NULL);
            """)

    def db(self):
        return sqlite3.connect(self.root / "praxis.sqlite", timeout=20)

    def create(self, spec):
        mid = uuid4().hex
        body = {
            **spec,
            "id": mid,
            "state": "CREATED",
            "created_at": now(),
            "updated_at": now(),
            "plan": [],
            "evidence": [],
            "decisions": [],
            "experiments": [],
            "artifacts": [],
            "result": None,
            "error": None,
            "approved": False,
            "attempts": 0,
            "skill_id": None,
        }
        with self.db() as db:
            db.execute("INSERT INTO missions VALUES (?,?)", (mid, json.dumps(body)))
        self.event(mid, "state", "Mission accepted", {"state": "CREATED"})
        return self.get(mid)

    def get(self, mid):
        with self.db() as db:
            row = db.execute("SELECT body FROM missions WHERE id=?", (mid,)).fetchone()
        if not row:
            raise KeyError(mid)
        return json.loads(row[0])

    def list(self):
        with self.db() as db:
            rows = db.execute(
                "SELECT body FROM missions ORDER BY rowid DESC"
            ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def update(self, mid, **changes):
        with self.lock, self.db() as db:
            row = db.execute("SELECT body FROM missions WHERE id=?", (mid,)).fetchone()
            if not row:
                raise KeyError(mid)
            body = json.loads(row[0])
            if body["state"] == "CANCELLED" and changes.get("state") != "CANCELLED":
                return body
            body.update(changes, updated_at=now())
            db.execute("UPDATE missions SET body=? WHERE id=?", (json.dumps(body), mid))
        return body

    def append(self, mid, field, item):
        with self.lock:
            items = self.get(mid)[field]
            self.update(mid, **{field: [*items, item]})
        return item

    def event(self, mid, kind, message, data=None):
        event = {"at": now(), "kind": kind, "message": message, "data": data or {}}
        with self.db() as db:
            cur = db.execute(
                "INSERT INTO events(mission,body) VALUES (?,?)",
                (mid, json.dumps(event)),
            )
            event["seq"] = cur.lastrowid
        return event

    def events(self, mid, after=0):
        with self.db() as db:
            rows = db.execute(
                "SELECT seq,body FROM events WHERE mission=? AND seq>? ORDER BY seq",
                (mid, after),
            ).fetchall()
        return [{**json.loads(body), "seq": seq} for seq, body in rows]

    def skills(self):
        with self.db() as db:
            return [json.loads(r[0]) for r in db.execute("SELECT body FROM skills")]

    def save_skill(self, body):
        with self.lock, self.db() as db:
            db.execute(
                "INSERT OR REPLACE INTO skills VALUES (?,?)",
                (body["id"], json.dumps(body)),
            )
