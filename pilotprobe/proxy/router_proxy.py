"""
PilotProbe Router Proxy
Transparent ROUTER↔DEALER proxy that sits between PilotOS and the simulator.

ZMQ framing model (from examining zmq_router_server.py):
  - Simulator binds a ROUTER socket, clients connect via DEALER
  - DEALER sends:  [data_frame]
  - ROUTER receives: [peer_identity, data_frame]
  - ROUTER sends:  [peer_identity, data_frame]
  - DEALER receives: [data_frame]

Proxy approach:
  Frontend (ROUTER) ← PilotOS/test_client (DEALER)
  Backend  (DEALER) → Simulator (ROUTER)

  Request flow:
    frontend.recv_multipart()  → [client_id, payload]
    capture(payload)
    backend.send(payload)      → simulator receives [proxy_id, payload]

  Response flow:
    backend.recv()             → [reply]   (DEALER strips routing)
    capture(reply)
    frontend.send_multipart([client_id, reply])  → client receives [reply]
"""
import json
import time
import threading
import logging
import zmq
from typing import Optional, Callable, List

from store.models import CapturedMessage
from config import ProbeConfig

logger = logging.getLogger("pilotprobe.router_proxy")


class RouterProxy:
    """
    Transparent proxy for a single quantum system's Router channel.

    One instance per system type (superconducting, ion_trap, etc.).
    Runs in its own thread via start().
    """

    def __init__(
        self,
        system_type: str,
        listen_port: int,
        target_port: int,
        target_host: str = "localhost",
        on_capture: Optional[Callable[[CapturedMessage], None]] = None,
    ):
        self.system_type = system_type
        self.listen_port = listen_port
        self.target_port = target_port
        self.target_host = target_host
        self.on_capture = on_capture

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._context: Optional[zmq.Context] = None

        # Track the last client identity so we can route async responses
        # (e.g., MsgTaskResult that arrives after MsgTaskAck)
        self._last_client_id: Optional[bytes] = None
        self._client_lock = threading.Lock()

        # Stats
        self.request_count = 0
        self.response_count = 0

    # ── Lifecycle ───────────────────────────────────────────────────

    def start(self):
        """Start the proxy in a background thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._run,
            name=f"router-proxy-{self.system_type}",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """Signal the proxy to stop."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    # ── Core proxy loop ─────────────────────────────────────────────

    def _run(self):
        """Main proxy loop: poll both sockets and forward frames."""
        self._context = zmq.Context()

        # Frontend: ROUTER — PilotOS / test_client connects here
        frontend = self._context.socket(zmq.ROUTER)
        frontend.setsockopt(zmq.RCVHWM, ProbeConfig.ZMQ_HWM)
        frontend.setsockopt(zmq.SNDHWM, ProbeConfig.ZMQ_HWM)
        frontend.setsockopt(zmq.LINGER, ProbeConfig.ZMQ_LINGER_MS)
        frontend.bind(f"tcp://{ProbeConfig.BIND_ADDRESS}:{self.listen_port}")

        # Backend: DEALER — connects to the real simulator's ROUTER
        backend = self._context.socket(zmq.DEALER)
        # Set an explicit UTF-8 identity so the simulator's ROUTER can
        # decode it (zmq_router_server.py:164 does identity.decode('utf-8'))
        dealer_identity = f"pilotprobe-{self.system_type}".encode("utf-8")
        backend.setsockopt(zmq.IDENTITY, dealer_identity)
        backend.setsockopt(zmq.RCVHWM, ProbeConfig.ZMQ_HWM)
        backend.setsockopt(zmq.SNDHWM, ProbeConfig.ZMQ_HWM)
        backend.setsockopt(zmq.LINGER, ProbeConfig.ZMQ_LINGER_MS)
        backend.connect(f"tcp://{self.target_host}:{self.target_port}")

        poller = zmq.Poller()
        poller.register(frontend, zmq.POLLIN)
        poller.register(backend, zmq.POLLIN)

        logger.info(
            f"[{self.system_type}] Router proxy: "
            f":{self.listen_port} → :{self.target_port}"
        )

        try:
            while self._running:
                sockets = dict(poller.poll(ProbeConfig.POLL_TIMEOUT_MS))

                # ── Request: PilotOS → Simulator ────────────────────
                if frontend in sockets:
                    frames = frontend.recv_multipart()
                    if len(frames) >= 2:
                        client_id = frames[0]
                        data_frames = frames[1:]

                        # Remember client identity for async responses
                        with self._client_lock:
                            self._last_client_id = client_id

                        # Capture the data payload
                        self._capture_request(data_frames)

                        # Forward to simulator (just data, no identity)
                        backend.send_multipart(data_frames)
                    else:
                        logger.warning(
                            f"[{self.system_type}] Unexpected frame count "
                            f"from frontend: {len(frames)}"
                        )

                # ── Response: Simulator → PilotOS ───────────────────
                if backend in sockets:
                    frames = backend.recv_multipart()

                    # Capture the reply
                    self._capture_response(frames)

                    # Route back to the client
                    with self._client_lock:
                        cid = self._last_client_id

                    if cid is not None:
                        frontend.send_multipart([cid] + frames)
                    else:
                        logger.warning(
                            f"[{self.system_type}] Response received but "
                            f"no client identity stored — dropping"
                        )
        except zmq.ZMQError as e:
            if self._running:
                logger.error(f"[{self.system_type}] ZMQ error: {e}")
        finally:
            frontend.close()
            backend.close()
            self._context.term()
            logger.info(f"[{self.system_type}] Router proxy stopped")

    # ── Capture helpers ─────────────────────────────────────────────

    def _capture_request(self, data_frames: List[bytes]):
        """Capture an incoming request from PilotOS."""
        self.request_count += 1
        payload = data_frames[0] if data_frames else b""
        msg = CapturedMessage.from_raw(
            system_type=self.system_type,
            direction="REQUEST",
            channel="router",
            raw_bytes=payload,
        )
        if self.on_capture:
            self.on_capture(msg)

    def _capture_response(self, frames: List[bytes]):
        """Capture a response from the simulator."""
        self.response_count += 1
        payload = frames[0] if frames else b""
        msg = CapturedMessage.from_raw(
            system_type=self.system_type,
            direction="RESPONSE",
            channel="router",
            raw_bytes=payload,
        )
        if self.on_capture:
            self.on_capture(msg)
