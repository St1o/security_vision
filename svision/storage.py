"""Журнал нарушений в SQLite."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .rules import KIND_LABELS

TS_FORMAT = "%Y-%m-%d %H:%M:%S"

SCHEMA = """
CREATE TABLE IF NOT EXISTS violations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT    NOT NULL,
    day        TEXT    NOT NULL,
    shift      INTEGER NOT NULL,
    camera     TEXT    NOT NULL,
    zone       TEXT    NOT NULL,
    kind       TEXT    NOT NULL,
    track_id   INTEGER,
    duration_s REAL,
    snapshot   TEXT,
    is_demo    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_violations_day ON violations(day, shift);
"""


@dataclass(frozen=True)
class ViolationRecord:
    id: int
    ts: datetime
    shift: int
    camera: str
    zone: str
    kind: str
    track_id: int | None
    duration_s: float | None
    snapshot: str | None
    is_demo: bool

    @property
    def label(self) -> str:
        return KIND_LABELS.get(self.kind, self.kind)


class Storage:
    def __init__(self, db_path: Path, base_dir: Path | None = None):
        self.db_path = Path(db_path)
        self.base_dir = Path(base_dir) if base_dir else self.db_path.parent
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with closing(self._connect()) as conn, conn:
            conn.executescript(SCHEMA)

    def add(self, ts: datetime, shift: int, camera: str, zone: str, kind: str,
            track_id: int | None = None, duration_s: float | None = None,
            snapshot: str | None = None, is_demo: bool = False) -> int:
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO violations (ts, day, shift, camera, zone, kind, track_id, duration_s, snapshot, is_demo) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ts.strftime(TS_FORMAT), ts.strftime("%Y-%m-%d"), shift, camera, zone, kind,
                 track_id, duration_s, snapshot, int(is_demo)),
            )
            return int(cur.lastrowid)

    def set_duration(self, record_id: int, duration_s: float) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("UPDATE violations SET duration_s = ? WHERE id = ?", (duration_s, record_id))

    def get(self, record_id: int) -> ViolationRecord | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM violations WHERE id = ?", (record_id,)).fetchone()
        return self._row(row) if row else None

    def days_with_violations(self, year: int, month: int) -> set[date]:
        prefix = f"{year:04d}-{month:02d}-%"
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT DISTINCT day FROM violations WHERE day LIKE ?", (prefix,)).fetchall()
        return {date.fromisoformat(r["day"]) for r in rows}

    def counts_by_shift(self, day: date) -> dict[int, int]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT shift, COUNT(*) AS n FROM violations WHERE day = ? GROUP BY shift", (day.isoformat(),)
            ).fetchall()
        return {int(r["shift"]): int(r["n"]) for r in rows}

    def list(self, day: date, shift: int) -> list[ViolationRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM violations WHERE day = ? AND shift = ? ORDER BY ts, id", (day.isoformat(), shift)
            ).fetchall()
        return [self._row(r) for r in rows]

    def delete_demo(self) -> int:
        with closing(self._connect()) as conn, conn:
            return conn.execute("DELETE FROM violations WHERE is_demo = 1").rowcount

    def snapshot_path(self, record: ViolationRecord) -> Path | None:
        if not record.snapshot:
            return None
        path = Path(record.snapshot)
        path = path if path.is_absolute() else self.base_dir / path
        return path if path.exists() else None

    @staticmethod
    def _row(row: sqlite3.Row) -> ViolationRecord:
        return ViolationRecord(
            id=row["id"], ts=datetime.strptime(row["ts"], TS_FORMAT), shift=row["shift"],
            camera=row["camera"], zone=row["zone"], kind=row["kind"], track_id=row["track_id"],
            duration_s=row["duration_s"], snapshot=row["snapshot"], is_demo=bool(row["is_demo"]),
        )
