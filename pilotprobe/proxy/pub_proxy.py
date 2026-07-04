"""
PilotProbe Pub-Sub Proxy
Subscribes to the simulator's PUB ports and re-publishes on proxy ports.

ZMQ framing (from examining zmq_pub_server.py):
  Simulator PUB sends 3 frames:
    frame[0] = topic       (e.g., b'simulator_topic')
    frame[1] = operation   (e.g., b'task_status', b'probe', b'chip_update')
    frame[2] = data JSON   (e.g., '{"MsgType":"TaskStatus","TaskId":"..."}')

Proxy approach:
  subscriber.connect(simulator_pub_port)   — subscribe to everything
  publisher.bind(proxy_pub_port)           — re-publish for PilotOS
  Forward all frames transparently while capturing a copy.
"""
import time
import threading
import logging
import zmq
from typing import Optional, Callable, List

from store.models import CapturedMessage
from config import ProbeConfig

logger = logging.getLogger("pilotprobe.pub_proxy")


class PubProxy:
    """
    Transparent Pub-Sub proxy for a single quantum system.

    Subscribes to the real simulator's PUB socket, captures messages,
    and re-publishes them on a proxy port for PilotOS to subscribe to.
    """

    def __init__(
        self,
        system_type: str,
        simulator_pub_port: int,
        proxy_pub_port: int,
        simulator_host: str = "localhost",
        on_capture: Optional[Callable[[CapturedMessage], None]] = None,
    ):
        self.system_type = system_type
        self.simulator_pub_port = simulator_pub_port
        self.proxy_pub_port = proxy_pub_port
        self.simulator_host = simulator_host
        self.on_capture = on_capture

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._context: Optional[zmq.Context] = None

        # Stats
        self.pub_count = 0

    # ── Lifecycle ───────────────────────────────────────────────────

    def start(self):
        """Start the pub-sub proxy in a background thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._run,
            name=f"pub-proxy-{self.system_type}",
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
        """Subscribe → capture → re-publish loop."""
        self._context = zmq.Context()

        # Subscriber: connect to the real simulator's PUB
        subscriber = self._context.socket(zmq.SUB)
        subscriber.setsockopt(zmq.SUBSCRIBE, b"")  # Subscribe to all topics
        subscriber.setsockopt(zmq.RCVHWM, ProbeConfig.ZMQ_HWM)
        subscriber.setsockopt(zmq.LINGER, ProbeConfig.ZMQ_LINGER_MS)
        subscriber.connect(
            f"tcp://{self.simulator_host}:{self.simulator_pub_port}"
        )

        # Publisher: PilotOS subscribes here instead of the simulator
        publisher = self._context.socket(zmq.PUB)
        publisher.setsockopt(zmq.SNDHWM, ProbeConfig.ZMQ_HWM)
        publisher.setsockopt(zmq.LINGER, ProbeConfig.ZMQ_LINGER_MS)
        publisher.bind(f"tcp://{ProbeConfig.BIND_ADDRESS}:{self.proxy_pub_port}")

        poller = zmq.Poller()
        poller.register(subscriber, zmq.POLLIN)

        logger.info(
            f"[{self.system_type}] Pub proxy: "
            f"sub :{self.simulator_pub_port} → pub :{self.proxy_pub_port}"
        )

        try:
            while self._running:
                sockets = dict(poller.poll(ProbeConfig.POLL_TIMEOUT_MS))

                if subscriber in sockets:
                    frames = subscriber.recv_multipart()

                    # Capture the published message
                    self._capture_pub(frames)

                    # Re-publish exactly as received
                    publisher.send_multipart(frames)

        except zmq.ZMQError as e:
            if self._running:
                logger.error(f"[{self.system_type}] PUB proxy ZMQ error: {e}")
        finally:
            subscriber.close()
            publisher.close()
            self._context.term()
            logger.info(f"[{self.system_type}] Pub proxy stopped")

    # ── Capture helper ──────────────────────────────────────────────

    def _capture_pub(self, frames: List[bytes]):
        """Capture a PUB message (3-frame: topic + operation + data)."""
        self.pub_count += 1
        msg = CapturedMessage.from_pub_frames(
            system_type=self.system_type,
            frames=frames,
        )
        if self.on_capture:
            self.on_capture(msg)
