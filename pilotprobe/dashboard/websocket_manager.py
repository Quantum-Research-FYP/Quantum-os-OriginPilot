"""
PilotProbe WebSocket Manager
Manages browser connections and broadcasts captured messages in real-time.
"""
import json
import asyncio
import logging
from typing import Set
from fastapi import WebSocket

logger = logging.getLogger("pilotprobe.websocket")


class WebSocketManager:
    """Manages WebSocket connections for live message streaming."""

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.add(ws)
        logger.info(f"WebSocket connected. Total: {len(self._connections)}")

    async def disconnect(self, ws: WebSocket):
        self._connections.discard(ws)
        logger.info(f"WebSocket disconnected. Total: {len(self._connections)}")

    def broadcast_sync(self, data: dict):
        """Thread-safe broadcast — called from proxy threads."""
        if not self._connections or not self._loop:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._broadcast(data), self._loop)
        except Exception:
            pass

    async def _broadcast(self, data: dict):
        dead = set()
        for ws in self._connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self._connections -= dead

    @property
    def connection_count(self) -> int:
        return len(self._connections)
