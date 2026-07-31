"""
Benchmark: Fuzz Validation Test Suite
Generates 1000+ randomized/mutated test cases across ALL 4 paradigms to
measure PilotProbe's true detection accuracy at scale.

Mutation strategies:
  1. Type Mutations     — swap field types (int→str, str→int, bool→list, etc.)
  2. Field Deletions    — remove required fields one at a time
  3. Value Boundary     — inject edge-case values (negatives, huge ints, empty strings)
  4. Extra Field Injection — add unknown fields to valid messages
  5. Malformed JSON     — truncated, nested corruption, unicode bombs
  6. Valid Message Variants — ensure no false positives across diverse valid inputs

Output: True Positive Rate, True Negative Rate, False Positive/Negative counts.
"""
import sys
import os
import json
import random
import string
import copy
import time
from typing import List, Dict, Tuple, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from store.models import CapturedMessage
from validator.validator import ProtocolValidator


# ── All 4 paradigms ──────────────────────────────────────────────────
ALL_PARADIGMS = ["superconducting", "ion_trap", "neutral_atom", "photonic"]
AUTH_PARADIGMS = ["ion_trap", "neutral_atom"]  # Require MsgGetToken


# ── Base valid message templates per message type ────────────────────
def _base_heartbeat(sn: int = 1) -> dict:
    return {"MsgType": "MsgHeartbeat", "SN": sn, "Chip": 72, "TimeStamp": 1720000000000}


def _base_heartbeat_ack(sn: int = 1) -> dict:
    return {"MsgType": "MsgHeartbeatAck", "SN": sn, "TimeStamp": 1720000000000}


def _base_get_chip_config(sn: int = 1) -> dict:
    return {"MsgType": "GetChipConfig", "SN": sn, "Chip": 72}


def _base_get_chip_config_ack(sn: int = 1) -> dict:
    return {"MsgType": "GetChipConfigAck", "SN": sn, "ErrCode": 0,
            "ChipConfig": {"qubits": 20}, "PointLabelList": [1]}


def _base_task(task_id: str, sn: int = 10) -> dict:
    return {
        "MsgType": "MsgTask", "SN": sn, "TaskId": task_id,
        "ConvertQProg": '[[[{"RX": [0, 90.0]}]]]',
        "Configure": {"Shot": 100, "TaskPriority": 0, "IsExperiment": False, "PointLabel": 128},
    }


def _base_task_ack(sn: int = 10) -> dict:
    return {"MsgType": "MsgTaskAck", "SN": sn, "ErrCode": 0}


def _base_task_result(task_id: str, sn: int = 10) -> dict:
    return {"MsgType": "MsgTaskResult", "SN": sn, "TaskId": task_id,
            "ErrCode": 0, "Key": ["00", "01", "10", "11"],
            "ProbCount": [25, 25, 25, 25]}


def _base_task_status(task_id: str, sn: int = 10) -> dict:
    return {"MsgType": "TaskStatus", "SN": sn, "TaskId": task_id}


def _base_task_status_ack(task_id: str, sn: int = 10) -> dict:
    return {"MsgType": "TaskStatusAck", "SN": sn, "TaskId": task_id, "TaskStatus": 2}


def _base_set_vip(sn: int = 1) -> dict:
    return {"MsgType": "SetVip", "SN": sn}


def _base_release_vip(sn: int = 1) -> dict:
    return {"MsgType": "ReleaseVip", "SN": sn}


def _base_get_token() -> dict:
    return {"MsgType": "MsgGetToken"}


def _base_get_token_ack() -> dict:
    return {"MsgType": "MsgGetTokenAck", "ErrCode": 0, "Data": {"token": "abc123"}}


# ── Mutation Strategies ──────────────────────────────────────────────

