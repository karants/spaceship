"""
Spaceship — Database Layer

Supports two backends via the same interface:
  - Local SQLite (development) — when TURSO_DATABASE_URL is not set
  - Turso (production)         — cloud-hosted SQLite over HTTP

The models are backend-agnostic.  They call self._db.execute(),
self._db.fetchone(), and self._db.fetchall().

Tables:
    mission_log  — single-row identity/about section
    earth_photos — photography gallery entries
"""

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from urllib.request import Request, urlopen


# ======================================================================
# Backend: Local SQLite (development)
# ======================================================================

class LocalDatabase:
    """SQLite on local disk — used when Turso is not configured."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, sql: str, params: tuple = ()) -> None:
        with self._conn() as conn:
            conn.execute(sql, params)

    def executescript(self, sql: str) -> None:
        with self._conn() as conn:
            conn.executescript(sql)

    def fetchone(self, sql: str, params: tuple = ()) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def insert(self, sql: str, params: tuple = ()) -> int:
        with self._conn() as conn:
            cur = conn.execute(sql, params)
            return cur.lastrowid


# ======================================================================
# Backend: Turso (production — SQLite over HTTP)
# ======================================================================

class TursoDatabase:
    """Turso cloud SQLite accessed via their HTTP pipeline API."""

    def __init__(self, db_url: str, auth_token: str):
        self.api_url = db_url.replace("libsql://", "https://")
        self.auth_token = auth_token

    def _request(self, statements: list[dict]) -> list[dict]:
        """Send a batch of statements to the Turso HTTP API."""
        url = f"{self.api_url}/v2/pipeline"
        body = json.dumps({
            "requests": [
                {"type": "execute", "stmt": s} for s in statements
            ] + [{"type": "close"}]
        }).encode("utf-8")

        req = Request(url, data=body, method="POST")
        req.add_header("Authorization", f"Bearer {self.auth_token}")
        req.add_header("Content-Type", "application/json")

        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        return data.get("results", [])

    def _make_stmt(self, sql: str, params: tuple = ()) -> dict:
        """Build a Turso statement dict with positional args."""
        stmt = {"sql": sql}
        if params:
            args = []
            for p in params:
                if isinstance(p, int):
                    args.append({"type": "integer", "value": str(p)})
                elif isinstance(p, float):
                    args.append({"type": "float", "value": p})
                elif p is None:
                    args.append({"type": "null"})
                else:
                    args.append({"type": "text", "value": str(p)})
            stmt["args"] = args
        return stmt

    def _rows_to_dicts(self, result: dict) -> list[dict]:
        """Convert a Turso result into a list of dicts."""
        resp = result.get("response", {})
        res = resp.get("result", {})
        cols = [c["name"] for c in res.get("cols", [])]
        rows = res.get("rows", [])
        output = []
        for row in rows:
            d = {}
            for i, col in enumerate(cols):
                cell = row[i]
                val = cell.get("value")
                if cell.get("type") == "integer" and val is not None:
                    val = int(val)
                elif cell.get("type") == "float" and val is not None:
                    val = float(val)
                d[col] = val
            output.append(d)
        return output

    def execute(self, sql: str, params: tuple = ()) -> None:
        self._request([self._make_stmt(sql, params)])

    def executescript(self, sql: str) -> None:
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        self._request([self._make_stmt(s) for s in statements])

    def fetchone(self, sql: str, params: tuple = ()) -> dict | None:
        results = self._request([self._make_stmt(sql, params)])
        rows = self._rows_to_dicts(results[0])
        return rows[0] if rows else None

    def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        results = self._request([self._make_stmt(sql, params)])
        return self._rows_to_dicts(results[0])

    def insert(self, sql: str, params: tuple = ()) -> int:
        results = self._request([self._make_stmt(sql, params)])
        resp = results[0].get("response", {})
        res = resp.get("result", {})
        return res.get("last_insert_rowid", 0)


# ======================================================================
# Factory + Schema
# ======================================================================

def create_database(app):
    """Return the correct database backend based on config."""
    turso_url = app.config.get("TURSO_DATABASE_URL", "")
    turso_token = app.config.get("TURSO_AUTH_TOKEN", "")

    if turso_url and turso_token:
        return TursoDatabase(turso_url, turso_token)
    return LocalDatabase(app.config["DATABASE_PATH"])


def init_schema(db) -> None:
    """Create tables if they don't exist."""
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS mission_log (
            id          INTEGER PRIMARY KEY CHECK (id = 1),
            heading     TEXT NOT NULL DEFAULT 'Mission Log',
            body        TEXT NOT NULL DEFAULT 'Transmitting from Earth…',
            photo_ref   TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS earth_photos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            reference   TEXT    NOT NULL,
            caption     TEXT    NOT NULL DEFAULT '',
            sort_order  INTEGER NOT NULL DEFAULT 0,
            created_at  REAL    NOT NULL
        );

        INSERT OR IGNORE INTO mission_log (id) VALUES (1)
        """
    )


# ======================================================================
# Models (backend-agnostic)
# ======================================================================

class MissionLogModel:
    """Single-row model for the identity / about section."""

    def __init__(self, db):
        self._db = db

    def get(self) -> dict:
        return self._db.fetchone("SELECT * FROM mission_log WHERE id = 1") or {}

    def update(self, heading: str, body: str, photo_ref: str | None = None) -> None:
        if photo_ref is not None:
            self._db.execute(
                "UPDATE mission_log SET heading=?, body=?, photo_ref=? WHERE id=1",
                (heading, body, photo_ref),
            )
        else:
            self._db.execute(
                "UPDATE mission_log SET heading=?, body=? WHERE id=1",
                (heading, body),
            )


class EarthPhotoModel:
    """CRUD model for the Our Earth photography gallery."""

    def __init__(self, db):
        self._db = db

    def count(self) -> int:
        row = self._db.fetchone("SELECT COUNT(*) as cnt FROM earth_photos")
        return row["cnt"] if row else 0

    def paginate(self, page: int, per_page: int) -> list[dict]:
        offset = (page - 1) * per_page
        return self._db.fetchall(
            "SELECT * FROM earth_photos ORDER BY sort_order DESC, id DESC "
            "LIMIT ? OFFSET ?",
            (per_page, offset),
        )

    def get_all(self) -> list[dict]:
        return self._db.fetchall(
            "SELECT * FROM earth_photos ORDER BY sort_order DESC, id DESC"
        )

    def get(self, photo_id: int) -> dict | None:
        return self._db.fetchone(
            "SELECT * FROM earth_photos WHERE id=?", (photo_id,)
        )

    def create(self, reference: str, caption: str, sort_order: int = 0) -> int:
        return self._db.insert(
            "INSERT INTO earth_photos (reference, caption, sort_order, created_at) "
            "VALUES (?, ?, ?, ?)",
            (reference, caption, sort_order, time.time()),
        )

    def update(
        self, photo_id: int, caption: str, sort_order: int,
        reference: str | None = None,
    ) -> None:
        if reference:
            self._db.execute(
                "UPDATE earth_photos SET caption=?, sort_order=?, reference=? WHERE id=?",
                (caption, sort_order, reference, photo_id),
            )
        else:
            self._db.execute(
                "UPDATE earth_photos SET caption=?, sort_order=? WHERE id=?",
                (caption, sort_order, photo_id),
            )

    def delete(self, photo_id: int) -> str | None:
        row = self._db.fetchone(
            "SELECT reference FROM earth_photos WHERE id=?", (photo_id,)
        )
        if row:
            self._db.execute("DELETE FROM earth_photos WHERE id=?", (photo_id,))
            return row["reference"]
        return None
