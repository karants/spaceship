"""
Spaceship — Database Layer

Thin OOP wrapper around sqlite3.  Each model encapsulates queries for
its own table.  The Database singleton manages connection lifecycle.

Tables:
    mission_log  — single-row identity/about section
    earth_photos — photography gallery entries
"""

import os
import sqlite3
import time
from contextlib import contextmanager


class Database:
    """Singleton managing a SQLite database file."""

    _instance = None

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    @classmethod
    def get_instance(cls, db_path: str | None = None) -> "Database":
        if cls._instance is None:
            if db_path is None:
                raise RuntimeError("Database not initialised — provide db_path.")
            cls._instance = cls(db_path)
        return cls._instance

    @contextmanager
    def connect(self):
        """Yield a connection with WAL mode and foreign keys enabled."""
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

    def init_schema(self):
        """Create tables if they don't exist yet."""
        with self.connect() as conn:
            conn.executescript(
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

                INSERT OR IGNORE INTO mission_log (id) VALUES (1);
                """
            )


# ======================================================================
# Models
# ======================================================================

class MissionLogModel:
    """Single-row model for the identity / about section."""

    def __init__(self, db: Database):
        self._db = db

    def get(self) -> dict:
        with self._db.connect() as conn:
            row = conn.execute("SELECT * FROM mission_log WHERE id = 1").fetchone()
            return dict(row) if row else {}

    def update(self, heading: str, body: str, photo_ref: str | None = None) -> None:
        with self._db.connect() as conn:
            if photo_ref is not None:
                conn.execute(
                    "UPDATE mission_log SET heading=?, body=?, photo_ref=? WHERE id=1",
                    (heading, body, photo_ref),
                )
            else:
                conn.execute(
                    "UPDATE mission_log SET heading=?, body=? WHERE id=1",
                    (heading, body),
                )


class EarthPhotoModel:
    """CRUD model for the Our Earth photography gallery."""

    def __init__(self, db: Database):
        self._db = db

    def count(self) -> int:
        with self._db.connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM earth_photos").fetchone()[0]

    def paginate(self, page: int, per_page: int) -> list[dict]:
        offset = (page - 1) * per_page
        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM earth_photos ORDER BY sort_order DESC, id DESC "
                "LIMIT ? OFFSET ?",
                (per_page, offset),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all(self) -> list[dict]:
        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM earth_photos ORDER BY sort_order DESC, id DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get(self, photo_id: int) -> dict | None:
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM earth_photos WHERE id=?", (photo_id,)
            ).fetchone()
            return dict(row) if row else None

    def create(self, reference: str, caption: str, sort_order: int = 0) -> int:
        with self._db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO earth_photos (reference, caption, sort_order, created_at) "
                "VALUES (?, ?, ?, ?)",
                (reference, caption, sort_order, time.time()),
            )
            return cur.lastrowid

    def update(
        self, photo_id: int, caption: str, sort_order: int,
        reference: str | None = None,
    ) -> None:
        with self._db.connect() as conn:
            if reference:
                conn.execute(
                    "UPDATE earth_photos SET caption=?, sort_order=?, reference=? WHERE id=?",
                    (caption, sort_order, reference, photo_id),
                )
            else:
                conn.execute(
                    "UPDATE earth_photos SET caption=?, sort_order=? WHERE id=?",
                    (caption, sort_order, photo_id),
                )

    def delete(self, photo_id: int) -> str | None:
        """Delete row and return the old reference for storage cleanup."""
        with self._db.connect() as conn:
            row = conn.execute(
                "SELECT reference FROM earth_photos WHERE id=?", (photo_id,)
            ).fetchone()
            if row:
                conn.execute("DELETE FROM earth_photos WHERE id=?", (photo_id,))
                return row["reference"]
            return None
