"""
PilotProbe Proxy Manager
Orchestrates all Router and Pub proxies across 4 quantum systems.
"""
import time
import logging
from datetime import datetime
from typing import Callable, Optional, List

from config import SystemType, ProbeConfig
from store.models import CapturedMessage
from store.database import MessageStore
from .router_proxy import RouterProxy
from .pub_proxy import PubProxy
from validator.validator import ProtocolValidator
from dashboard import ws_manager
import dataclasses

logger = logging.getLogger("pilotprobe.proxy_manager")


class ProxyManager:
    """
    Creates and manages 4 Router proxies + 4 Pub proxies.
    Wires them to the message store, validator, and CLI logger.
    """

    def __init__(self, store: MessageStore):
        self.store = store
        self.validator = ProtocolValidator()
        self._router_proxies: List[RouterProxy] = []
        self._pub_proxies: List[PubProxy] = []
        self._capture_callbacks: List[Callable[[CapturedMessage], None]] = []
        self._message_count = 0

        # Register default callbacks
        self.add_capture_callback(self._cli_log)
        self.add_capture_callback(self._store_message)
        self.add_capture_callback(self._broadcast_message)

    # ── Callbacks ───────────────────────────────────────────────────

    def add_capture_callback(self, cb: Callable[[CapturedMessage], None]):
        """Add a callback that fires on every captured message."""
        self._capture_callbacks.append(cb)

    def _on_capture(self, msg: CapturedMessage):
        """Dispatch captured message to all registered callbacks."""
        self._message_count += 1
        
        # Run validation before dispatching to callbacks
        try:
            self.validator.validate(msg)
        except Exception as e:
            logger.error(f"Validation error: {e}")

        for cb in self._capture_callbacks:
            try:
                cb(msg)
            except Exception as e:
                logger.error(f"Capture callback error: {e}")

    # ── Default callbacks ───────────────────────────────────────────

    def _store_message(self, msg: CapturedMessage):
        """Store captured message in SQLite."""
        self.store.store(msg)

    def _broadcast_message(self, msg: CapturedMessage):
        """Broadcast message to connected WebSocket clients."""
        try:
            ws_manager.broadcast_sync(dataclasses.asdict(msg))
        except Exception as e:
            logger.error(f"WebSocket broadcast error: {e}")

    def _cli_log(self, msg: CapturedMessage):
        """Pretty-print captured message to terminal."""
        cfg = ProbeConfig

        # Timestamp
        ts = datetime.fromtimestamp(msg.timestamp).strftime("%H:%M:%S.%f")[:-3]

        # System color
        try:
            sys_type = SystemType(msg.system_type)
            color = cfg.SYSTEM_COLORS.get(sys_type, "")
        except ValueError:
            color = ""

        # Direction symbol
        dir_sym = cfg.DIRECTION_SYMBOLS.get(msg.direction, "? ???")

        # Validation indicator
        if not msg.is_valid:
            valid_icon = f"{cfg.COLOR_RED}❌{cfg.COLOR_RESET}"
        elif msg.validation_errors and "⚠️" in msg.validation_errors:
            valid_icon = f"{cfg.COLOR_YELLOW}⚠️{cfg.COLOR_RESET}"
        else:
            valid_icon = f"{cfg.COLOR_GREEN}✅{cfg.COLOR_RESET}"

        # Summary
        summary = msg.summary_line()

        # Format: [HH:MM:SS.mmm] ← REQ  superconducting  MsgHeartbeat  SN=1  ✅
        line = (
            f"{cfg.COLOR_DIM}[{ts}]{cfg.COLOR_RESET} "
            f"{dir_sym}  "
            f"{color}{msg.system_type:<18}{cfg.COLOR_RESET} "
            f"{summary}  "
            f"{valid_icon}"
        )
        print(line)

    # ── Lifecycle ───────────────────────────────────────────────────

    def start(self):
        """Start all proxy pairs for every quantum system."""
        print()
        print(f"{ProbeConfig.COLOR_BOLD}[PilotProbe] Starting proxy interceptors...{ProbeConfig.COLOR_RESET}")
        print()

        for sys_type in SystemType:
            # Router proxy
            rp = RouterProxy(
                system_type=sys_type.value,
                listen_port=ProbeConfig.PROXY_ROUTER_PORTS[sys_type],
                target_port=ProbeConfig.SIMULATOR_ROUTER_PORTS[sys_type],
                target_host=ProbeConfig.SIMULATOR_HOST,
                on_capture=self._on_capture,
            )
            rp.start()
            self._router_proxies.append(rp)

            # Pub proxy
            pp = PubProxy(
                system_type=sys_type.value,
                simulator_pub_port=ProbeConfig.SIMULATOR_PUB_PORTS[sys_type],
                proxy_pub_port=ProbeConfig.PROXY_PUB_PORTS[sys_type],
                simulator_host=ProbeConfig.SIMULATOR_HOST,
                on_capture=self._on_capture,
            )
            pp.start()
            self._pub_proxies.append(pp)

            # Display port mapping
            rp_listen = ProbeConfig.PROXY_ROUTER_PORTS[sys_type]
            rp_target = ProbeConfig.SIMULATOR_ROUTER_PORTS[sys_type]
            pp_sub = ProbeConfig.SIMULATOR_PUB_PORTS[sys_type]
            pp_pub = ProbeConfig.PROXY_PUB_PORTS[sys_type]

            sys_color = ProbeConfig.SYSTEM_COLORS.get(sys_type, "")
            rst = ProbeConfig.COLOR_RESET

            print(
                f"  {sys_color}{sys_type.value:<18}{rst} "
                f"Router {rp_listen} → {rp_target}   "
                f"Pub {pp_sub} → {pp_pub}"
            )

        print()
        print(f"{ProbeConfig.COLOR_BOLD}[PilotProbe] All proxies active. Waiting for traffic...{ProbeConfig.COLOR_RESET}")
        print(f"{ProbeConfig.COLOR_DIM}{'─' * 80}{ProbeConfig.COLOR_RESET}")
        print()

    def stop(self):
        """Stop all proxies gracefully."""
        print()
        print(f"{ProbeConfig.COLOR_BOLD}[PilotProbe] Shutting down proxies...{ProbeConfig.COLOR_RESET}")

        for rp in self._router_proxies:
            rp.stop()
        for pp in self._pub_proxies:
            pp.stop()

        print(f"[PilotProbe] Total messages captured: {self._message_count}")
        print(f"[PilotProbe] Messages stored in DB: {self.store.total_stored}")

    @property
    def message_count(self) -> int:
        return self._message_count
