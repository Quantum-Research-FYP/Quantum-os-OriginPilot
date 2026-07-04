"""
PilotProbe Replay Engine
Loads recorded ZMQ requests from the database, replays them to the simulator,
receives replies, and compares the new responses with the original ones.
"""
import sqlite3
import json
import time
import logging
import zmq
from typing import Dict, List, Any, Optional

from config import ProbeConfig, SystemType
from store.models import CapturedMessage

logger = logging.getLogger("pilotprobe.replay_engine")


class ReplayEngine:
    """
    Replays recorded request messages to the quantum simulators to reproduce
    bugs or test regression.
    """

    def __init__(self, db_path: str = "pilotprobe.db"):
        self.db_path = db_path
        self.context = zmq.Context()

    def get_requests(self, system_type: Optional[str] = None, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve recorded REQUEST messages from the DB."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conditions = ["direction = 'REQUEST'"]
            params = []
            if system_type:
                conditions.append("system_type = ?")
                params.append(system_type)
            if task_id:
                conditions.append("task_id = ?")
                params.append(task_id)

            where = f"WHERE {' AND '.join(conditions)}"
            sql = f"""
                SELECT * FROM messages
                {where}
                ORDER BY timestamp ASC
            """
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_recorded_responses(self, request_id: int) -> List[Dict[str, Any]]:
        """
        Find all RESPONSE messages that were originally received for this request
        (matching system type, SN, grouped chronologically by request index).
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            req = conn.execute("SELECT * FROM messages WHERE id = ?", (request_id,)).fetchone()
            if not req:
                return []

            # Find all requests with the same system type and SN
            all_reqs = conn.execute(
                "SELECT id FROM messages WHERE direction = 'REQUEST' AND system_type = ? AND sn = ? ORDER BY id ASC",
                (req["system_type"], req["sn"])
            ).fetchall()
            req_ids = [r["id"] for r in all_reqs]
            
            try:
                req_index = req_ids.index(request_id)
            except ValueError:
                return []

            # Find all responses with the same system type and SN
            all_res = conn.execute(
                "SELECT * FROM messages WHERE direction = 'RESPONSE' AND system_type = ? AND sn = ? ORDER BY id ASC",
                (req["system_type"], req["sn"])
            ).fetchall()
            
            # Group responses chronologically. A new group starts with an "Ack" message type.
            groups = []
            current_group = []
            for res in all_res:
                payload = {}
                try:
                    payload = json.loads(res["raw_payload"])
                except Exception:
                    pass
                msg_type = payload.get("MsgType") or ""
                if not msg_type and "Header" in payload:
                    msg_type = payload["Header"].get("MsgType") or ""

                if msg_type.endswith("Ack") or not msg_type:
                    if current_group:
                        groups.append(current_group)
                    current_group = [dict(res)]
                else:
                    current_group.append(dict(res))
            if current_group:
                groups.append(current_group)

            if req_index < len(groups):
                return groups[req_index]
            return []
        finally:
            conn.close()

    def replay_session(
        self,
        system_type: Optional[str] = None,
        task_id: Optional[str] = None,
        speed: float = 1.0,
        target_host: str = "localhost"
    ) -> List[Dict[str, Any]]:
        """
        Run the replay session.
        - speed: speed multiplier (1.0 = real-time, 0.0 = immediate/no sleep)
        """
        requests = self.get_requests(system_type, task_id)
        if not requests:
            print("[Replay] No requests found matching the criteria.")
            return []

        print(f"[Replay] Loaded {len(requests)} requests for replay.")
        results = []

        # Open sockets to target simulators
        sockets: Dict[str, zmq.Socket] = {}
        try:
            prev_ts = None
            for req in requests:
                sys_type_str = req["system_type"]

                # ── Delay to match original timing ──
                if prev_ts is not None and speed > 0.0:
                    delay = (req["timestamp"] - prev_ts) / speed
                    if delay > 0:
                        time.sleep(min(delay, 5.0))  # Cap delay at 5s to avoid hanging long replays

                prev_ts = req["timestamp"]

                # Get socket for system type (e.g. superconducting -> port 7000)
                if sys_type_str not in sockets:
                    try:
                        sys_type = SystemType(sys_type_str)
                    except ValueError:
                        print(f"[Replay] Unknown system type: {sys_type_str}")
                        continue
                    
                    target_port = ProbeConfig.SIMULATOR_ROUTER_PORTS[sys_type]
                    sock = self.context.socket(zmq.DEALER)
                    
                    # Set a distinct identity for replay client
                    replay_identity = f"pilotprobe-replay-{sys_type_str}".encode("utf-8")
                    sock.setsockopt(zmq.IDENTITY, replay_identity)
                    sock.setsockopt(zmq.RCVTIMEO, 5000)  # 5s receive timeout
                    sock.connect(f"tcp://{target_host}:{target_port}")
                    sockets[sys_type_str] = sock

                sock = sockets[sys_type_str]
                payload_bytes = req["raw_payload"].encode("utf-8")

                print(f"[Replay] Sending {req['msg_type']} (SN={req['sn']}) to {sys_type_str}...")
                
                # Send request to simulator
                sock.send(payload_bytes)
                
                # Wait for response(s)
                replayed_responses = []
                try:
                    # First response: wait up to 5s
                    res_bytes = sock.recv()
                    replayed_responses.append(res_bytes)
                    
                    # Subsequent responses: poll with a short timeout (300ms)
                    # to capture async replies (like MsgTaskResult)
                    poller = zmq.Poller()
                    poller.register(sock, zmq.POLLIN)
                    while True:
                        socks = dict(poller.poll(300))
                        if sock in socks:
                            res_bytes = sock.recv()
                            replayed_responses.append(res_bytes)
                        else:
                            break
                except zmq.Again:
                    if not replayed_responses:
                        print(f"[Replay] ⚠️ Timeout waiting for response to {req['msg_type']}!")

                # Parse replayed messages
                replayed_msgs = []
                for rb in replayed_responses:
                    msg = CapturedMessage.from_raw(
                        system_type=sys_type_str,
                        direction="RESPONSE",
                        channel="router",
                        raw_bytes=rb
                    )
                    replayed_msgs.append(msg)

                # Retrieve recorded responses for comparison
                orig_res_list = self.get_recorded_responses(req["id"])

                # Compare responses
                comparison = self._compare_responses(orig_res_list, replayed_msgs)
                
                results.append({
                    "request_id": req["id"],
                    "msg_type": req["msg_type"],
                    "sn": req["sn"],
                    "system_type": sys_type_str,
                    "original_responses": [o["raw_payload"] for o in orig_res_list],
                    "replay_responses": [r.raw_payload for r in replayed_msgs],
                    "match": comparison["match"],
                    "diff_details": comparison["details"]
                })

        finally:
            for s in sockets.values():
                s.close()
            self.context.term()

        return results

    def _compare_responses(self, orig_list: List[Dict[str, Any]], replayed_list: List[CapturedMessage]) -> Dict[str, Any]:
        """Compare the list of original responses with the list of replayed responses."""
        if len(orig_list) != len(replayed_list):
            return {
                "match": False,
                "details": f"Response count mismatch: original={len(orig_list)}, replayed={len(replayed_list)}"
            }
        
        diffs = []
        for i, (orig, replayed) in enumerate(zip(orig_list, replayed_list)):
            try:
                o_data = json.loads(orig["raw_payload"])
                r_data = json.loads(replayed.raw_payload)
            except (json.JSONDecodeError, TypeError):
                # Fall back to string comparison
                if orig["raw_payload"] != replayed.raw_payload:
                    diffs.append(f"Response #{i} raw string mismatch")
                continue

            # Check fields like ErrCode, MsgType
            for field in ("MsgType", "ErrCode", "ErrInfo", "TaskId", "SN"):
                o_val = o_data.get(field)
                r_val = r_data.get(field)
                
                # Handle Ion Trap / Neutral Atom Header/Body format
                if o_val is None and "Header" in o_data:
                    o_val = o_data["Header"].get(field) or o_data.get("Body", {}).get(field)
                if r_val is None and "Header" in r_data:
                    r_val = r_data["Header"].get(field) or r_data.get("Body", {}).get(field)

                if o_val != r_val:
                    diffs.append(f"Response #{i} {field} changed: original={o_val}, replayed={r_val}")

            # Check special task output values (Data / ProbCount/Key etc) if relevant
            # NOTE: Quantum measurements are probabilistic, so ProbCount might vary slightly unless seed is fixed.
            # We flag ProbCount variation as a info mismatch but not necessarily a failure match.
            o_prob = o_data.get("ProbCount") or o_data.get("Body", {}).get("ProbCount")
            r_prob = r_data.get("ProbCount") or r_data.get("Body", {}).get("ProbCount")
            if o_prob != r_prob:
                diffs.append(f"Response #{i} ProbCount values differ (expected due to quantum randomness)")

        match = len([d for d in diffs if "ProbCount" not in d]) == 0

        return {
            "match": match,
            "details": "; ".join(diffs) if diffs else "Perfect match (excluding quantum randomness)"
        }
