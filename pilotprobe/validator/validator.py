"""
PilotProbe Protocol Validator
Schema validation + semantic checks (SN pairing, lifecycle, auth, duplicates, timing).
"""
import json
import time
import threading
import logging
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

import jsonschema

from store.models import CapturedMessage
from .schema_registry import SchemaRegistry

logger = logging.getLogger("pilotprobe.validator")

# Valid task status transitions (status code → allowed next codes)
VALID_TRANSITIONS = {
    1: {2, 7, 4},        # PENDING → RUNNING, COMPILING, FAILED
    7: {8, 4},            # COMPILING → COMPILED, FAILED
    8: {2, 4},            # COMPILED → RUNNING, FAILED
    2: {5, 4, 6},         # RUNNING → SUCCESSED, FAILED, RETRY
    6: {1, 2, 4},         # RETRY → PENDING, RUNNING, FAILED
}

SLOW_RESPONSE_THRESHOLD = 5.0  # seconds


class ProtocolValidator:
    """
    Validates captured messages against protocol schemas and semantic rules.

    Thread-safe: called from multiple proxy threads via the capture callback.
    """

    def __init__(self):
        self.registry = SchemaRegistry()
        self._lock = threading.Lock()

        # Semantic state tracking (per system)
        self._pending_requests: Dict[str, Dict[int, float]] = defaultdict(dict)
        self._task_ids_seen: Dict[str, Set[str]] = defaultdict(set)
        self._task_status: Dict[str, Dict[str, int]] = defaultdict(dict)
        self._auth_state: Dict[str, bool] = defaultdict(lambda: False)

        # Counters
        self.total_validated = 0
        self.schema_errors = 0
        self.semantic_warnings = 0
        self.semantic_errors = 0

    def validate(self, msg: CapturedMessage) -> CapturedMessage:
        """
        Validate a captured message. Mutates msg.is_valid and msg.validation_errors.
        Returns the same message for chaining.
        """
        errors: List[str] = []
        warnings: List[str] = []

        with self._lock:
            self.total_validated += 1

            # 1. Schema validation
            schema_errs = self._validate_schema(msg)
            errors.extend(schema_errs)

            # 2. Semantic validation (only for router messages with parseable JSON)
            if msg.channel == "router" and msg.msg_type:
                sem_errs, sem_warns = self._validate_semantics(msg)
                errors.extend(sem_errs)
                warnings.extend(sem_warns)

            # 3. PUB lifecycle validation
            if msg.channel == "pub" and msg.task_id:
                lc_warns = self._validate_lifecycle(msg)
                warnings.extend(lc_warns)

            # Set results
            if errors:
                msg.is_valid = False
                self.schema_errors += len([e for e in errors if "Schema" in e])
                self.semantic_errors += len([e for e in errors if "Schema" not in e])
            if warnings:
                self.semantic_warnings += len(warnings)

            all_issues = []
            if errors:
                all_issues.extend([f"❌ {e}" for e in errors])
            if warnings:
                all_issues.extend([f"⚠️ {w}" for w in warnings])

            if all_issues:
                msg.validation_errors = "; ".join(all_issues)

        return msg

    def _validate_schema(self, msg: CapturedMessage) -> List[str]:
        """Validate message structure against JSON schema."""
        errors = []
        if not msg.msg_type or msg.direction == "PUB":
            return errors

        schema = self.registry.get_schema(msg.system_type, msg.msg_type)
        if not schema:
            return errors  # No schema = skip (don't flag unknown types as errors)

        try:
            payload = json.loads(msg.raw_payload)
            jsonschema.validate(instance=payload, schema=schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Schema: {e.message}")
        except (json.JSONDecodeError, Exception):
            pass

        return errors

    def _validate_semantics(self, msg: CapturedMessage) -> Tuple[List[str], List[str]]:
        """Semantic validation: SN pairing, auth flow, duplicates, timing."""
        errors = []
        warnings = []
        sys = msg.system_type

        # Track request SN → timestamp for response pairing
        # Guard against unhashable SN types (e.g. dict/list from fuzz mutations)
        sn_hashable = msg.sn is not None and isinstance(msg.sn, (int, str, float))
        if msg.direction == "REQUEST" and sn_hashable:
            self._pending_requests[sys][msg.sn] = msg.timestamp

        # Check response timing
        if msg.direction == "RESPONSE" and sn_hashable:
            req_time = self._pending_requests[sys].pop(msg.sn, None)
            if req_time:
                elapsed = msg.timestamp - req_time
                if elapsed > SLOW_RESPONSE_THRESHOLD:
                    warnings.append(f"Slow response: {elapsed:.2f}s (threshold: {SLOW_RESPONSE_THRESHOLD}s)")

        # Auth flow check: ion_trap/neutral_atom must MsgGetToken before MsgTask
        if msg.msg_type == "MsgGetTokenAck" and msg.direction == "RESPONSE":
            try:
                payload = json.loads(msg.raw_payload)
                if payload.get("ErrCode") == 0:
                    self._auth_state[sys] = True
            except (json.JSONDecodeError, Exception):
                pass

        if msg.msg_type == "MsgTask" and msg.direction == "REQUEST":
            if self.registry.requires_auth(sys) and not self._auth_state[sys]:
                warnings.append("No MsgGetToken before MsgTask (auth required)")

            # Duplicate TaskId check (guard against unhashable types from fuzz)
            if msg.task_id and isinstance(msg.task_id, str):
                if msg.task_id in self._task_ids_seen[sys]:
                    errors.append(f"Duplicate TaskId: {msg.task_id[:16]}")
                else:
                    self._task_ids_seen[sys].add(msg.task_id)

        return errors, warnings

    def _validate_lifecycle(self, msg: CapturedMessage) -> List[str]:
        """Validate task status transitions from PUB messages."""
        warnings = []
        if not msg.task_id or not msg.parsed_fields:
            return warnings

        try:
            pf = json.loads(msg.parsed_fields)
            new_status = pf.get("TaskStatus")
            if new_status is None:
                return warnings
        except (json.JSONDecodeError, Exception):
            return warnings

        sys = msg.system_type
        old_status = self._task_status[sys].get(msg.task_id)

        if old_status is not None and old_status in VALID_TRANSITIONS:
            allowed = VALID_TRANSITIONS[old_status]
            if new_status not in allowed:
                warnings.append(
                    f"Invalid transition: status {old_status}→{new_status} "
                    f"(allowed: {sorted(allowed)})"
                )

        self._task_status[sys][msg.task_id] = new_status
        return warnings

    def get_stats(self) -> Dict:
        """Return validation statistics."""
        with self._lock:
            return {
                "total_validated": self.total_validated,
                "schema_errors": self.schema_errors,
                "semantic_warnings": self.semantic_warnings,
                "semantic_errors": self.semantic_errors,
            }