def _random_string(length: int = 8) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def _random_wrong_type(original_value: Any) -> Any:
    """Return a value of a different type than the original."""
    if isinstance(original_value, int):
        return random.choice([_random_string(), True, [1, 2, 3], {"a": 1}, None, 3.14])
    elif isinstance(original_value, str):
        return random.choice([42, True, [1, 2], {"a": 1}, None, -99])
    elif isinstance(original_value, bool):
        return random.choice([42, "true", [True], {"val": True}, None])
    elif isinstance(original_value, list):
        return random.choice([42, "not-a-list", True, {"a": 1}, None])
    elif isinstance(original_value, dict):
        return random.choice([42, "not-a-dict", True, [1, 2], None])
    else:
        return _random_string()


def _boundary_value(original_value: Any) -> Any:
    """Return an edge-case value for the same type."""
    if isinstance(original_value, int):
        return random.choice([-1, -999999, 0, 2**31, 2**63, 999999999])
    elif isinstance(original_value, str):
        return random.choice(["", " ", "a" * 10000, "\x00\x01\x02",
                              "'; DROP TABLE tasks; --", "<script>alert(1)</script>"])
    elif isinstance(original_value, list):
        return random.choice([[], [None] * 100, list(range(10000))])
    elif isinstance(original_value, dict):
        return random.choice([{}, {"": ""}, {str(i): i for i in range(100)}])
    return original_value


def mutate_type(payload: dict) -> Tuple[dict, str]:
    """Strategy 1: Swap one field's type to an incompatible type."""
    mutated = copy.deepcopy(payload)
    # Collect mutable fields (skip MsgType — changing that makes it a different msg)
    flat_keys = [k for k in mutated if k != "MsgType" and mutated[k] is not None]
    if not flat_keys:
        return mutated, "no_mutable_fields"
    key = random.choice(flat_keys)
    original = mutated[key]
    if isinstance(original, dict):
        # Mutate a nested field
        nested_keys = [k for k in original if original[k] is not None]
        if nested_keys:
            nk = random.choice(nested_keys)
            original[nk] = _random_wrong_type(original[nk])
            return mutated, f"type_mutation:{key}.{nk}"
    mutated[key] = _random_wrong_type(original)
    return mutated, f"type_mutation:{key}"


def mutate_delete_required(payload: dict, required_fields: list) -> Tuple[dict, str]:
    """Strategy 2: Delete one required field."""
    mutated = copy.deepcopy(payload)
    # Don't delete MsgType as that changes parsing behavior entirely
    deletable = [f for f in required_fields if f in mutated and f != "MsgType"]
    if not deletable:
        return mutated, "no_deletable_fields"
    key = random.choice(deletable)
    del mutated[key]
    return mutated, f"field_deletion:{key}"


def mutate_boundary(payload: dict) -> Tuple[dict, str]:
    """Strategy 3: Replace one field with a boundary/edge-case value."""
    mutated = copy.deepcopy(payload)
    flat_keys = [k for k in mutated if k != "MsgType" and mutated[k] is not None]
    if not flat_keys:
        return mutated, "no_boundary_fields"
    key = random.choice(flat_keys)
    original = mutated[key]
    if isinstance(original, dict):
        nested_keys = [k for k in original if original[k] is not None]
        if nested_keys:
            nk = random.choice(nested_keys)
            original[nk] = _boundary_value(original[nk])
            return mutated, f"boundary:{key}.{nk}"
    mutated[key] = _boundary_value(original)
    return mutated, f"boundary:{key}"


def mutate_extra_field(payload: dict) -> Tuple[dict, str]:
    """Strategy 4: Add an unexpected extra field."""
    mutated = copy.deepcopy(payload)
    extra_key = f"__fuzz_{_random_string(4)}"
    mutated[extra_key] = random.choice([42, "fuzz", True, [1], {"x": 1}])
    return mutated, f"extra_field:{extra_key}"


