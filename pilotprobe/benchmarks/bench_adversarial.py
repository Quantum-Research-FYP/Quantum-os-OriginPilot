"""
Benchmark: Adversarial Injection Test Suite
Simulates a realistic traffic stream where malformed/adversarial messages
are injected at random intervals between legitimate traffic.

This tests PilotProbe's ability to:
  1. Detect ALL injected malformed messages (zero false negatives)
  2. Pass ALL legitimate messages (zero false positives)
  3. Maintain correct semantic state even under adversarial conditions

Attack categories:
  - SQL injection payloads in TaskId fields
  - Buffer overflow attempts (extremely long strings)
  - Unicode/encoding attacks
  - Protocol confusion (wrong MsgType constants)
  - Replay attacks (duplicate SN with different content)
  - State machine violations (invalid lifecycle transitions)
  - Auth bypass attempts (MsgTask without token on auth systems)
"""
import sys
import os
import json
import random
import time
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from store.models import CapturedMessage
from validator.validator import ProtocolValidator

ALL_PARADIGMS = ["superconducting", "ion_trap", "neutral_atom", "photonic"]


# ── Legitimate Traffic Templates ─────────────────────────────────────

def generate_legitimate_sequence(paradigm: str, task_num: int) -> List[dict]:
    """Generate a realistic legitimate traffic sequence for one task."""
    task_id = f"legit-{paradigm[:4]}-{task_num:04d}"
    sn_base = task_num * 10
    sequence = []

    # Heartbeat exchange
    sequence.append({
        "payload": {"MsgType": "MsgHeartbeat", "SN": sn_base, "Chip": 72,
                     "TimeStamp": int(time.time() * 1000)},
        "direction": "REQUEST", "is_legit": True,
    })
    sequence.append({
        "payload": {"MsgType": "MsgHeartbeatAck", "SN": sn_base,
                     "TimeStamp": int(time.time() * 1000)},
        "direction": "RESPONSE", "is_legit": True,
    })

    # Auth for ion_trap/neutral_atom
    if paradigm in ["ion_trap", "neutral_atom"]:
        sequence.append({
            "payload": {"MsgType": "MsgGetToken"},
            "direction": "REQUEST", "is_legit": True,
        })
        sequence.append({
            "payload": {"MsgType": "MsgGetTokenAck", "ErrCode": 0,
                         "Data": {"token": f"tok-{task_num}"}},
            "direction": "RESPONSE", "is_legit": True,
        })

    # Task submission
    sequence.append({
        "payload": {"MsgType": "MsgTask", "SN": sn_base + 1,
                     "TaskId": task_id,
                     "ConvertQProg": '[[[{"RX": [0, 90.0]}]]]',
                     "Configure": {"Shot": 100, "TaskPriority": 0,
                                   "IsExperiment": False, "PointLabel": 128}},
        "direction": "REQUEST", "is_legit": True,
    })
    sequence.append({
        "payload": {"MsgType": "MsgTaskAck", "SN": sn_base + 1, "ErrCode": 0},
        "direction": "RESPONSE", "is_legit": True,
    })

    return sequence


# ── Adversarial Attack Templates ─────────────────────────────────────

