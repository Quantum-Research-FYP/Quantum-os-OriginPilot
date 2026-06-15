"""
Test client for quantum simulation ZMQ server
"""
import json
import time
import uuid
import zmq
import argparse
from typing import Dict, Any


class QuantumTestClient:
    """Test client for quantum simulation server"""
    
    def __init__(self, host: str = "localhost", port: int = 7000, timeout: int = 5000):
        """
        Initialize test client
        
        Args:
            host: Server host address
            port: Server port
            timeout: Socket timeout in milliseconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.context = None
        self.socket = None
        self.sn_counter = 0
    
    def connect(self):
        """Connect to ZMQ server"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.RCVTIMEO, self.timeout)
        self.socket.setsockopt(zmq.LINGER, 0)
        
        addr = f"tcp://{self.host}:{self.port}"
        print(f"Connecting to {addr}...")
        self.socket.connect(addr)
        print(f"Connected to {addr}")
    
    def disconnect(self):
        """Disconnect from server"""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        print("Disconnected from server")
    
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send request and receive response
        
        Args:
            request: Request dictionary
            
        Returns:
            Response dictionary
        """
        self.sn_counter += 1
        request['SN'] = self.sn_counter
        
        request_str = json.dumps(request)
        print(f"\n[Request] {request_str[:200]}...")
        
        # Send request
        self.socket.send_string(request_str)
        
        # Receive response
        try:
            response_str = self.socket.recv_string()
            response = json.loads(response_str)
            print(f"[Response] {json.dumps(response, indent=2, ensure_ascii=False)}")
            return response
        except zmq.Again:
            print("[Error] Request timeout")
            return {'ErrCode': -1, 'ErrInfo': 'Timeout'}
    
    def test_heartbeat(self):
        """Test heartbeat message"""
        print("\n" + "="*60)
        print("Testing Heartbeat")
        print("="*60)
        
        request = {
            "MsgType": "MsgHeartbeat",
            "Chip": 72,
            "TimeStamp": int(time.time() * 1000)
        }
        
        return self.send_request(request)
    
    def test_get_chip_config(self):
        """Test get chip configuration"""
        print("\n" + "="*60)
        print("Testing Get Chip Config")
        print("="*60)
        
        request = {
            "MsgType": "GetChipConfig",
            "Chip": 72
        }
        
        return self.send_request(request)
    
    def test_submit_task(self, shots: int = 1000):
        """Test task submission"""
        print("\n" + "="*60)
        print("Testing Task Submission")
        print("="*60)
        
        task_id = str(uuid.uuid4())
        
        # Different task formats for different systems
        if self.port == 7002:  # Neutral Atom
            task_qasm = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[5];
creg c[5];
rx (1.570796) q[0];
measure q[0] -> c[0];"""
            
            request = {
                "Header": {
                    "MsgType": "MsgTask",
                    "Version": "1.0",
                    "Authorization": "test_token"
                },
                "Body": {
                    "TaskId": task_id,
                    "Task": task_qasm,
                    "Mode": "line",
                    "Type": "",
                    "repeatTime": shots,
                    "quantumNum": 5
                }
            }
        elif self.port in [7001]:  # Ion Trap
            request = {
                "Header": {
                    "MsgType": "MsgTask",
                    "Version": "1.0",
                    "Authorization": "test_token"
                },
                "Body": {
                    "TaskId": task_id,
                    "ConvertQProg": json.dumps([
                        [
                            [
                                {"RPhi": [0, 0.0, 180.0, 0]},
                                {"RPhi": [1, 270.0, 90.0, 0]},
                                {"Measure": [[1, 0], 30]}
                            ]
                        ]
                    ]),
                    "Configure": {
                        "IsSrcResult": False,
                        "Shot": shots,
                        "IsFidelityMat": False,
                        "IsProbCount": True,
                        "IsExperiment": False,
                        "UsedQubits": [[0, 1]]
                    }
                }
            }
        else:  # Superconducting and Photonic
            request = {
                "MsgType": "MsgTask",
                "TaskId": task_id,
                "ConvertQProg": json.dumps([
                    [
                        [{"RX": [0, 90.0]}, {"RY": [0, 45.0]}, {"Measure": [[0]]}]
                    ]
                ]),
                "Configure": {
                    "Shot": shots,
                    "TaskPriority": 0,
                    "IsExperiment": False,
                    "PointLabel": 128
                }
            }
        
        # Submit task and get acknowledgment
        ack = self.send_request(request)
        
        if ack.get('ErrCode') == 0:
            print(f"\nTask submitted successfully!")
            print(f"Task ID: {task_id}")
            print(f"Waiting for task completion...")
            
            # Wait for result
            time.sleep(2)  # Wait for task to complete
            
            # Query task status
            print("\nQuerying task status...")
            status_request = {
                "MsgType": "TaskStatus",
                "TaskId": task_id
            }
            if self.port in [7001, 7002]:
                status_request = {
                    "Header": {
                        "MsgType": "TaskStatus",
                        "Version": "1.0",
                        "Authorization": "test_token"
                    },
                    "Body": {
                        "TaskId": task_id
                    }
                }
            
            status = self.send_request(status_request)
            print(f"Task Status: {status.get('TaskStatus', status.get('Data', {}).get('status', 'Unknown'))}")
        
        return ack
    
    def test_get_update_time(self):
        """Test get update time"""
        print("\n" + "="*60)
        print("Testing Get Update Time")
        print("="*60)
        
        request = {
            "MsgType": "GetUpdateTime"
        }
        if self.port in [7001, 7002]:
            request = {
                "Header": {
                    "MsgType": "GetUpdateTime",
                    "Version": "1.0",
                    "Authorization": "test_token"
                },
                "Body": {}
            }
        
        return self.send_request(request)
    
    def test_get_rb_data(self):
        """Test get RB data"""
        print("\n" + "="*60)
        print("Testing Get RB Data")
        print("="*60)
        
        request = {
            "MsgType": "GetRBData",
            "Chip": 72
        }
        if self.port in [7001, 7002]:
            request = {
                "Header": {
                    "MsgType": "GetRBData",
                    "Version": "1.0",
                    "Authorization": "test_token"
                },
                "Body": {
                    "Chip": 72
                }
            }
        
        return self.send_request(request)
    
    def test_get_token(self):
        """Test get token (Ion Trap and Neutral Atom only)"""
        if self.port not in [7001, 7002]:
            print("\n[Info] Token authentication not required for this system")
            return None
        
        print("\n" + "="*60)
        print("Testing Get Token")
        print("="*60)
        
        request = {
            "Header": {
                "MsgType": "MsgGetToken",
                "Version": "1.0"
            },
            "Body": {
                "APPId": "test_app",
                "APIKey": "test_key_123456",
                "APISecret": "test_secret_123456"
            }
        }
        
        return self.send_request(request)
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("Starting Test Suite")
        print("="*60)
        print(f"Server: {self.host}:{self.port}")
        print(f"Timeout: {self.timeout}ms")
        print("="*60)
        
        try:
            # Test heartbeat
            self.test_heartbeat()
            time.sleep(0.5)
            
            # Test get chip config
            self.test_get_chip_config()
            time.sleep(0.5)
            
            # Test get token (for Ion Trap and Neutral Atom)
            if self.port in [7001, 7002]:
                self.test_get_token()
                time.sleep(0.5)
            
            # Test get update time
            self.test_get_update_time()
            time.sleep(0.5)
            
            # Test get RB data
            self.test_get_rb_data()
            time.sleep(0.5)
            
            # Test task submission
            self.test_submit_task(shots=100)
            
            print("\n" + "="*60)
            print("Test Suite Completed Successfully!")
            print("="*60)
            
        except KeyboardInterrupt:
            print("\n\nTests interrupted by user")
        except Exception as e:
            print(f"\n[Error] Test failed: {e}")
            import traceback
            traceback.print_exc()


