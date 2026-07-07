"""
Benchmark 1: Latency Overhead Measurement
Measures the round-trip latency added by PilotProbe's transparent proxy.

Methodology:
  1. Start a mock ZMQ ROUTER server (simulating the quantum simulator).
  2. Send N messages DIRECTLY to the mock server and measure RTT.
  3. Send N messages THROUGH PilotProbe proxy and measure RTT.
  4. Compare the two to calculate proxy overhead.

Output: Mean, median, P95, P99 latency for both paths + overhead delta.
"""
import zmq
import json
import time
import statistics
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def run_mock_server(port: int, stop_after: int = 1000):
    """A simple ZMQ ROUTER echo server that replies to every request."""
    ctx = zmq.Context()
    sock = ctx.socket(zmq.ROUTER)
    sock.bind(f"tcp://0.0.0.0:{port}")
    count = 0
    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)
    while count < stop_after:
        socks = dict(poller.poll(100))
        if sock in socks:
            frames = sock.recv_multipart()
            identity = frames[0]
            payload = frames[-1]
            # Echo back with an Ack
            try:
                data = json.loads(payload.decode("utf-8"))
                reply = {
                    "MsgType": data.get("MsgType", "Unknown") + "Ack",
                    "SN": data.get("SN", 0),
                    "ErrCode": 0,
                }
            except Exception:
                reply = {"MsgType": "ErrorAck", "SN": 0, "ErrCode": 1}
            sock.send_multipart([identity, json.dumps(reply).encode("utf-8")])
            count += 1
    sock.close()
    ctx.term()


def measure_rtt(target_port: int, num_messages: int = 500) -> list:
    """Send messages to a target port and measure round-trip times."""
    ctx = zmq.Context()
    sock = ctx.socket(zmq.DEALER)
    sock.setsockopt(zmq.IDENTITY, b"bench-client")
    sock.setsockopt(zmq.LINGER, 0)
    sock.connect(f"tcp://localhost:{target_port}")

    # Warmup
    time.sleep(0.3)
    for i in range(5):
        msg = {"MsgType": "MsgHeartbeat", "SN": i, "Chip": 72,
               "TimeStamp": int(time.time() * 1000)}
        sock.send(json.dumps(msg).encode("utf-8"))
        sock.recv()

    # Actual measurement
    latencies = []
    for i in range(num_messages):
        msg = {"MsgType": "MsgHeartbeat", "SN": 100 + i, "Chip": 72,
               "TimeStamp": int(time.time() * 1000)}
        payload = json.dumps(msg).encode("utf-8")

        t_start = time.perf_counter_ns()
        sock.send(payload)
        sock.recv()
        t_end = time.perf_counter_ns()

        latencies.append((t_end - t_start) / 1000.0)  # Convert to microseconds

    sock.close()
    ctx.term()
    return latencies


def compute_stats(latencies: list) -> dict:
    """Compute statistical summary of latency measurements."""
    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)
    return {
        "count": n,
        "mean_us": round(statistics.mean(latencies), 1),
        "median_us": round(statistics.median(latencies), 1),
        "stdev_us": round(statistics.stdev(latencies), 1) if n > 1 else 0,
        "min_us": round(min(latencies), 1),
        "max_us": round(max(latencies), 1),
        "p95_us": round(latencies_sorted[int(n * 0.95)], 1),
        "p99_us": round(latencies_sorted[int(n * 0.99)], 1),
    }


def run_latency_benchmark(
    direct_port: int = 7000,
    proxy_port: int = 6000,
    num_messages: int = 500,
) -> dict:
    """
    Run the full latency benchmark.
    
    Prerequisites:
      - Mock server running on direct_port (or real simulator).
      - PilotProbe proxy running, forwarding proxy_port -> direct_port.
    """
    print(f"\n{'='*60}")
    print("  BENCHMARK 1: Latency Overhead Measurement")
    print(f"{'='*60}")
    print(f"  Messages per test: {num_messages}")
    print(f"  Direct port: {direct_port} | Proxy port: {proxy_port}")
    print()

    # Phase 1: Direct measurement
    print("  [1/2] Measuring DIRECT latency (no proxy)...")
    direct_latencies = measure_rtt(direct_port, num_messages)
    direct_stats = compute_stats(direct_latencies)
    print(f"         Mean: {direct_stats['mean_us']:.1f} μs | "
          f"P95: {direct_stats['p95_us']:.1f} μs | "
          f"P99: {direct_stats['p99_us']:.1f} μs")

    # Phase 2: Through proxy
    print("  [2/2] Measuring PROXY latency (through PilotProbe)...")
    proxy_latencies = measure_rtt(proxy_port, num_messages)
    proxy_stats = compute_stats(proxy_latencies)
    print(f"         Mean: {proxy_stats['mean_us']:.1f} μs | "
          f"P95: {proxy_stats['p95_us']:.1f} μs | "
          f"P99: {proxy_stats['p99_us']:.1f} μs")

    # Calculate overhead
    overhead_mean = proxy_stats["mean_us"] - direct_stats["mean_us"]
    overhead_pct = (overhead_mean / direct_stats["mean_us"]) * 100 if direct_stats["mean_us"] > 0 else 0

    print(f"\n  ── Results ──")
    print(f"  Proxy overhead (mean): {overhead_mean:.1f} μs ({overhead_pct:.1f}%)")
    print(f"{'='*60}\n")

    return {
        "benchmark": "latency_overhead",
        "num_messages": num_messages,
        "direct": direct_stats,
        "proxy": proxy_stats,
        "overhead_mean_us": round(overhead_mean, 1),
        "overhead_percent": round(overhead_pct, 1),
    }


if __name__ == "__main__":
    import threading

    MOCK_PORT = 7000
    NUM = 500

    print("Starting mock server...")
    server_thread = threading.Thread(
        target=run_mock_server, args=(MOCK_PORT, NUM + 10), daemon=True
    )
    server_thread.start()
    time.sleep(0.5)

    print("Running direct latency test...")
    lats = measure_rtt(MOCK_PORT, NUM)
    stats = compute_stats(lats)
    print(f"Direct stats: {stats}")