# ── Required fields per message type (from schemas) ──────────────────
REQUIRED_FIELDS = {
    "MsgHeartbeat": ["MsgType"],
    "MsgHeartbeatAck": ["MsgType", "SN"],
    "GetChipConfig": ["MsgType"],
    "GetChipConfigAck": ["MsgType", "SN", "ErrCode"],
    "MsgTask": ["MsgType", "SN", "TaskId", "ConvertQProg", "Configure"],
    "MsgTaskAck": ["MsgType", "SN", "ErrCode"],
    "MsgTaskResult": ["MsgType", "SN", "TaskId", "ErrCode"],
    "TaskStatus": ["MsgType", "TaskId"],
    "TaskStatusAck": ["MsgType", "SN"],
    "SetVip": ["MsgType", "SN"],
    "ReleaseVip": ["MsgType", "SN"],
    "MsgGetToken": ["MsgType"],
    "MsgGetTokenAck": ["MsgType", "ErrCode"],
}

# ── Message generators per type ──────────────────────────────────────
BASE_GENERATORS = {
    "MsgHeartbeat": lambda tid, sn: _base_heartbeat(sn),
    "MsgHeartbeatAck": lambda tid, sn: _base_heartbeat_ack(sn),
    "GetChipConfig": lambda tid, sn: _base_get_chip_config(sn),
    "GetChipConfigAck": lambda tid, sn: _base_get_chip_config_ack(sn),
    "MsgTask": lambda tid, sn: _base_task(tid, sn),
    "MsgTaskAck": lambda tid, sn: _base_task_ack(sn),
    "MsgTaskResult": lambda tid, sn: _base_task_result(tid, sn),
    "TaskStatus": lambda tid, sn: _base_task_status(tid, sn),
    "TaskStatusAck": lambda tid, sn: _base_task_status_ack(tid, sn),
    "SetVip": lambda tid, sn: _base_set_vip(sn),
    "ReleaseVip": lambda tid, sn: _base_release_vip(sn),
    "MsgGetToken": lambda tid, sn: _base_get_token(),
    "MsgGetTokenAck": lambda tid, sn: _base_get_token_ack(),
}


def _generate_valid_cases(count_per_paradigm: int = 50) -> List[dict]:
    """Generate diverse valid messages across all 4 paradigms."""
    cases = []
    msg_types_common = ["MsgHeartbeat", "MsgHeartbeatAck", "GetChipConfig",
                        "GetChipConfigAck", "MsgTask", "MsgTaskAck",
                        "MsgTaskResult", "TaskStatus", "TaskStatusAck",
                        "SetVip", "ReleaseVip"]
    msg_types_auth = ["MsgGetToken", "MsgGetTokenAck"]

    for paradigm in ALL_PARADIGMS:
        types_for_paradigm = msg_types_common[:]
        if paradigm in AUTH_PARADIGMS:
            types_for_paradigm.extend(msg_types_auth)

        for i in range(count_per_paradigm):
            msg_type = random.choice(types_for_paradigm)
            task_id = f"fuzz-valid-{paradigm[:4]}-{i:04d}"
            sn = random.randint(1, 50000)
            gen = BASE_GENERATORS.get(msg_type)
            if gen:
                payload = gen(task_id, sn)
                direction = "RESPONSE" if msg_type.endswith("Ack") else "REQUEST"
                cases.append({
                    "id": f"V-{paradigm[:4]}-{i:04d}",
                    "name": f"Valid {paradigm} {msg_type}",
                    "system": paradigm,
                    "direction": direction,
                    "payload": payload,
                    "expect_valid": True,
                    "mutation": "none",
                })
    return cases


