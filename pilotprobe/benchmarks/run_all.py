#!/usr/bin/env python3
"""
PilotProbe Benchmark Suite — Main Runner

Runs all benchmark tests and generates a JSON report.

Usage:
  # Run only validation accuracy (no proxy/simulator needed):
    python benchmarks/run_all.py --validation-only

  # Run all benchmarks (requires simulator + proxy running):
    python benchmarks/run_all.py --all

  # Run with custom message count:
    python benchmarks/run_all.py --all --num-messages 1000
"""
import sys
import os
import json
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from benchmarks.bench_validation import run_validation_benchmark


def main():
    parser = argparse.ArgumentParser(description="PilotProbe Benchmark Suite")
    parser.add_argument("--all", action="store_true", help="Run all benchmarks")
    parser.add_argument("--validation-only", action="store_true",
                        help="Run only validation accuracy (no proxy needed)")
    parser.add_argument("--latency", action="store_true", help="Run latency benchmark")
    parser.add_argument("--throughput", action="store_true", help="Run throughput benchmark")
    parser.add_argument("--num-messages", type=int, default=500,
                        help="Number of messages for latency/throughput tests (default: 500)")
    parser.add_argument("--direct-port", type=int, default=7000,
                        help="Direct simulator port (default: 7000)")
    parser.add_argument("--proxy-port", type=int, default=6000,
                        help="PilotProbe proxy port (default: 6000)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSON report path")
    args = parser.parse_args()

    if not any([args.all, args.validation_only, args.latency, args.throughput]):
        parser.print_help()
        print("\nError: Specify at least one benchmark to run.")
        return 1

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           PilotProbe Benchmark Suite v1.0                   ║
║           Quantum OS Diagnostic Tool Evaluation             ║
╚══════════════════════════════════════════════════════════════╝
  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")

    report = {
        "tool": "PilotProbe",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "benchmarks": {},
    }

    # ── Benchmark 1: Latency ──
    if args.all or args.latency:
        from benchmarks.bench_latency import run_latency_benchmark
        try:
            result = run_latency_benchmark(
                direct_port=args.direct_port,
                proxy_port=args.proxy_port,
                num_messages=args.num_messages,
            )
            report["benchmarks"]["latency"] = result
        except Exception as e:
            print(f"  ❌ Latency benchmark failed: {e}")
            print("     Make sure the simulator and PilotProbe proxy are running.")
            report["benchmarks"]["latency"] = {"error": str(e)}

    # ── Benchmark 2: Validation Accuracy ──
    if args.all or args.validation_only:
        try:
            result = run_validation_benchmark()
            report["benchmarks"]["validation"] = result
        except Exception as e:
            print(f"  ❌ Validation benchmark failed: {e}")
            report["benchmarks"]["validation"] = {"error": str(e)}

    # ── Benchmark 3: Throughput ──
    if args.all or args.throughput:
        from benchmarks.bench_throughput import run_throughput_benchmark
        try:
            result = run_throughput_benchmark(
                target_port=args.proxy_port,
                num_messages=args.num_messages,
            )
            report["benchmarks"]["throughput"] = result
        except Exception as e:
            print(f"  ❌ Throughput benchmark failed: {e}")
            print("     Make sure the simulator and PilotProbe proxy are running.")
            report["benchmarks"]["throughput"] = {"error": str(e)}

    # ── Save report ──
    output_path = args.output or f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  📄 Report saved to: {output_path}")

    # ── Print summary ──
    print(f"\n{'='*60}")
    print("  BENCHMARK SUMMARY")
    print(f"{'='*60}")
    for name, result in report["benchmarks"].items():
        if "error" in result:
            print(f"  {name}: ❌ FAILED ({result['error']})")
        elif name == "validation":
            print(f"  {name}: {result['detection_rate']}% accuracy "
                  f"({result['passed']}/{result['total_tests']} passed)")
        elif name == "latency":
            print(f"  {name}: {result['overhead_mean_us']} μs overhead "
                  f"({result['overhead_percent']}%)")
        elif name == "throughput":
            print(f"  {name}: {result['throughput_msg_per_sec']:.0f} msg/s "
                  f"({result['loss_percent']}% loss)")
    print(f"{'='*60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
