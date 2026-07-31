#!/usr/bin/env python3
"""
PilotProbe Benchmark Suite — Main Runner (v2.0)

Runs all benchmark tests and generates a comprehensive JSON report.

Benchmarks:
  1. Validation Accuracy   — Hand-crafted test cases (all 4 paradigms)
  2. Fuzz Validation       — 1000+ auto-generated mutated test cases
  3. Adversarial Injection — Interleaved attack + legitimate traffic
  4. Baseline Comparison   — tcpdump/strace vs PilotProbe
  5. Latency Overhead      — Proxy round-trip latency (requires live proxy)
  6. Throughput            — Max message throughput (requires live proxy)

Usage:
  # Run offline benchmarks (no proxy/simulator needed):
    python benchmarks/run_all.py --validation-only
    python benchmarks/run_all.py --offline

  # Run all benchmarks including live proxy tests:
    python benchmarks/run_all.py --all

  # Run with custom fuzz count:
    python benchmarks/run_all.py --offline --fuzz-count 2000

Note: PilotProbe is designed for job-level circuit submission and result
retrieval observability, NOT real-time pulse control or active reset loops
where classical control must respond in <1 ms.
"""
import sys
import os
import json
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from benchmarks.bench_validation import run_validation_benchmark
from benchmarks.bench_fuzz_validation import run_fuzz_benchmark
from benchmarks.bench_adversarial import run_adversarial_benchmark
from benchmarks.bench_baseline_comparison import run_baseline_benchmark


def main():
    parser = argparse.ArgumentParser(description="PilotProbe Benchmark Suite v2.0")
    parser.add_argument("--all", action="store_true", help="Run ALL benchmarks (requires live proxy)")
    parser.add_argument("--offline", action="store_true",
                        help="Run all offline benchmarks (no proxy needed)")
    parser.add_argument("--validation-only", action="store_true",
                        help="Run only hand-crafted validation accuracy")
    parser.add_argument("--fuzz", action="store_true", help="Run fuzz validation")
    parser.add_argument("--adversarial", action="store_true", help="Run adversarial injection")
    parser.add_argument("--baseline", action="store_true", help="Run baseline comparison")
    parser.add_argument("--latency", action="store_true", help="Run latency benchmark (requires proxy)")
    parser.add_argument("--throughput", action="store_true", help="Run throughput benchmark (requires proxy)")
    parser.add_argument("--fuzz-count", type=int, default=1000,
                        help="Target fuzz test case count (default: 1000)")
    parser.add_argument("--num-messages", type=int, default=500,
                        help="Number of messages for latency/throughput tests (default: 500)")
    parser.add_argument("--direct-port", type=int, default=7000,
                        help="Direct simulator port (default: 7000)")
    parser.add_argument("--proxy-port", type=int, default=6000,
                        help="PilotProbe proxy port (default: 6000)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSON report path")
    args = parser.parse_args()

    if not any([args.all, args.offline, args.validation_only, args.fuzz,
                args.adversarial, args.baseline, args.latency, args.throughput]):
        parser.print_help()
        print("\nError: Specify at least one benchmark to run.")
        return 1

    # --offline enables all non-proxy benchmarks
    run_validation = args.all or args.offline or args.validation_only
    run_fuzz = args.all or args.offline or args.fuzz
    run_adversarial_test = args.all or args.offline or args.adversarial
    run_baseline = args.all or args.offline or args.baseline
    run_latency = args.all or args.latency
    run_throughput = args.all or args.throughput

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           PilotProbe Benchmark Suite v2.0                   ║
║           Quantum OS Diagnostic Tool Evaluation             ║
║                                                              ║
║  Scope: Job-level circuit submission & result retrieval      ║
║         (not real-time pulse control)                        ║
╚══════════════════════════════════════════════════════════════╝
  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  Platform:  Simulation-based feasibility study
""")

    report = {
        "tool": "PilotProbe",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "scope": "Job-level circuit submission and result retrieval observability",
        "evaluation_platform": "Python-based quantum simulator (PilotOS ZMQ protocol)",
        "benchmarks": {},
    }

    # ── Benchmark 1: Hand-crafted Validation Accuracy ──
    if run_validation:
        try:
            result = run_validation_benchmark()
            report["benchmarks"]["validation_accuracy"] = result
        except Exception as e:
            print(f"  ❌ Validation benchmark failed: {e}")
            import traceback; traceback.print_exc()
            report["benchmarks"]["validation_accuracy"] = {"error": str(e)}

    # ── Benchmark 2: Fuzz Validation ──
    if run_fuzz:
        try:
            result = run_fuzz_benchmark(total_target=args.fuzz_count)
            report["benchmarks"]["fuzz_validation"] = result
        except Exception as e:
            print(f"  ❌ Fuzz validation benchmark failed: {e}")
            import traceback; traceback.print_exc()
            report["benchmarks"]["fuzz_validation"] = {"error": str(e)}

    # ── Benchmark 3: Adversarial Injection ──
    if run_adversarial_test:
        try:
            result = run_adversarial_benchmark()
            report["benchmarks"]["adversarial_injection"] = result
        except Exception as e:
            print(f"  ❌ Adversarial benchmark failed: {e}")
            import traceback; traceback.print_exc()
            report["benchmarks"]["adversarial_injection"] = {"error": str(e)}

    # ── Benchmark 4: Baseline Comparison ──
    if run_baseline:
        try:
            result = run_baseline_benchmark()
            report["benchmarks"]["baseline_comparison"] = result
        except Exception as e:
            print(f"  ❌ Baseline benchmark failed: {e}")
            import traceback; traceback.print_exc()
            report["benchmarks"]["baseline_comparison"] = {"error": str(e)}

    # ── Benchmark 5: Latency ──
    if run_latency:
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

    # ── Benchmark 6: Throughput ──
    if run_throughput:
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
            print(f"  {name}: ❌ FAILED ({result['error'][:60]})")
        elif name == "validation_accuracy":
            print(f"  {name}: {result['detection_rate']}% accuracy "
                  f"({result['passed']}/{result['total_tests']} passed)")
        elif name == "fuzz_validation":
            print(f"  {name}: {result['overall_accuracy']}% accuracy "
                  f"({result['total_cases']} cases, "
                  f"TP={result['true_positives']}, TN={result['true_negatives']}, "
                  f"FP={result['false_positives']}, FN={result['false_negatives']})")
        elif name == "adversarial_injection":
            print(f"  {name}: {result['detection_rate']}% detection "
                  f"({result['attacks_caught']}/{result['total_attacks']} attacks caught, "
                  f"FP={result['false_positive_rate']}%)")
        elif name == "baseline_comparison":
            print(f"  {name}: PilotProbe {result['pilotprobe']['capability_score']} capabilities "
                  f"vs tcpdump {result['tcpdump']['capability_score']}")
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
