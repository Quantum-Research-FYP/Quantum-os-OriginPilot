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

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """
        Analyze tasks to compute pipeline performance and latency bottlenecks.
        
        Calculates:
          - Total tasks processed
          - Success and failure counts
          - Phase durations: Pending time, Compile time, Execution time, Turnaround time
          - SLA violations
          - Latency bottleneck recommendation
        """
        import json

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            # Query all messages with a task_id ordered by task_id and timestamp
            # This allows us to reconstruct the lifecycle of each task
            rows = conn.execute(
                "SELECT task_id, system_type, msg_type, direction, timestamp, parsed_fields "
                "FROM messages WHERE task_id IS NOT NULL AND task_id != '' "
                "ORDER BY task_id, timestamp ASC"
            ).fetchall()

            # Group rows by task_id
            tasks = {}
            for row in rows:
                tid = row["task_id"]
                if tid not in tasks:
                    tasks[tid] = {
                        "system_type": row["system_type"],
                        "events": [],
                    }
                tasks[tid]["events"].append(row)

            pending_times = []
            compile_times = []
            execution_times = []
            turnaround_times = []

            successful_tasks = 0
            failed_tasks = 0
            running_tasks = 0

            compile_sla_violations = 0
            pending_sla_violations = 0

            COMPILE_SLA_MS = 5000.0  # 5 seconds
            PENDING_SLA_MS = 2000.0  # 2 seconds

            for tid, tdata in tasks.items():
                t_submit = None
                t_compiling = None
                t_compiled = None
                t_running = None
                t_end = None
                is_success = False
                is_failed = False

                # Scan events
                for ev in tdata["events"]:
                    mtype = ev["msg_type"]
                    direction = ev["direction"]
                    ts = ev["timestamp"]

                    parsed = {}
                    if ev["parsed_fields"]:
                        try:
                            parsed = json.loads(ev["parsed_fields"])
                        except Exception:
                            pass

                    tstatus = parsed.get("TaskStatus")
                    err_code = parsed.get("ErrCode")

                    # 1. Submission
                    if mtype == "MsgTask" and direction == "REQUEST":
                        if t_submit is None:
                            t_submit = ts

                    # 2. Status Transitions
                    if tstatus == 1:  # PENDING
                        if t_submit is None:
                            t_submit = ts
                    elif tstatus == 7:  # COMPILING
                        if t_compiling is None:
                            t_compiling = ts
                    elif tstatus == 8:  # COMPILED
                        if t_compiled is None:
                            t_compiled = ts
                    elif tstatus == 2:  # RUNNING
                        if t_running is None:
                            t_running = ts
                    elif tstatus == 5:  # SUCCESSED
                        t_end = ts
                        is_success = True
                    elif tstatus == 4:  # FAILED
                        t_end = ts
                        is_failed = True

                    # Also check message types directly as fallback
                    if mtype == "MsgTaskResult":
                        t_end = ts
                        if err_code == 0:
                            is_success = True
                        else:
                            is_failed = True
                    elif mtype == "MsgTaskAck" and direction == "RESPONSE":
                        if err_code is not None and err_code != 0:
                            t_end = ts
                            is_failed = True

                # Fallback: if we don't have t_submit, use the first event's timestamp
                if t_submit is None and tdata["events"]:
                    t_submit = tdata["events"][0]["timestamp"]

                # If the task completed (or failed)
                if t_submit is not None:
                    if is_success:
                        successful_tasks += 1
                    elif is_failed:
                        failed_tasks += 1
                    else:
                        running_tasks += 1

                    if t_end is not None:
                        # Turnaround time
                        turnaround_ms = (t_end - t_submit) * 1000.0
                        turnaround_times.append(turnaround_ms)

                        # Pending duration: time from submission to compile or run
                        t_next = t_compiling or t_running or t_end
                        if t_next > t_submit:
                            pending_ms = (t_next - t_submit) * 1000.0
                            pending_times.append(pending_ms)
                            if pending_ms > PENDING_SLA_MS:
                                pending_sla_violations += 1

                        # Compile duration: time from compiling to compiled (or run if it goes straight to running)
                        if t_compiling is not None:
                            t_comp_end = t_compiled or t_running or t_end
                            if t_comp_end > t_compiling:
                                compile_ms = (t_comp_end - t_compiling) * 1000.0
                                compile_times.append(compile_ms)
                                if compile_ms > COMPILE_SLA_MS:
                                    compile_sla_violations += 1

                        # Execution duration: time from running to completion
                        if t_running is not None and t_end > t_running:
                            exec_ms = (t_end - t_running) * 1000.0
                            execution_times.append(exec_ms)

            # Calculate averages
            avg_pending = sum(pending_times) / len(pending_times) if pending_times else 0.0
            avg_compile = sum(compile_times) / len(compile_times) if compile_times else 0.0
            avg_execution = sum(execution_times) / len(execution_times) if execution_times else 0.0
            avg_turnaround = sum(turnaround_times) / len(turnaround_times) if turnaround_times else 0.0

            # Determine bottleneck recommendation
            bottleneck = "None"
            max_val = 0.0
            if len(turnaround_times) > 0:
                if avg_compile > max_val:
                    max_val = avg_compile
                    bottleneck = "COMPILATION (Optimize pulse compiler parameters)"
                if avg_pending > max_val:
                    max_val = avg_pending
                    bottleneck = "SCHEDULING / QUEUE DEPTH (Increase QPU slot capacity)"
                if avg_execution > max_val:
                    max_val = avg_execution
                    bottleneck = "QPU EXECUTION / SIMULATOR (Reduce simulator network overhead)"

            return {
                "total_tasks": len(tasks),
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "running_tasks": running_tasks,
                "avg_pending_ms": round(avg_pending, 1),
                "avg_compile_ms": round(avg_compile, 1),
                "avg_execution_ms": round(avg_execution, 1),
                "avg_turnaround_ms": round(avg_turnaround, 1),
                "pending_sla_violations": pending_sla_violations,
                "compile_sla_violations": compile_sla_violations,
                "bottleneck_recommendation": bottleneck,
            }
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
