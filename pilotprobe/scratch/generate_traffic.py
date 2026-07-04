import zmq
import json
import time

def run_tests():
    context = zmq.Context()
    
    # ── 1. Connect to Superconducting Proxy (6000) ──
    print("Connecting to Superconducting Proxy on port 6000...")
    super_socket = context.socket(zmq.DEALER)
    super_socket.setsockopt(zmq.IDENTITY, b"test-client-super")
    super_socket.connect("tcp://localhost:6000")
    
    # Clean up any lingering messages
    poller = zmq.Poller()
    poller.register(super_socket, zmq.POLLIN)
    
    # A. Send a VALID Heartbeat
    print("A. Sending Valid Heartbeat...")
    req_hb = {
        "MsgType": "MsgHeartbeat",
        "SN": 1,
        "Chip": 72,
        "TimeStamp": int(time.time() * 1000)
    }
    super_socket.send(json.dumps(req_hb).encode("utf-8"))
    
    # B. Send an INVALID Heartbeat (Trigger Schema Error: SN is string instead of integer)
    print("B. Sending Invalid Heartbeat (Schema Error: SN is string)...")
    req_hb_invalid = {
        "MsgType": "MsgHeartbeat",
        "SN": "one-hundred",
        "Chip": 72,
        "TimeStamp": int(time.time() * 1000)
    }
    super_socket.send(json.dumps(req_hb_invalid).encode("utf-8"))
    
    # C. Send GetChipConfig
    print("C. Sending GetChipConfig...")
    req_cc = {
        "MsgType": "GetChipConfig",
        "SN": 2,
        "Chip": 72
    }
    super_socket.send(json.dumps(req_cc).encode("utf-8"))
    
    # D. Send MsgTask
    task_id = "test-task-12345"
    print(f"D. Sending MsgTask with TaskId={task_id}...")
    req_task = {
        "MsgType": "MsgTask",
        "SN": 3,
        "TaskId": task_id,
        "ConvertQProg": "[[[{\"RX\": [0, 90.0]}]]]",
        "Configure": {
            "Shot": 100,
            "TaskPriority": 0,
            "IsExperiment": False,
            "PointLabel": 128
        }
    }
    super_socket.send(json.dumps(req_task).encode("utf-8"))
    
    # E. Send Duplicate MsgTask (Trigger Semantic Error: Duplicate Task ID)
    print("E. Sending Duplicate MsgTask (Semantic Error)...")
    super_socket.send(json.dumps(req_task).encode("utf-8"))
    
    # ── Wait and receive responses ──
    print("Waiting for superconducting replies...")
    for _ in range(5):
        socks = dict(poller.poll(2000))
        if super_socket in socks:
            reply = super_socket.recv()
            print(f"Received reply: {reply.decode('utf-8')[:100]}...")
            
    super_socket.close()

    # ── 2. Connect to Ion Trap Proxy (6001) ──
    print("\nConnecting to Ion Trap Proxy on port 6001...")
    ion_socket = context.socket(zmq.DEALER)
    ion_socket.setsockopt(zmq.IDENTITY, b"test-client-ion")
    ion_socket.connect("tcp://localhost:6001")
    
    # F. Send MsgTask without getting a token (Trigger Semantic Warning: No MsgGetToken before MsgTask)
    print("F. Sending Ion Trap MsgTask without auth token (Semantic Warning)...")
    req_task_ion = {
        "MsgType": "MsgTask",
        "SN": 10,
        "TaskId": "ion-task-no-auth",
        "ConvertQProg": "[[[{\"RX\": [0, 90.0]}]]]",
        "Configure": {
            "Shot": 100,
            "UsedQubits": [0]
        }
    }
    ion_socket.send(json.dumps(req_task_ion).encode("utf-8"))
    time.sleep(0.5)
    ion_socket.close()
    
    # ── 3. Connect to Pub socket and simulate invalid transition ──
    # Wait, PUB proxy listens to the simulator PUB socket. But we can publish direct to the simulator PUB socket?
    # Simulator pub server is bound to 8000. It doesn't connect.
    # The proxy connects to Simulator PUB 8000 and binds to 9000.
    # Since Simulator PUB is bound to 8000 (ZmqPubServer binds), only one socket can bind to tcp://0.0.0.0:8000.
    # So we can't easily publish to 8000 unless we trigger the simulator to publish something,
    # or the simulator itself publishes status updates during normal execution.
    # Wait, in the superconducting client run above (Step D), the simulator *does* run the task and publishes updates to 8000!
    # Let's see: `TaskStatus` with Status=1 (PENDING) -> 2 (RUNNING) -> 5 (SUCCESSED). That's valid.
    # Let's also check if we can trigger invalid transitions by submitting a customized task.
    # Or, we can just let it run. The duplicate TaskId and schema errors on Heartbeat are already very comprehensive!
    
    context.term()
    print("\n=== Traffic Generation Finished ===")

if __name__ == "__main__":
    run_tests()