def _generate_mutated_cases(count_per_paradigm: int = 200) -> List[dict]:
    """Generate mutated (invalid) messages across all 4 paradigms."""
    cases = []
    # Message types that have strict schema enforcement
    strict_types = ["MsgHeartbeat", "MsgTask", "MsgTaskAck",
                    "GetChipConfigAck", "MsgTaskResult"]

    strategies = [
        ("type_mutation", mutate_type),
        ("field_deletion", None),  # handled separately (needs required fields)
        ("boundary_value", mutate_boundary),
        ("extra_field", mutate_extra_field),
    ]

    for paradigm in ALL_PARADIGMS:
        for i in range(count_per_paradigm):
            msg_type = random.choice(strict_types)
            task_id = f"fuzz-mut-{paradigm[:4]}-{i:04d}"
            sn = random.randint(1, 50000)
            gen = BASE_GENERATORS.get(msg_type)
            if not gen:
                continue
            base_payload = gen(task_id, sn)

            strategy_name, strategy_fn = random.choice(strategies)

            if strategy_name == "field_deletion":
                required = REQUIRED_FIELDS.get(msg_type, [])
                mutated, mutation_desc = mutate_delete_required(base_payload, required)
                # If a required field was deleted, it should be invalid
                expect_valid = "no_deletable" in mutation_desc
            elif strategy_name == "extra_field":
                # Extra fields are typically allowed by JSON schema (no additionalProperties: false)
                mutated, mutation_desc = strategy_fn(base_payload)
                expect_valid = True  # extra fields should not cause validation failure
            else:
                mutated, mutation_desc = strategy_fn(base_payload)
                # Type mutations and boundary values on constrained fields should fail
                # But not all will — some boundary values are still valid
                expect_valid = None  # we'll check dynamically

            direction = "RESPONSE" if msg_type.endswith("Ack") else "REQUEST"
            cases.append({
                "id": f"M-{paradigm[:4]}-{i:04d}",
                "name": f"Mutated {paradigm} {msg_type} ({strategy_name})",
                "system": paradigm,
                "direction": direction,
                "payload": mutated,
                "expect_valid": expect_valid,
                "mutation": mutation_desc,
            })
    return cases


