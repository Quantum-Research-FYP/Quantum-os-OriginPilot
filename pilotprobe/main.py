#!/usr/bin/env python3
"""
PilotProbe — ZMQ Protocol Analyzer & Diagnostic Tool for PilotOS

Usage:
    python main.py --proxy                  # Start proxy interceptor only (CLI output)
    python main.py --proxy --dashboard      # Start proxy + web dashboard
    python main.py --help                   # Show all options

This tool intercepts all ZMQ traffic between PilotOS and quantum hardware
simulators, providing full visibility into the quantum task pipeline.

No modifications to PilotOS or the simulator are required.
"""
import sys
import os
import time
import signal
import logging
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ProbeConfig, SystemType
from store.database import MessageStore
from proxy.proxy_manager import ProxyManager


def setup_logging(verbose: bool = False):
    """Configure logging for PilotProbe."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def print_banner():
    """Print the PilotProbe startup banner."""
    C = ProbeConfig
    print(f"""
{C.COLOR_BOLD}{C.COLOR_CYAN}
  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║   ██████╗ ██╗██╗      ██████╗ ████████╗                   ║
  ║   ██╔══██╗██║██║     ██╔═══██╗╚══██╔══╝                   ║
  ║   ██████╔╝██║██║     ██║   ██║   ██║                      ║
  ║   ██╔═══╝ ██║██║     ██║   ██║   ██║                      ║
  ║   ██║     ██║███████╗╚██████╔╝   ██║                      ║
  ║   ╚═╝     ╚═╝╚══════╝ ╚═════╝    ╚═╝                      ║
  ║              ██████╗ ██████╗  ██████╗ ██████╗ ███████╗     ║
  ║              ██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝     ║
  ║              ██████╔╝██████╔╝██║   ██║██████╔╝█████╗       ║
  ║              ██╔═══╝ ██╔══██╗██║   ██║██╔══██╗██╔══╝       ║
  ║              ██║     ██║  ██║╚██████╔╝██████╔╝███████╗     ║
  ║              ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝     ║
  ║                                                           ║
  ║   ZMQ Protocol Analyzer for PilotOS                       ║
  ║   Quantum Hardware Diagnostic Tool                        ║
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝
{C.COLOR_RESET}""")


def main():
    parser = argparse.ArgumentParser(
        description="PilotProbe — ZMQ Protocol Analyzer for PilotOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start proxy interceptor with CLI output
  python main.py --proxy

  # Start proxy + web dashboard on port 9090
  python main.py --proxy --dashboard

  # Verbose logging for debugging
  python main.py --proxy -v

  # Custom database path
  python main.py --proxy --db /tmp/session.db

  # Connect to simulator on a different host
  python main.py --proxy --sim-host 192.168.1.100
        """,
    )

    parser.add_argument(
        "--proxy",
        action="store_true",
        help="Start the ZMQ proxy interceptor",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Start the web dashboard (requires --proxy)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=ProbeConfig.DATABASE_PATH,
        help=f"SQLite database path (default: {ProbeConfig.DATABASE_PATH})",
    )
    parser.add_argument(
        "--sim-host",
        type=str,
        default=ProbeConfig.SIMULATOR_HOST,
        help=f"Simulator host address (default: {ProbeConfig.SIMULATOR_HOST})",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )

    args = parser.parse_args()

    if not args.proxy and not args.dashboard:
        parser.print_help()
        print("\nError: Specify at least --proxy to start.")
        return 1

    # Setup
    setup_logging(args.verbose)
    print_banner()

    # Apply config overrides
    ProbeConfig.DATABASE_PATH = args.db
    ProbeConfig.SIMULATOR_HOST = args.sim_host

    # Initialize store
    store = MessageStore(db_path=args.db)
    store.start()

    # Initialize proxy manager
    proxy_manager = None
    if args.proxy:
        proxy_manager = ProxyManager(store)
        proxy_manager.start()

    if args.dashboard:
        from dashboard.app import create_app
        import uvicorn

        app = create_app(store)
        print(f"{ProbeConfig.COLOR_BOLD}[PilotProbe] Starting Dashboard on http://localhost:{ProbeConfig.DASHBOARD_PORT}...{ProbeConfig.COLOR_RESET}")
        try:
            uvicorn.run(app, host=ProbeConfig.BIND_ADDRESS, port=ProbeConfig.DASHBOARD_PORT, log_level="warning")
        except KeyboardInterrupt:
            pass
    else:
        # Graceful shutdown handler for headless mode
        shutdown_requested = False

        def handle_signal(signum, frame):
            nonlocal shutdown_requested
            if shutdown_requested:
                print("\nForce quit.")
                sys.exit(1)
            shutdown_requested = True
            print(f"\n{ProbeConfig.COLOR_YELLOW}[PilotProbe] Shutdown signal received...{ProbeConfig.COLOR_RESET}")

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        # Main loop
        try:
            while not shutdown_requested:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

    # Cleanup
    if proxy_manager:
        proxy_manager.stop()
    store.stop()

    print(f"\n{ProbeConfig.COLOR_GREEN}[PilotProbe] Shutdown complete.{ProbeConfig.COLOR_RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