def get_system_name(port: int) -> str:
    """Get system name from port"""
    port_map = {
        7000: "Superconducting (超导)",
        7001: "Ion Trap (离子阱)",
        7002: "Neutral Atom (中性原子)",
        7003: "Photonic (光量子)"
    }
    return port_map.get(port, f"Port {port}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Test client for quantum simulation ZMQ server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test superconducting server
  python test_client.py --port 7000
  
  # Test ion trap server
  python test_client.py --port 7001
  
  # Test all servers
  python test_client.py --all
  
  # Test with custom host
  python test_client.py --port 7000 --host 192.168.1.100
        """
    )
    
    parser.add_argument(
        '--port',
        type=int,
        choices=[7000, 7001, 7002, 7003],
        help='Server port to test'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Test all servers'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='localhost',
        help='Server host address (default: localhost)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=5000,
        help='Socket timeout in milliseconds (default: 5000)'
    )
    
    args = parser.parse_args()
    
    if args.all:
        # Test all servers
        ports = [7000, 7001, 7002, 7003]
        for port in ports:
            print(f"\n\n{'#'*60}")
            print(f"# Testing {get_system_name(port)}")
            print(f"{'#'*60}")
            
            client = QuantumTestClient(args.host, port, args.timeout)
            try:
                client.connect()
                client.run_all_tests()
                client.disconnect()
            except Exception as e:
                print(f"[Error] Failed to test {get_system_name(port)}: {e}")
            
            time.sleep(1)  # Delay between tests
    elif args.port:
        # Test single server
        print(f"\nTesting {get_system_name(args.port)}")
        client = QuantumTestClient(args.host, args.port, args.timeout)
        try:
            client.connect()
            client.run_all_tests()
            client.disconnect()
        except Exception as e:
            print(f"[Error] Failed to test: {e}")
            return 1
    else:
        # No port specified
        print("Error: Please specify --port or --all")
        print("Use --help for more information")
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