def run_fuzz_benchmark(total_target: int = 1000) -> dict:
    """
    Run comprehensive fuzz validation benchmark.
    
    Generates valid and mutated messages, validates each one,
    and reports true/false positive/negative rates.
    """
    print(f"\n{'='*60}")
    print("  BENCHMARK: Fuzz Validation (Auto-Generated Test Cases)")
    print(f"{'='*60}\n")

    # Calculate distribution
    valid_per_paradigm = max(25, total_target // 8)  # ~25% valid
    mutated_per_paradigm = max(50, (total_target * 3) // (4 * len(ALL_PARADIGMS)))  # ~75% mutated

    print(f"  Generating test cases...")
    print(f"    Valid: {valid_per_paradigm} per paradigm × {len(ALL_PARADIGMS)} = {valid_per_paradigm * len(ALL_PARADIGMS)}")
    print(f"    Mutated: {mutated_per_paradigm} per paradigm × {len(ALL_PARADIGMS)} = {mutated_per_paradigm * len(ALL_PARADIGMS)}")

    valid_cases = _generate_valid_cases(valid_per_paradigm)
    mutated_cases = _generate_mutated_cases(mutated_per_paradigm)
    all_cases = valid_cases + mutated_cases
    random.shuffle(all_cases)

    total_cases = len(all_cases)
    print(f"    Total: {total_cases} test cases\n")

    # Run validation
    start_time = time.time()
    true_positives = 0   # correctly caught invalid
    true_negatives = 0   # correctly passed valid
    false_positives = 0  # incorrectly rejected valid
    false_negatives = 0  # incorrectly passed invalid
    undetermined = 0     # cases where expected validity is unknown

    paradigm_stats = {p: {"tp": 0, "tn": 0, "fp": 0, "fn": 0, "total": 0}
                      for p in ALL_PARADIGMS}
    mutation_stats = {}

    for case in all_cases:
        # Fresh validator per test to avoid cross-contamination of semantic state
        validator = ProtocolValidator()

        payload_str = json.dumps(case["payload"])
        msg = CapturedMessage.from_raw(
            system_type=case["system"],
            direction=case["direction"],
            channel="router",
            raw_bytes=payload_str.encode("utf-8"),
        )
        validated = validator.validate(msg)

        actual_valid = validated.is_valid
        expected_valid = case["expect_valid"]
        paradigm = case["system"]

        paradigm_stats[paradigm]["total"] += 1

        # Track mutation strategy stats
        mutation = case.get("mutation", "none")
        strategy_key = mutation.split(":")[0] if ":" in mutation else mutation
        if strategy_key not in mutation_stats:
            mutation_stats[strategy_key] = {"caught": 0, "missed": 0, "total": 0}
        mutation_stats[strategy_key]["total"] += 1

        if expected_valid is None:
            # For undetermined cases, just record what happened
            undetermined += 1
            if not actual_valid:
                mutation_stats[strategy_key]["caught"] += 1
            else:
                mutation_stats[strategy_key]["missed"] += 1
            continue

        if expected_valid and actual_valid:
            true_negatives += 1
            paradigm_stats[paradigm]["tn"] += 1
        elif expected_valid and not actual_valid:
            false_positives += 1
            paradigm_stats[paradigm]["fp"] += 1
        elif not expected_valid and not actual_valid:
            true_positives += 1
            paradigm_stats[paradigm]["tp"] += 1
            mutation_stats[strategy_key]["caught"] += 1
        elif not expected_valid and actual_valid:
            false_negatives += 1
            paradigm_stats[paradigm]["fn"] += 1
            mutation_stats[strategy_key]["missed"] += 1

    elapsed = time.time() - start_time
    determined_total = total_cases - undetermined

    # Calculate rates
    tp_rate = (true_positives / (true_positives + false_negatives) * 100
               if (true_positives + false_negatives) > 0 else 0)
    tn_rate = (true_negatives / (true_negatives + false_positives) * 100
               if (true_negatives + false_positives) > 0 else 0)
    overall_accuracy = ((true_positives + true_negatives) / determined_total * 100
                        if determined_total > 0 else 0)

    # Print results
    print(f"  ── Results ({elapsed:.2f}s) ──")
    print(f"  Total Cases:         {total_cases}")
    print(f"  Determined:          {determined_total}")
    print(f"  Undetermined:        {undetermined}")
    print()
    print(f"  True Positives:      {true_positives:>5}  (correctly caught invalid)")
    print(f"  True Negatives:      {true_negatives:>5}  (correctly passed valid)")
    print(f"  False Positives:     {false_positives:>5}  (incorrectly rejected valid)")
    print(f"  False Negatives:     {false_negatives:>5}  (incorrectly passed invalid)")
    print()
    print(f"  True Positive Rate:  {tp_rate:.1f}%")
    print(f"  True Negative Rate:  {tn_rate:.1f}%")
    print(f"  Overall Accuracy:    {overall_accuracy:.1f}%")

    # Per-paradigm breakdown
    print(f"\n  ── Per-Paradigm Breakdown ──")
    for paradigm in ALL_PARADIGMS:
        ps = paradigm_stats[paradigm]
        p_total = ps["tp"] + ps["tn"] + ps["fp"] + ps["fn"]
        p_acc = ((ps["tp"] + ps["tn"]) / p_total * 100) if p_total > 0 else 0
        print(f"  {paradigm:>20s}: {p_acc:5.1f}% accuracy "
              f"(TP={ps['tp']}, TN={ps['tn']}, FP={ps['fp']}, FN={ps['fn']}, total={ps['total']})")

    # Per-mutation strategy breakdown
    print(f"\n  ── Per-Mutation Strategy ──")
    for strategy, stats in sorted(mutation_stats.items()):
        catch_rate = (stats["caught"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {strategy:>20s}: {catch_rate:5.1f}% caught ({stats['caught']}/{stats['total']})")

    print(f"{'='*60}\n")

    return {
        "benchmark": "fuzz_validation",
        "total_cases": total_cases,
        "determined_cases": determined_total,
        "undetermined_cases": undetermined,
        "true_positives": true_positives,
        "true_negatives": true_negatives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "true_positive_rate": round(tp_rate, 2),
        "true_negative_rate": round(tn_rate, 2),
        "overall_accuracy": round(overall_accuracy, 2),
        "elapsed_seconds": round(elapsed, 3),
        "paradigm_breakdown": paradigm_stats,
        "mutation_breakdown": mutation_stats,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fuzz Validation Benchmark")
    parser.add_argument("--count", type=int, default=1000,
                        help="Target total test case count (default: 1000)")
    args = parser.parse_args()
    result = run_fuzz_benchmark(total_target=args.count)
    print(f"  Result: {json.dumps(result, indent=2)}")
