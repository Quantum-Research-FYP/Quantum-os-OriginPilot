"""
PilotProbe Data Models
Dataclass representations of captured ZMQ messages.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import time
import json


@dataclass
class CapturedMessage:
    """A single captured ZMQ message with metadata."""

    timestamp: float                       # Unix timestamp (high resolution)
    system_type: str                       # superconducting, ion_trap, etc.
    direction: str                         # REQUEST, RESPONSE, PUB
    channel: str                           # router, pub
    raw_payload: str                       # Full JSON string
    msg_type: Optional[str] = None         # MsgTask, MsgHeartbeat, etc.
    task_id: Optional[str] = None          # Extracted task ID
    sn: Optional[int] = None              # Sequence number
    parsed_fields: Optional[str] = None    # Key fields as JSON string
    is_valid: bool = True                  # Validation result
    validation_errors: Optional[str] = None  # Validation error details

    @classmethod
    def from_raw(cls, system_type: str, direction: str, channel: str,
                 raw_bytes: bytes) -> "CapturedMessage":
        """
        Create a CapturedMessage by parsing raw ZMQ frame bytes.

        Handles both flat JSON (superconducting/photonic) and
        Header/Body JSON (ion_trap/neutral_atom) message formats.
        """
        ts = time.time()
        try:
            payload_str = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            payload_str = repr(raw_bytes)

        msg_type = None
        task_id = None
        sn = None
        parsed = {}

        try:
            data = json.loads(payload_str)

            # ── Flat structure (superconducting, photonic) ──
            if "MsgType" in data:
                msg_type = data["MsgType"]
                sn = data.get("SN")
                task_id = data.get("TaskId")
                parsed = {
                    k: data[k] for k in ("MsgType", "SN", "TaskId", "ErrCode",
                                         "ErrInfo", "TaskStatus")
                    if k in data
                }

            # ── Header/Body structure (ion_trap, neutral_atom) ──
            elif "Header" in data:
                header = data.get("Header", {})
                body = data.get("Body", {})
                msg_type = header.get("MsgType")
                sn = header.get("SN") or body.get("SN")
                task_id = body.get("TaskId")
                parsed = {
                    "MsgType": msg_type,
                    "SN": sn,
                    "TaskId": task_id,
                    "Authorization": header.get("Authorization"),
                }
                # Include ErrCode from body if present
                if "ErrCode" in body:
                    parsed["ErrCode"] = body["ErrCode"]

            # ── Response formats (may have Data wrapper) ──
            if msg_type and "Data" in data if isinstance(data, dict) else False:
                inner = data["Data"]
                if isinstance(inner, dict):
                    if "status" in inner:
                        parsed["TaskStatus"] = inner["status"]
                    if "TaskId" in inner and not task_id:
                        task_id = inner["TaskId"]

        except (json.JSONDecodeError, TypeError, AttributeError):
            # Non-JSON payload — store raw
            parsed = {"_raw": payload_str[:200]}

        return cls(
            timestamp=ts,
            system_type=system_type,
            direction=direction,
            channel=channel,
            raw_payload=payload_str,
            msg_type=msg_type,
            task_id=task_id,
            sn=sn,
            parsed_fields=json.dumps(parsed, ensure_ascii=False) if parsed else None,
        )

    @classmethod
    def from_pub_frames(cls, system_type: str, frames: list) -> "CapturedMessage":
        """
        Create a CapturedMessage from PUB multipart frames.
        Simulator PUB sends 3 frames: [topic, operation, data_json]
        """
        ts = time.time()

        topic = frames[0].decode("utf-8", errors="replace") if len(frames) > 0 else ""
        operation = frames[1].decode("utf-8", errors="replace") if len(frames) > 1 else ""
        data_raw = frames[2].decode("utf-8", errors="replace") if len(frames) > 2 else ""

        msg_type = None
        task_id = None
        sn = None
        parsed = {"topic": topic, "operation": operation}

        try:
            data = json.loads(data_raw)
            msg_type = data.get("MsgType", operation)
            task_id = data.get("TaskId")
            sn = data.get("SN")
            parsed.update({
                k: data[k] for k in ("MsgType", "SN", "TaskId", "TaskStatus")
                if k in data
            })
        except (json.JSONDecodeError, TypeError):
            parsed["_raw"] = data_raw[:200]

        # Combine all frames into a single payload for storage
        full_payload = json.dumps({
            "topic": topic,
            "operation": operation,
            "data": data_raw,
        }, ensure_ascii=False)

        return cls(
            timestamp=ts,
            system_type=system_type,
            direction="PUB",
            channel="pub",
            raw_payload=full_payload,
            msg_type=msg_type,
            task_id=task_id,
            sn=sn,
            parsed_fields=json.dumps(parsed, ensure_ascii=False) if parsed else None,
        )

    def summary_line(self) -> str:
        """Return a compact one-line summary for CLI display."""
        parts = [self.msg_type or "???"]
        if self.sn is not None:
            parts.append(f"SN={self.sn}")
        if self.task_id:
            parts.append(f"TaskId={self.task_id[:12]}")

        # Extract TaskStatus if present
        if self.parsed_fields:
            try:
                pf = json.loads(self.parsed_fields)
                if "TaskStatus" in pf:
                    parts.append(f"Status={pf['TaskStatus']}")
                if "ErrCode" in pf and pf["ErrCode"] not in (None, 0):
                    parts.append(f"ErrCode={pf['ErrCode']}")
            except (json.JSONDecodeError, TypeError):
                pass

        return "  ".join(parts)
