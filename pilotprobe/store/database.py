"""
PilotProbe Message Store
Thread-safe SQLite storage with a background writer thread.
"""
import sqlite3
import threading
import json
import os
from queue import Queue, Empty
from typing import Optional, List, Dict, Any

from .models import CapturedMessage

# ── Schema ──────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       REAL    NOT NULL,
    system_type     TEXT    NOT NULL,
    direction       TEXT    NOT NULL,
    channel         TEXT    NOT NULL,
    msg_type        TEXT,
    task_id         TEXT,
    sn              INTEGER,
    raw_payload     TEXT    NOT NULL,
    parsed_fields   TEXT,
    is_valid        BOOLEAN DEFAULT 1,
    validation_errors TEXT
);
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_task_id   ON messages(task_id);",
    "CREATE INDEX IF NOT EXISTS idx_msg_type  ON messages(msg_type);",
    "CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_system    ON messages(system_type);",
    "CREATE INDEX IF NOT EXISTS idx_direction ON messages(direction);",
]

INSERT_SQL = """
INSERT INTO messages
    (timestamp, system_type, direction, channel, msg_type,
     task_id, sn, raw_payload, parsed_fields, is_valid, validation_errors)
VALUES
    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


class MessageStore:
    """
    Thread-safe message storage backed by SQLite.

    Proxy threads push CapturedMessage objects into an internal queue.
    A dedicated writer thread drains the queue and performs batch inserts.
    """

    def __init__(self, db_path: str = "pilotprobe.db"):
        self.db_path = db_path
        self._queue: Queue = Queue()
        self._running = False
        self._writer_thread: Optional[threading.Thread] = None
        self._total_stored = 0
        self._lock = threading.Lock()

    # ── Lifecycle ───────────────────────────────────────────────────

    def start(self):
        """Initialize the database and start the background writer."""
        self._init_db()
        self._running = True
        self._writer_thread = threading.Thread(
            target=self._writer_loop, name="db-writer", daemon=True
        )
        self._writer_thread.start()

    def stop(self):
        """Flush remaining messages and shut down the writer."""
        self._running = False
        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=5)
        # Final flush
        self._flush_queue()

    # ── Public API ──────────────────────────────────────────────────

    def store(self, msg: CapturedMessage):
        """Enqueue a message for storage (non-blocking, thread-safe)."""
        self._queue.put(msg)

    @property
    def total_stored(self) -> int:
        with self._lock:
            return self._total_stored

    def query_messages(
        self,
        system_type: Optional[str] = None,
        msg_type: Optional[str] = None,
        task_id: Optional[str] = None,
        direction: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query stored messages with optional filters."""
        conditions = []
        params = []

        if system_type:
            conditions.append("system_type = ?")
            params.append(system_type)
        if msg_type:
            conditions.append("msg_type = ?")
            params.append(msg_type)
        if task_id:
            conditions.append("task_id = ?")
            params.append(task_id)
        if direction:
            conditions.append("direction = ?")
            params.append(direction)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT * FROM messages {where}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            total = conn.execute("SELECT COUNT(*) as cnt FROM messages").fetchone()["cnt"]

            by_system = {}
            for row in conn.execute(
                "SELECT system_type, COUNT(*) as cnt FROM messages GROUP BY system_type"
            ).fetchall():
                by_system[row["system_type"]] = row["cnt"]

            by_type = {}
            for row in conn.execute(
                "SELECT msg_type, COUNT(*) as cnt FROM messages "
                "GROUP BY msg_type ORDER BY cnt DESC LIMIT 20"
            ).fetchall():
                by_type[row["msg_type"] or "unknown"] = row["cnt"]

            errors = conn.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE is_valid = 0"
            ).fetchone()["cnt"]

            return {
                "total_messages": total,
                "by_system": by_system,
                "by_type": by_type,
                "validation_errors": errors,
            }
        finally:
            conn.close()

    def get_task_timeline(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a specific task, ordered by time."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM messages WHERE task_id = ? ORDER BY timestamp ASC",
                (task_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    # ── Internal ────────────────────────────────────────────────────

    def _init_db(self):
        """Create tables and indexes if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(CREATE_TABLE_SQL)
            for idx_sql in CREATE_INDEXES_SQL:
                conn.execute(idx_sql)
            conn.commit()
        finally:
            conn.close()

    def _writer_loop(self):
        """Background loop: drain the queue and batch-insert into SQLite."""
        conn = sqlite3.connect(self.db_path)
        batch = []
        batch_size = 50

        try:
            while self._running or not self._queue.empty():
                try:
                    msg = self._queue.get(timeout=0.2)
                    batch.append(self._msg_to_tuple(msg))

                    if len(batch) >= batch_size:
                        self._write_batch(conn, batch)
                        batch.clear()

                except Empty:
                    # Flush any partial batch on timeout
                    if batch:
                        self._write_batch(conn, batch)
                        batch.clear()

            # Final flush
            if batch:
                self._write_batch(conn, batch)
        finally:
            conn.close()

    def _flush_queue(self):
        """Final drain of the queue (called on shutdown)."""
        conn = sqlite3.connect(self.db_path)
        try:
            batch = []
            while not self._queue.empty():
                try:
                    msg = self._queue.get_nowait()
                    batch.append(self._msg_to_tuple(msg))
                except Empty:
                    break
            if batch:
                self._write_batch(conn, batch)
        finally:
            conn.close()

    def _write_batch(self, conn: sqlite3.Connection, batch: list):
        """Write a batch of message tuples to SQLite."""
        conn.executemany(INSERT_SQL, batch)
        conn.commit()
        with self._lock:
            self._total_stored += len(batch)

    @staticmethod
    def _msg_to_tuple(msg: CapturedMessage) -> tuple:
        return (
            msg.timestamp,
            msg.system_type,
            msg.direction,
            msg.channel,
            msg.msg_type,
            msg.task_id,
            msg.sn,
            msg.raw_payload,
            msg.parsed_fields,
            1 if msg.is_valid else 0,
            msg.validation_errors,
        )
