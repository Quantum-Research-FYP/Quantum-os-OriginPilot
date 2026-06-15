"""
Main entry point for quantum simulation ZMQ servers
"""
import sys
import argparse
import signal
import os
from config import QuantumSystemType, ServerConfig
from zmq_router_server import ZmqRouterServer


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutting down server...")
    sys.exit(0)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Quantum Simulation ZMQ Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start superconducting quantum server (default port 7000)
  python main.py --system superconducting
  
  # Start ion trap server (default port 7001)
  python main.py --system ion_trap
  
  # Start neutral atom server (default port 7002)
  python main.py --system neutral_atom
  
  # Start photonic server (default port 7003)
  python main.py --system photonic
  
  # Start all servers
  python main.py --all
        """
    )
    
    parser.add_argument(
        '--system',
        type=str,
        choices=['superconducting', 'ion_trap', 'neutral_atom', 'photonic'],
        help='Type of quantum system to simulate'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Start all quantum system servers'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        help='Override default port (default: varies by system type)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--bind-address',
        type=str,
        default=ServerConfig.BIND_ADDRESS,
        help=f'Bind address (default: {ServerConfig.BIND_ADDRESS})'
    )
    
    return parser.parse_args()


def get_system_type(system_str: str) -> QuantumSystemType:
    """Convert string to QuantumSystemType enum"""
    system_map = {
        'superconducting': QuantumSystemType.SUPERCONDUCTING,
        'ion_trap': QuantumSystemType.ION_TRAP,
        'neutral_atom': QuantumSystemType.NEUTRAL_ATOM,
        'photonic': QuantumSystemType.PHOTONIC
    }
    return system_map.get(system_str.lower())


def start_single_server(system_type: QuantumSystemType, port: int = None):
    """Start a single server instance"""
    # Override port if specified
    if port:
        ServerConfig.ROUTER_PORTS[system_type] = port
    
    print("=" * 60)
    print(f"Starting {system_type.value} Quantum Simulation Server")
    print("=" * 60)
    
    server = ZmqRouterServer(system_type)
    
    try:
        server.start()
        print(f"\n{system_type.value} server is running")
        print(f"  - Router Port: {server.port}")
        print(f"  - Pub Port: {ServerConfig.PUB_PORTS[system_type]}")
        print(f"  - Bind Address: {ServerConfig.BIND_ADDRESS}")
        print(f"  - Log Level: {ServerConfig.LOG_LEVEL}")
        print(f"  - Thread Pool Size: {ServerConfig.THREAD_POOL_SIZE}")
        print(f"  - Max Queue Size: {ServerConfig.MAX_QUEUE_SIZE}")
        print("\nPress Ctrl+C to stop the server\n")
        
        # Keep main thread alive
        while True:
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        server.stop()
        print(f"{system_type.value} server stopped")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        server.stop()
        return 1
    
    return 0


def start_all_servers():
    """Start all quantum system servers"""
    import multiprocessing
    import time
    
    print("=" * 60)
    print("Starting All Quantum Simulation Servers")
    print("=" * 60)
    
    systems = [
        QuantumSystemType.SUPERCONDUCTING,
        QuantumSystemType.ION_TRAP,
        QuantumSystemType.NEUTRAL_ATOM,
        QuantumSystemType.PHOTONIC
    ]
    
    processes = []
    
    # Start each server in a separate process
    for system in systems:
        p = multiprocessing.Process(
            target=start_single_server,
            args=(system,)
        )
        p.daemon = True
        p.start()
        processes.append(p)
        time.sleep(0.5)  # Small delay between starts
    
    print(f"\nAll servers started successfully!")
    print("\nRunning servers:")
    for system in systems:
        router_port = ServerConfig.ROUTER_PORTS[system]
        pub_port = ServerConfig.PUB_PORTS[system]
        print(f"  - {system.value:<20} : Router {router_port}, Pub {pub_port}")
    
    print("\nPress Ctrl+C to stop all servers\n")
    
    try:
        # Wait for all processes
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print("\n\nShutting down all servers...")
        for p in processes:
            p.terminate()
        time.sleep(1)
        print("All servers stopped")


def main():
    """Main entry point"""
    # Parse arguments
    args = parse_args()
    
    # Update config from arguments
    ServerConfig.LOG_LEVEL = args.log_level
    ServerConfig.BIND_ADDRESS = args.bind_address
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create log directory if it doesn't exist
    os.makedirs('log', exist_ok=True)
    
    # Start server(s)
    if args.all:
        # Start all servers
        return start_all_servers()
    elif args.system:
        # Start single server
        system_type = get_system_type(args.system)
        if system_type:
            return start_single_server(system_type, args.port)
        else:
            print(f"Error: Unknown system type '{args.system}'")
            return 1
    else:
        # No server specified
        print("Error: Please specify --system or --all")
        print("Use --help for more information")
        return 1


if __name__ == '__main__':
    sys.exit(main())
