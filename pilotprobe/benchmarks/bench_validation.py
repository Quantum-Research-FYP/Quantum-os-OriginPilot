"""
Benchmark 2: Validation Accuracy Test Suite (All 4 Paradigms)
Tests PilotProbe's ability to correctly detect protocol violations
across Superconducting, Ion Trap, Neutral Atom, and Photonic systems.

Test Cases:
  A. Valid messages        → should PASS (no errors)
  B. Schema violations     → should be CAUGHT (type errors, missing fields)
  C. Semantic violations   → should be CAUGHT (duplicates, auth, transitions)
  D. Cross-paradigm tests  → validates all 4 paradigms

Note: PilotProbe is designed for job-level circuit submission and result
retrieval observability, NOT real-time pulse control or active reset loops
where classical control must respond in <1 ms.

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
    # ══════════════════════════════════════════════════════════════════
    # A. VALID Messages (should pass) — All 4 paradigms
    # ══════════════════════════════════════════════════════════════════

    # ── Superconducting ──
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
        "name": "Valid Superconducting GetChipConfig",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {"MsgType": "GetChipConfig", "SN": 3, "Chip": 72},
        "expect_valid": True,
    },
    {
        "id": "A4",
        "name": "Valid Superconducting MsgTaskAck",
        "system": "superconducting",
        "direction": "RESPONSE",
        "payload": {"MsgType": "MsgTaskAck", "SN": 2, "ErrCode": 0},
        "expect_valid": True,
    },
    {
        "id": "A5",
        "name": "Valid Superconducting MsgTaskResult",
        "system": "superconducting",
        "direction": "RESPONSE",
        "payload": {"MsgType": "MsgTaskResult", "SN": 2, "TaskId": "result-task-001",
                    "ErrCode": 0, "Key": ["00", "01"], "ProbCount": [50, 50]},
        "expect_valid": True,
    },
    {
        "id": "A6",
        "name": "Valid Superconducting SetVip",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {"MsgType": "SetVip", "SN": 100},
        "expect_valid": True,
    },
    {
        "id": "A7",
        "name": "Valid Superconducting ReleaseVip",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {"MsgType": "ReleaseVip", "SN": 101},
        "expect_valid": True,
    },

    # ── Ion Trap ──
    {
        "id": "A8",
        "name": "Valid Ion Trap MsgGetToken",
        "system": "ion_trap",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgGetToken"},
        "expect_valid": True,
    },
    {
        "id": "A9",
        "name": "Valid Ion Trap MsgGetTokenAck",
        "system": "ion_trap",
        "direction": "RESPONSE",
        "payload": {"MsgType": "MsgGetTokenAck", "ErrCode": 0, "Data": {"token": "abc123"}},
        "expect_valid": True,
    },
    {
        "id": "A10",
        "name": "Valid Ion Trap Heartbeat",
        "system": "ion_trap",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgHeartbeat", "SN": 10, "Chip": "IT-20", "TimeStamp": 1720000000000},
        "expect_valid": True,
    },
    {
        "id": "A11",
        "name": "Valid Ion Trap MsgTask",
        "system": "ion_trap",
        "direction": "REQUEST",
        "payload": {
            "MsgType": "MsgTask", "SN": 11, "TaskId": "ion-task-001",
            "ConvertQProg": "[[[{\"XX\": [0, 1, 90.0]}]]]",
            "Configure": {"Shot": 200, "TaskPriority": 1, "IsExperiment": True, "PointLabel": 64},
        },
        "expect_valid": True,
    },
    {
        "id": "A12",
        "name": "Valid Ion Trap MsgUpdateToken",
        "system": "ion_trap",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgUpdateToken"},
        "expect_valid": True,
    },

    # ── Neutral Atom ──
    {
        "id": "A13",
        "name": "Valid Neutral Atom MsgGetToken",
        "system": "neutral_atom",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgGetToken"},
        "expect_valid": True,
    },
    {
        "id": "A14",
        "name": "Valid Neutral Atom Heartbeat",
        "system": "neutral_atom",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgHeartbeat", "SN": 20, "Chip": "NA-50", "TimeStamp": 1720000000000},
        "expect_valid": True,
    },
    {
        "id": "A15",
        "name": "Valid Neutral Atom MsgTask",
        "system": "neutral_atom",
        "direction": "REQUEST",
        "payload": {
            "MsgType": "MsgTask", "SN": 21, "TaskId": "na-task-001",
            "ConvertQProg": "[[[{\"RZ\": [0, 45.0]}]]]",
            "Configure": {"Shot": 500, "TaskPriority": 2, "IsExperiment": False, "PointLabel": 32},
        },
        "expect_valid": True,
    },
    {
        "id": "A16",
        "name": "Valid Neutral Atom GetChipConfigAck",
        "system": "neutral_atom",
        "direction": "RESPONSE",
        "payload": {"MsgType": "GetChipConfigAck", "SN": 20, "ErrCode": 0,
                    "ChipConfig": {"qubits": 50, "type": "neutral_atom"},
                    "PointLabelList": [1, 2]},
        "expect_valid": True,
    },
    {
        "id": "A17",
        "name": "Valid Neutral Atom TaskStatusAck",
        "system": "neutral_atom",
        "direction": "RESPONSE",
        "payload": {"MsgType": "TaskStatusAck", "SN": 21, "TaskId": "na-status-001", "TaskStatus": 2},
        "expect_valid": True,
    },

    # ── Photonic ──
    {
        "id": "A18",
        "name": "Valid Photonic Heartbeat",
        "system": "photonic",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgHeartbeat", "SN": 30, "Chip": "PH-8", "TimeStamp": 1720000000000},
        "expect_valid": True,
    },
    {
        "id": "A19",
        "name": "Valid Photonic MsgTask",
        "system": "photonic",
        "direction": "REQUEST",
        "payload": {
            "MsgType": "MsgTask", "SN": 31, "TaskId": "ph-task-001",
            "ConvertQProg": "[[[{\"BS\": [0, 1, 0.5]}]]]",
            "Configure": {"Shot": 1000, "TaskPriority": 0, "IsExperiment": False, "PointLabel": 16},
        },
        "expect_valid": True,
    },
    {
        "id": "A20",
        "name": "Valid Photonic MsgTaskResult",
        "system": "photonic",
        "direction": "RESPONSE",
        "payload": {"MsgType": "MsgTaskResult", "SN": 31, "TaskId": "ph-result-001",
                    "ErrCode": 0, "Key": ["000", "001", "010", "011"],
                    "ProbCount": [250, 250, 250, 250]},
        "expect_valid": True,
    },
    {
        "id": "A21",
        "name": "Valid Photonic GetChipConfig",
        "system": "photonic",
        "direction": "REQUEST",
        "payload": {"MsgType": "GetChipConfig", "SN": 32, "Chip": "PH-8"},
        "expect_valid": True,
    },
    {
        "id": "A22",
        "name": "Valid Photonic SetVip",
        "system": "photonic",
        "direction": "REQUEST",
        "payload": {"MsgType": "SetVip", "SN": 200},
        "expect_valid": True,
    },

    # ══════════════════════════════════════════════════════════════════
    # B. SCHEMA Violations (should be caught) — All 4 paradigms
    # ══════════════════════════════════════════════════════════════════

    # ── Superconducting ──
    {
        "id": "B1",
        "name": "Schema Error: SN is string (superconducting)",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgHeartbeat", "SN": "one-hundred", "Chip": 72},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B2",
        "name": "Schema Error: MsgTask missing TaskId (superconducting)",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgTask", "SN": 5, "ConvertQProg": "[]",
                    "Configure": {"Shot": 100}},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B3",
        "name": "Schema Error: Shot is string (superconducting)",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {
            "MsgType": "MsgTask", "SN": 10, "TaskId": "schema-err-sc",
            "ConvertQProg": "[]",
            "Configure": {"Shot": "many", "TaskPriority": 0},
        },
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B4",
        "name": "Schema Error: Shot exceeds max 20000 (superconducting)",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {
            "MsgType": "MsgTask", "SN": 11, "TaskId": "schema-shot-max-sc",
            "ConvertQProg": "[]",
            "Configure": {"Shot": 99999},
        },
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B5",
        "name": "Schema Error: Invalid ErrCode enum (superconducting)",
        "system": "superconducting",
        "direction": "RESPONSE",
        "payload": {"MsgType": "MsgTaskAck", "SN": 12, "ErrCode": 777},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B6",
        "name": "Schema Error: Negative SN (superconducting)",
        "system": "superconducting",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgTask", "SN": -1, "TaskId": "neg-sn-sc",
                    "ConvertQProg": "[]", "Configure": {"Shot": 100}},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },

    # ── Ion Trap ──
    {
        "id": "B7",
        "name": "Schema Error: SN is string (ion_trap)",
        "system": "ion_trap",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgHeartbeat", "SN": "bad-sn", "Chip": "IT-20"},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B8",
        "name": "Schema Error: MsgTask missing Configure (ion_trap)",
        "system": "ion_trap",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgTask", "SN": 15, "TaskId": "ion-no-config",
                    "ConvertQProg": "[]"},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B9",
        "name": "Schema Error: Shot is zero (ion_trap)",
        "system": "ion_trap",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgTask", "SN": 16, "TaskId": "ion-shot-zero",
                    "ConvertQProg": "[]", "Configure": {"Shot": 0}},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B10",
        "name": "Schema Error: MsgGetTokenAck missing ErrCode (ion_trap)",
        "system": "ion_trap",
        "direction": "RESPONSE",
        "payload": {"MsgType": "MsgGetTokenAck"},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },

    # ── Neutral Atom ──
    {
        "id": "B11",
        "name": "Schema Error: SN is float (neutral_atom)",
        "system": "neutral_atom",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgHeartbeat", "SN": 3.14, "Chip": "NA-50"},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B12",
        "name": "Schema Error: MsgTask missing ConvertQProg (neutral_atom)",
        "system": "neutral_atom",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgTask", "SN": 25, "TaskId": "na-no-qprog",
                    "Configure": {"Shot": 100}},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B13",
        "name": "Schema Error: TaskId is integer (neutral_atom)",
        "system": "neutral_atom",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgTask", "SN": 26, "TaskId": 12345,
                    "ConvertQProg": "[]", "Configure": {"Shot": 100}},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B14",
        "name": "Schema Error: Invalid TaskStatus enum (neutral_atom)",
        "system": "neutral_atom",
        "direction": "RESPONSE",
        "payload": {"MsgType": "TaskStatusAck", "SN": 27, "TaskStatus": 99},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },

    # ── Photonic ──
    {
        "id": "B15",
        "name": "Schema Error: SN is boolean (photonic)",
        "system": "photonic",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgHeartbeat", "SN": True, "Chip": "PH-8"},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B16",
        "name": "Schema Error: Configure is string (photonic)",
        "system": "photonic",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgTask", "SN": 35, "TaskId": "ph-bad-config",
                    "ConvertQProg": "[]", "Configure": "not-an-object"},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B17",
        "name": "Schema Error: MsgTaskResult missing ErrCode (photonic)",
        "system": "photonic",
        "direction": "RESPONSE",
        "payload": {"MsgType": "MsgTaskResult", "SN": 36, "TaskId": "ph-no-errcode"},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },
    {
        "id": "B18",
        "name": "Schema Error: Empty TaskId (photonic)",
        "system": "photonic",
        "direction": "REQUEST",
        "payload": {"MsgType": "MsgTask", "SN": 37, "TaskId": "",
                    "ConvertQProg": "[]", "Configure": {"Shot": 100}},
        "expect_valid": False,
        "expect_error_contains": "Schema",
    },

    # ══════════════════════════════════════════════════════════════════
    # C. SEMANTIC Violations — All 4 paradigms
    # ══════════════════════════════════════════════════════════════════

    {
        "id": "C1",
        "name": "Semantic Error: Duplicate TaskId (superconducting)",
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
            "MsgType": "MsgTask", "SN": 50, "TaskId": "ion-no-auth-task",
            "ConvertQProg": "[]",
            "Configure": {"Shot": 100},
        },
        "expect_valid": True,  # Warnings don't make it invalid
        "expect_warning_contains": "MsgGetToken",
    },
    {
        "id": "C3",
        "name": "Semantic Warning: Neutral Atom MsgTask without auth",
        "system": "neutral_atom",
        "direction": "REQUEST",
        "payload": {
            "MsgType": "MsgTask", "SN": 60, "TaskId": "na-no-auth-task",
            "ConvertQProg": "[]",
            "Configure": {"Shot": 100},
        },
        "expect_valid": True,
        "expect_warning_contains": "MsgGetToken",
    },
]


def run_validation_benchmark() -> dict:
    """Run all validation accuracy test cases."""
    print(f"\n{'='*60}")
    print("  BENCHMARK 2: Validation Accuracy Test Suite")
    print("  (All 4 Paradigms: Superconducting, Ion Trap,")
    print("   Neutral Atom, Photonic)")
    print(f"{'='*60}\n")

    validator = ProtocolValidator()
    results = []
    passed = 0
    failed = 0

    # Track per-paradigm stats
    paradigm_stats = {}
    for paradigm in ["superconducting", "ion_trap", "neutral_atom", "photonic"]:
        paradigm_stats[paradigm] = {"passed": 0, "failed": 0, "total": 0}

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

        # Track per-paradigm
        paradigm = tc["system"]
        paradigm_stats[paradigm]["total"] += 1
        if test_passed:
            paradigm_stats[paradigm]["passed"] += 1
        else:
            paradigm_stats[paradigm]["failed"] += 1

        print(f"  [{tc['id']}] {status}  [{paradigm:>16s}] {tc['name']}")
        if not test_passed:
            print(f"        Reason: {reason}")
        if validated.validation_errors:
            print(f"        Errors: {validated.validation_errors}")

        results.append({
            "id": tc["id"],
            "name": tc["name"],
            "paradigm": paradigm,
            "passed": test_passed,
            "reason": reason,
        })

    total = passed + failed
    detection_rate = (passed / total) * 100 if total > 0 else 0

    print(f"\n  ── Results ──")
    print(f"  Passed: {passed}/{total} | Failed: {failed}/{total}")
    print(f"  Detection Accuracy: {detection_rate:.1f}%")

    print(f"\n  ── Per-Paradigm ──")
    for paradigm, stats in paradigm_stats.items():
        p_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {paradigm:>20s}: {stats['passed']}/{stats['total']} passed ({p_rate:.0f}%)")

    print(f"{'='*60}\n")

    return {
        "benchmark": "validation_accuracy",
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "detection_rate": round(detection_rate, 1),
        "paradigm_stats": paradigm_stats,
        "details": results,
    }


if __name__ == "__main__":
    run_validation_benchmark()
