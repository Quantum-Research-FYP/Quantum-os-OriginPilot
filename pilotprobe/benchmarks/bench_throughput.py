"""
Benchmark 3: Throughput Measurement
Measures the maximum message throughput PilotProbe can sustain.

Methodology:
  1. Start a mock echo server.
  2. Fire messages as fast as possible through the proxy.
  3. Count how many messages per second are processed without loss.

Output: Messages/second, total time, data loss percentage.
"""
import zmq
import json
import time
import threading
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def mock_echo_server(port: int, max_msgs: int = 5000):
    """Echo server that counts received messages."""
    ctx = zmq.Context()
    sock = ctx.socket(zmq.ROUTER)
    sock.bind(f"tcp://0.0.0.0:{port}")
    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)
    count = 0
    while count < max_msgs:
        socks = dict(poller.poll(100))
        if sock in socks:
            frames = sock.recv_multipart()
            identity = frames[0]
            reply = json.dumps({"MsgType": "Ack", "SN": count, "ErrCode": 0}).encode()
            sock.send_multipart([identity, reply])
            count += 1
    sock.close()
    ctx.term()
    return count


def run_throughput_benchmark(
    target_port: int = 6000,
    num_messages: int = 2000,
) -> dict:
    """
    Fire messages as fast as possible and measure throughput.

    Prerequisites:
      - Mock server or simulator running on the backend port.
      - PilotProbe proxy running on target_port.
    """
    print(f"\n{'='*60}")
    print("  BENCHMARK 3: Throughput Measurement")
    print(f"{'='*60}")
    print(f"  Target port: {target_port} | Messages: {num_messages}")
    print()

    ctx = zmq.Context()
    sock = ctx.socket(zmq.DEALER)
    sock.setsockopt(zmq.IDENTITY, b"throughput-client")
    sock.setsockopt(zmq.LINGER, 0)
    sock.setsockopt(zmq.SNDHWM, 50000)
    sock.setsockopt(zmq.RCVHWM, 50000)
    sock.connect(f"tcp://localhost:{target_port}")
    time.sleep(0.3)

    # Send all messages and track timing
    print("  Sending messages...")
    sent = 0
    received = 0
    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)

    t_start = time.perf_counter()

    for i in range(num_messages):
        msg = {
            "MsgType": "MsgHeartbeat",
            "SN": i,
            "Chip": 72,
            "TimeStamp": int(time.time() * 1000),
        }
        sock.send(json.dumps(msg).encode("utf-8"))
        sent += 1

    # Collect all replies
    print("  Collecting replies...")
    deadline = time.time() + 10  # 10 second timeout
    while received < sent and time.time() < deadline:
        socks = dict(poller.poll(100))
        if sock in socks:
            sock.recv()
            received += 1

    t_end = time.perf_counter()
    elapsed = t_end - t_start

    sock.close()
    ctx.term()

    # Calculate metrics
    throughput = received / elapsed if elapsed > 0 else 0
    loss = sent - received
    loss_pct = (loss / sent) * 100 if sent > 0 else 0

    print(f"\n  ── Results ──")
    print(f"  Sent:      {sent} messages")
    print(f"  Received:  {received} messages")
    print(f"  Lost:      {loss} ({loss_pct:.1f}%)")
    print(f"  Duration:  {elapsed:.3f} seconds")
    print(f"  Throughput: {throughput:.0f} messages/second")
    print(f"{'='*60}\n")

    return {
        "benchmark": "throughput",
        "num_messages": num_messages,
        "sent": sent,
        "received": received,
        "lost": loss,
        "loss_percent": round(loss_pct, 1),
        "duration_sec": round(elapsed, 3),
        "throughput_msg_per_sec": round(throughput, 0),
    }


if __name__ == "__main__":
    run_throughput_benchmark()