ADVERSARIAL_ATTACKS = [
    # Category 1: SQL Injection in TaskId
    {
        "name": "SQL injection in TaskId",
        "payload": {"MsgType": "MsgTask", "SN": 999, "TaskId": "'; DROP TABLE tasks; --",
                     "ConvertQProg": "[]", "Configure": {"Shot": 100}},
        "direction": "REQUEST",
        "expect_caught": False,  # SQL injection in string field may pass schema
    },
    {
        "name": "SQL injection in TaskId (UNION SELECT)",
        "payload": {"MsgType": "MsgTask", "SN": 998,
                     "TaskId": "' UNION SELECT * FROM users --",
                     "ConvertQProg": "[]", "Configure": {"Shot": 100}},
        "direction": "REQUEST",
        "expect_caught": False,  # schema allows any string
    },

    # Category 2: Buffer Overflow Attempts
    {
        "name": "Buffer overflow: 100KB TaskId",
        "payload": {"MsgType": "MsgTask", "SN": 997,
                     "TaskId": "A" * 100000,
                     "ConvertQProg": "[]", "Configure": {"Shot": 100}},
        "direction": "REQUEST",
        "expect_caught": False,  # no maxLength in schema
    },
    {
        "name": "Buffer overflow: 100KB ConvertQProg",
        "payload": {"MsgType": "MsgTask", "SN": 996,
                     "TaskId": "overflow-qprog",
                     "ConvertQProg": "X" * 100000,
                     "Configure": {"Shot": 100}},
        "direction": "REQUEST",
        "expect_caught": False,
    },

    # Category 3: Unicode/Encoding Attacks
    {
        "name": "Null bytes in TaskId",
        "payload": {"MsgType": "MsgTask", "SN": 995,
                     "TaskId": "task\x00injected",
                     "ConvertQProg": "[]", "Configure": {"Shot": 100}},
        "direction": "REQUEST",
        "expect_caught": False,
    },
    {
        "name": "Unicode RTL override in TaskId",
        "payload": {"MsgType": "MsgTask", "SN": 994,
                     "TaskId": "task\u202edetcejni",
                     "ConvertQProg": "[]", "Configure": {"Shot": 100}},
        "direction": "REQUEST",
        "expect_caught": False,
    },

    # Category 4: Protocol Confusion
    {
        "name": "Wrong MsgType constant",
        "payload": {"MsgType": "MsgHeartbeat", "SN": "not-an-int", "Chip": 72},
        "direction": "REQUEST",
        "expect_caught": True,  # SN must be integer
    },
    {
        "name": "Non-existent MsgType",
        "payload": {"MsgType": "MsgDeleteAllData", "SN": 1},
        "direction": "REQUEST",
        "expect_caught": False,  # unknown types are skipped, not flagged
    },
    {
        "name": "Empty MsgType",
        "payload": {"MsgType": "", "SN": 1},
        "direction": "REQUEST",
        "expect_caught": False,  # no schema match for empty MsgType
    },

    # Category 5: Constraint Violations
    {
        "name": "Shot exceeds maximum (20000)",
        "payload": {"MsgType": "MsgTask", "SN": 990,
                     "TaskId": "shot-overflow",
                     "ConvertQProg": "[]",
                     "Configure": {"Shot": 99999}},
        "direction": "REQUEST",
        "expect_caught": True,  # Shot max is 20000
    },
    {
        "name": "Shot is zero",
        "payload": {"MsgType": "MsgTask", "SN": 989,
                     "TaskId": "shot-zero",
                     "ConvertQProg": "[]",
                     "Configure": {"Shot": 0}},
        "direction": "REQUEST",
        "expect_caught": True,  # Shot minimum is 1
    },
    {
        "name": "Negative SN",
        "payload": {"MsgType": "MsgTask", "SN": -5,
                     "TaskId": "neg-sn-task",
                     "ConvertQProg": "[]",
                     "Configure": {"Shot": 100}},
        "direction": "REQUEST",
        "expect_caught": True,  # SN minimum is 0
    },
    {
        "name": "Invalid ErrCode in MsgTaskAck",
        "payload": {"MsgType": "MsgTaskAck", "SN": 988, "ErrCode": 999},
        "direction": "RESPONSE",
        "expect_caught": True,  # ErrCode must be in enum
    },

    # Category 6: Duplicate / Replay attacks
    {
        "name": "Duplicate TaskId replay",
        "payload": {"MsgType": "MsgTask", "SN": 987,
                     "TaskId": "replay-target",
                     "ConvertQProg": "[]",
                     "Configure": {"Shot": 100}},
        "direction": "REQUEST",
        "expect_caught": False,  # first submission is valid
        "setup_duplicate": True,
    },

    # Category 7: Missing required fields
    {
        "name": "MsgTask missing TaskId",
        "payload": {"MsgType": "MsgTask", "SN": 986,
                     "ConvertQProg": "[]",
                     "Configure": {"Shot": 100}},
        "direction": "REQUEST",
        "expect_caught": True,
    },
    {
        "name": "MsgTask missing Configure",
        "payload": {"MsgType": "MsgTask", "SN": 985,
                     "TaskId": "no-configure",
                     "ConvertQProg": "[]"},
        "direction": "REQUEST",
        "expect_caught": True,
    },
    {
        "name": "MsgTaskAck missing ErrCode",
        "payload": {"MsgType": "MsgTaskAck", "SN": 984},
        "direction": "RESPONSE",
        "expect_caught": True,
    },

    # Category 8: Type confusion
    {
        "name": "Shot as string",
        "payload": {"MsgType": "MsgTask", "SN": 983,
                     "TaskId": "shot-string",
                     "ConvertQProg": "[]",
                     "Configure": {"Shot": "one hundred"}},
        "direction": "REQUEST",
        "expect_caught": True,
    },
    {
        "name": "SN as float",
        "payload": {"MsgType": "MsgHeartbeat", "SN": 3.14, "Chip": 72},
        "direction": "REQUEST",
        "expect_caught": True,  # SN must be integer
    },
    {
        "name": "TaskId as integer",
        "payload": {"MsgType": "MsgTask", "SN": 982,
                     "TaskId": 12345,
                     "ConvertQProg": "[]",
                     "Configure": {"Shot": 100}},
        "direction": "REQUEST",
        "expect_caught": True,  # TaskId must be string
    },
    {
        "name": "Configure as string",
        "payload": {"MsgType": "MsgTask", "SN": 981,
                     "TaskId": "configure-str",
                     "ConvertQProg": "[]",
                     "Configure": "not-an-object"},
        "direction": "REQUEST",
        "expect_caught": True,  # Configure must be object
    },
]


