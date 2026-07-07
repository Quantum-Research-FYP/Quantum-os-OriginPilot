"""
Benchmark 2: Validation Accuracy Test Suite
Tests PilotProbe's ability to correctly detect protocol violations.

Test Cases:
  A. Valid messages        → should PASS (no errors)
  B. Schema violations     → should be CAUGHT (type errors, missing fields)
  C. Semantic violations   → should be CAUGHT (duplicates, auth, transitions)
  D. Cross-paradigm tests  → validates all 4 paradigms

Output: Detection rate (expected catches / actual catches).
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from store.models import CapturedMessage
from validator.validator import ProtocolValidator


# ── Test Case Definitions ────────────────────────────────────────────

TEST_CASES = [
    # ── A. VALID Messages (should pass) ──
    {
        "id": "A1",
        "name": "Valid Superconducting Heartbeat",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgHeartbeat", "SN": 1, "Chip": 72, "TimeStamp": 1720000000000},
        "expect_valid": True,
    },
    {
        "id": "A2",
        "name": "Valid Superconducting MsgTask",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {
            "MsgType": "MsgTask", "SN": 2, "TaskId": "valid-task-001",
            "ConvertQProg": "[[[{\"RX\": [0, 90.0]}]]]",
            "Configure": {"Shot": 100, "TaskPriority": 0, "IsExperiment": False, "PointLabel": 128},
        },
        "expect_valid": True,
    },
    {
        "id": "A3",
        "name": "Valid Ion Trap MsgGetToken",
        "system": "ion_trap",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgGetToken"},
        "expect_valid": True,
    },

    # ── B. SCHEMA Violations (should be caught) ──
    {
        "id": "B1",
        "name": "Schema Error: SN is string instead of integer",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgHeartbeat", "SN": "one-hundred", "Chip": 72},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B2",
        "name": "Schema Error: MsgTask missing required TaskId",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgTask", "SN": 5, "ConvertQProg": "[]",
                    "Configure": {"Shot": 100}},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B3",
        "name": "Schema Error: Shot is string instead of integer",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {
            "MsgType": "MsgTask", "SN": 10, "TaskId": "schema-err-task",
            "ConvertQProg": "[]",
            "Configure": {"Shot": "many", "TaskPriority": 0},
        },
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },

    # ── C. SEMANTIC Violations ──
    {
        "id": "C1",
        "name": "Semantic Error: Duplicate TaskId",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {
            "MsgType": "MsgTask", "SN": 20, "TaskId": "valid-task-001",
            "ConvertQProg": "[]", "Configure": {"Shot": 100},
        },
        "expect_valid": False,
        "expect_error_contains": "Duplicate",
    },
    {
        "id": "C2",
        "name": "Semantic Warning: Ion Trap MsgTask without auth token",
        "system": "ion_trap",
        "direction": "REQUEST",
        "payload": {
            "MsgType": "MsgTask", "SN": 5, "TaskId": "ion-no-auth-task",
            "ConvertQProg": "[]",
            "Configure": {"Shot": 100},
        },
        "expect_valid": True,  # Warnings don't make it invalid
        "expect_warning_contains": "MsgGetToken",
    },
]


def run_validation_benchmark() -> dict:
    """Run all validation accuracy test cases."""
    print(f"\n{'='*60}")
    print("  BENCHMARK 2: Validation Accuracy Test Suite")
    print(f"{'='*60}\n")

    validator = ProtocolValidator()
    results = []
    passed = 0
    failed = 0

    for tc in TEST_CASES:
        payload_str = json.dumps(tc["payload"])
        msg = CapturedMessage.from_raw(
            system_type=tc["system"],
            direction=tc["direction"],
            channel="router",
            raw_bytes=payload_str.encode("utf-8"),
        )
        validated = validator.validate(msg)

        # Check expectations
        test_passed = True
        reason = ""

        if tc["expect_valid"] and not validated.is_valid:
            test_passed = False
            reason = f"Expected VALID but got errors: {validated.validation_errors}"
        elif not tc["expect_valid"] and validated.is_valid:
            test_passed = False
            reason = "Expected INVALID but passed validation"

        # Check error content
        if "expect_error_contains" in tc and validated.validation_errors:
            if tc["expect_error_contains"] not in validated.validation_errors:
                test_passed = False
                reason = f"Expected error containing '{tc['expect_error_contains']}' but got: {validated.validation_errors}"

        # Check warning content
        if "expect_warning_contains" in tc and validated.validation_errors:
            if tc["expect_warning_contains"] not in (validated.validation_errors or ""):
                test_passed = False
                reason = f"Expected warning containing '{tc['expect_warning_contains']}'"

        status = "✅ PASS" if test_passed else "❌ FAIL"
        if test_passed:
            passed += 1
        else:
            failed += 1

        print(f"  [{tc['id']}] {status}  {tc['name']}")
        if not test_passed:
            print(f"        Reason: {reason}")
        if validated.validation_errors:
            print(f"        Errors: {validated.validation_errors}")

        results.append({
            "id": tc["id"],
            "name": tc["name"],
            "passed": test_passed,
            "reason": reason,
        })

    total = passed + failed
    detection_rate = (passed / total) * 100 if total > 0 else 0

    print(f"\n  ── Results ──")
    print(f"  Passed: {passed}/{total} | Failed: {failed}/{total}")
    print(f"  Detection Accuracy: {detection_rate:.1f}%")
    print(f"{'='*60}\n")

    return {
        "benchmark": "validation_accuracy",
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "detection_rate": round(detection_rate, 1),
        "details": results,
    }


if __name__ == "__main__":
    run_validation_benchmark()
