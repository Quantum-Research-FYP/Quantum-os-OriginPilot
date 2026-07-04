"""
PilotProbe Configuration
Port mappings, system types, and diagnostic settings.
"""
from enum import Enum


class SystemType(Enum):
    """Quantum system paradigm types (mirrors simulator's QuantumSystemType)"""
    SUPERCONDUCTING = "superconducting"
    ION_TRAP = "ion_trap"
    NEUTRAL_ATOM = "neutral_atom"
    PHOTONIC = "photonic"


class ProbeConfig:
    """Central configuration for PilotProbe"""

    # ── Proxy listen ports (PilotOS / test_client connects here) ──
    PROXY_ROUTER_PORTS = {
        SystemType.SUPERCONDUCTING: 6000,
        SystemType.ION_TRAP: 6001,
        SystemType.NEUTRAL_ATOM: 6002,
        SystemType.PHOTONIC: 6003,
    }

    # ── Simulator Router ports (proxy forwards requests here) ──
    SIMULATOR_ROUTER_PORTS = {
        SystemType.SUPERCONDUCTING: 7000,
        SystemType.ION_TRAP: 7001,
        SystemType.NEUTRAL_ATOM: 7002,
        SystemType.PHOTONIC: 7003,
    }

    # ── Simulator PUB ports (proxy subscribes here) ──
    SIMULATOR_PUB_PORTS = {
        SystemType.SUPERCONDUCTING: 8000,
        SystemType.ION_TRAP: 8001,
        SystemType.NEUTRAL_ATOM: 8002,
        SystemType.PHOTONIC: 8003,
    }

    # ── Proxy re-publish ports (PilotOS subscribes here instead of 8xxx) ──
    PROXY_PUB_PORTS = {
        SystemType.SUPERCONDUCTING: 9000,
        SystemType.ION_TRAP: 9001,
        SystemType.NEUTRAL_ATOM: 9002,
        SystemType.PHOTONIC: 9003,
    }

    # ── Network ──
    SIMULATOR_HOST = "localhost"
    BIND_ADDRESS = "0.0.0.0"

    # ── Dashboard ──
    DASHBOARD_PORT = 9090

    # ── Storage ──
    DATABASE_PATH = "pilotprobe.db"

    # ── ZMQ tuning ──
    POLL_TIMEOUT_MS = 100          # Poller timeout in milliseconds
    ZMQ_HWM = 10000                # High-water mark for send/recv buffers
    ZMQ_LINGER_MS = 0              # Linger period on socket close

    # ── CLI display ──
    SYSTEM_COLORS = {
        SystemType.SUPERCONDUCTING: "\033[94m",   # Bright blue
        SystemType.ION_TRAP:        "\033[92m",   # Bright green
        SystemType.NEUTRAL_ATOM:    "\033[95m",   # Bright magenta
        SystemType.PHOTONIC:        "\033[93m",    # Bright yellow
    }
    COLOR_RESET = "\033[0m"
    COLOR_DIM   = "\033[2m"
    COLOR_BOLD  = "\033[1m"
    COLOR_RED   = "\033[91m"
    COLOR_GREEN = "\033[92m"
    COLOR_YELLOW = "\033[93m"
    COLOR_CYAN  = "\033[96m"

    # ── Direction symbols ──
    DIRECTION_SYMBOLS = {
        "REQUEST":  "← REQ",
        "RESPONSE": "→ RES",
        "PUB":      "◆ PUB",
    }