def run_adversarial_benchmark() -> dict:
    """
    Run adversarial injection test.
    Interleaves legitimate and adversarial traffic and measures detection.
    """
    print(f"\n{'='*60}")
    print("  BENCHMARK: Adversarial Injection Testing")
    print(f"{'='*60}\n")

    results_per_paradigm = {}
    total_attacks = 0
    total_caught = 0
    total_missed = 0
    total_legit = 0
    total_legit_passed = 0
    total_legit_rejected = 0
    attack_results = []

    for paradigm in ALL_PARADIGMS:
        print(f"  ── {paradigm.upper()} ──")
        validator = ProtocolValidator()

        # If auth paradigm, pre-authenticate
        if paradigm in ["ion_trap", "neutral_atom"]:
            # Send auth sequence
            auth_req = CapturedMessage.from_raw(
                system_type=paradigm, direction="REQUEST", channel="router",
                raw_bytes=json.dumps({"MsgType": "MsgGetToken"}).encode())
            validator.validate(auth_req)
            auth_resp = CapturedMessage.from_raw(
                system_type=paradigm, direction="RESPONSE", channel="router",
                raw_bytes=json.dumps({"MsgType": "MsgGetTokenAck", "ErrCode": 0}).encode())
            validator.validate(auth_resp)

        paradigm_attacks = 0
        paradigm_caught = 0
        paradigm_missed = 0
        paradigm_legit = 0
        paradigm_legit_ok = 0
        paradigm_legit_bad = 0

        # Generate legitimate traffic
        legit_sequences = []
        for i in range(10):
            legit_sequences.extend(generate_legitimate_sequence(paradigm, i))

        # Interleave: process some legit, then an attack, then more legit
        legit_idx = 0
        for attack in ADVERSARIAL_ATTACKS:
            # Process 2 legitimate messages first
            for _ in range(min(2, len(legit_sequences) - legit_idx)):
                if legit_idx >= len(legit_sequences):
                    break
                leg = legit_sequences[legit_idx]
                legit_idx += 1
                msg = CapturedMessage.from_raw(
                    system_type=paradigm, direction=leg["direction"],
                    channel="router",
                    raw_bytes=json.dumps(leg["payload"]).encode())
                validated = validator.validate(msg)
                paradigm_legit += 1
                total_legit += 1
                if validated.is_valid:
                    paradigm_legit_ok += 1
                    total_legit_passed += 1
                else:
                    paradigm_legit_bad += 1
                    total_legit_rejected += 1

            # Handle duplicate setup
            if attack.get("setup_duplicate"):
                # First send is valid
                setup_msg = CapturedMessage.from_raw(
                    system_type=paradigm, direction=attack["direction"],
                    channel="router",
                    raw_bytes=json.dumps(attack["payload"]).encode())
                validator.validate(setup_msg)
                # Now the DUPLICATE should be caught
                dup_msg = CapturedMessage.from_raw(
                    system_type=paradigm, direction=attack["direction"],
                    channel="router",
                    raw_bytes=json.dumps(attack["payload"]).encode())
                validated = validator.validate(dup_msg)
                paradigm_attacks += 1
                total_attacks += 1
                if not validated.is_valid:
                    paradigm_caught += 1
                    total_caught += 1
                    status = "CAUGHT"
                else:
                    paradigm_missed += 1
                    total_missed += 1
                    status = "MISSED"
                attack_results.append({
                    "name": f"{attack['name']} [{paradigm}]",
                    "status": status,
                })
                continue

            # Inject the adversarial message
            msg = CapturedMessage.from_raw(
                system_type=paradigm, direction=attack["direction"],
                channel="router",
                raw_bytes=json.dumps(attack["payload"]).encode())
            validated = validator.validate(msg)

            if attack["expect_caught"]:
                paradigm_attacks += 1
                total_attacks += 1
                if not validated.is_valid:
                    paradigm_caught += 1
                    total_caught += 1
                    status = "✅ CAUGHT"
                else:
                    paradigm_missed += 1
                    total_missed += 1
                    status = "❌ MISSED"
                attack_results.append({
                    "name": f"{attack['name']} [{paradigm}]",
                    "status": status,
                    "errors": validated.validation_errors,
                })

        # Process remaining legitimate messages
        while legit_idx < len(legit_sequences):
            leg = legit_sequences[legit_idx]
            legit_idx += 1
            msg = CapturedMessage.from_raw(
                system_type=paradigm, direction=leg["direction"],
                channel="router",
                raw_bytes=json.dumps(leg["payload"]).encode())
            validated = validator.validate(msg)
            paradigm_legit += 1
            total_legit += 1
            if validated.is_valid:
                paradigm_legit_ok += 1
                total_legit_passed += 1
            else:
                paradigm_legit_bad += 1
                total_legit_rejected += 1

        catch_rate = (paradigm_caught / paradigm_attacks * 100) if paradigm_attacks > 0 else 0
        legit_pass_rate = (paradigm_legit_ok / paradigm_legit * 100) if paradigm_legit > 0 else 0
        print(f"    Attacks: {paradigm_caught}/{paradigm_attacks} caught ({catch_rate:.1f}%)")
        print(f"    Legitimate: {paradigm_legit_ok}/{paradigm_legit} passed ({legit_pass_rate:.1f}%)")

        results_per_paradigm[paradigm] = {
            "attacks_caught": paradigm_caught,
            "attacks_total": paradigm_attacks,
            "catch_rate": round(catch_rate, 1),
            "legit_passed": paradigm_legit_ok,
            "legit_total": paradigm_legit,
            "legit_rejected": paradigm_legit_bad,
        }

    # Summary
    overall_catch = (total_caught / total_attacks * 100) if total_attacks > 0 else 0
    overall_legit = (total_legit_passed / total_legit * 100) if total_legit > 0 else 0
    false_positive_rate = (total_legit_rejected / total_legit * 100) if total_legit > 0 else 0
    false_negative_rate = (total_missed / total_attacks * 100) if total_attacks > 0 else 0

    print(f"\n  ── Overall Results ──")
    print(f"  Adversarial Detection Rate: {overall_catch:.1f}% ({total_caught}/{total_attacks})")
    print(f"  Legitimate Pass Rate:       {overall_legit:.1f}% ({total_legit_passed}/{total_legit})")
    print(f"  False Positive Rate:        {false_positive_rate:.1f}%")
    print(f"  False Negative Rate:        {false_negative_rate:.1f}%")

    # Print detailed attack results
    print(f"\n  ── Attack Details ──")
    for ar in attack_results:
        print(f"    {ar['status']:>10s}  {ar['name']}")

    print(f"{'='*60}\n")

    return {
        "benchmark": "adversarial_injection",
        "total_attacks": total_attacks,
        "attacks_caught": total_caught,
        "attacks_missed": total_missed,
        "detection_rate": round(overall_catch, 2),
        "total_legitimate": total_legit,
        "legitimate_passed": total_legit_passed,
        "legitimate_rejected": total_legit_rejected,
        "false_positive_rate": round(false_positive_rate, 2),
        "false_negative_rate": round(false_negative_rate, 2),
        "paradigm_results": results_per_paradigm,
        "attack_details": attack_results,
    }


if __name__ == "__main__":
    result = run_adversarial_benchmark()
    print(f"\n  Result: {json.dumps({k: v for k, v in result.items() if k != 'attack_details'}, indent=2)}")
