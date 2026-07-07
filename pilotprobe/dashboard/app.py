"""
PilotProbe Dashboard — FastAPI Application
REST API + WebSocket + Static file serving.
"""
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from store.database import MessageStore
from .websocket_manager import WebSocketManager

logger = logging.getLogger("pilotprobe.dashboard")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

ws_manager = WebSocketManager()


def create_app(store: MessageStore) -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(title="PilotProbe Dashboard", version="1.0.0")

    # ── Static files ────────────────────────────────────────────
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # ── Root → serve index.html ─────────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    async def root():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    # ── WebSocket: live message stream ──────────────────────────
    @app.websocket("/ws/stream")
    async def message_stream(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()  # Keep connection alive
        except WebSocketDisconnect:
            await ws_manager.disconnect(websocket)

    # ── REST API: Messages ──────────────────────────────────────
    @app.get("/api/messages")
    async def get_messages(
        system: Optional[str] = None,
        msg_type: Optional[str] = None,
        task_id: Optional[str] = None,
        direction: Optional[str] = None,
        limit: int = Query(100, le=500),
        offset: int = 0,
    ):
        rows = store.query_messages(
            system_type=system, msg_type=msg_type,
            task_id=task_id, direction=direction,
            limit=limit, offset=offset,
        )
        return {"messages": rows, "count": len(rows)}

    # ── REST API: Stats ─────────────────────────────────────────
    @app.get("/api/stats")
    async def get_stats():
        return store.get_stats()

    # ── REST API: Pipeline Profiler ─────────────────────────────
    @app.get("/api/profiler/pipeline")
    async def get_pipeline_profile():
        return store.get_pipeline_stats()

    # ── REST API: Task Profiler ─────────────────────────────────
    @app.get("/api/profiler/task/{task_id}")
    async def get_task_profile(task_id: str):
        timeline = store.get_task_timeline(task_id)
        if not timeline:
            return {"error": "Task not found", "task_id": task_id}

        events = []
        first_ts = timeline[0]["timestamp"] if timeline else 0
        for row in timeline:
            parsed = {}
            if row.get("parsed_fields"):
                try:
                    parsed = json.loads(row["parsed_fields"])
                except (json.JSONDecodeError, TypeError):
                    pass
            events.append({
                "relative_ms": round((row["timestamp"] - first_ts) * 1000, 1),
                "timestamp": row["timestamp"],
                "direction": row["direction"],
                "msg_type": row["msg_type"],
                "channel": row["channel"],
                "is_valid": row["is_valid"],
                "validation_errors": row.get("validation_errors"),
                "task_status": parsed.get("TaskStatus"),
                "err_code": parsed.get("ErrCode"),
            })

        total_ms = round((timeline[-1]["timestamp"] - first_ts) * 1000, 1) if len(timeline) > 1 else 0
        return {
            "task_id": task_id,
            "system_type": timeline[0]["system_type"],
            "total_duration_ms": total_ms,
            "event_count": len(events),
            "events": events,
        }

    # ── REST API: Recent task IDs ───────────────────────────────
    @app.get("/api/tasks")
    async def get_recent_tasks(limit: int = 20):
        import sqlite3
        conn = sqlite3.connect(store.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT DISTINCT task_id, system_type, MIN(timestamp) as first_seen "
                "FROM messages WHERE task_id IS NOT NULL "
                "GROUP BY task_id ORDER BY first_seen DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return {"tasks": [dict(r) for r in rows]}
        finally:
            conn.close()

    # ── Startup event ───────────────────────────────────────────
    @app.on_event("startup")
    async def startup():
        ws_manager.set_loop(asyncio.get_event_loop())

    return app
