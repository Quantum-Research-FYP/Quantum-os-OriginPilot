"""
ZMQ Router Server for quantum simulation
"""
import json
import os
import time
import threading
import zmq
import logging
from typing import Optional, Dict, Any
from queue import Queue, Empty
from config import (
    QuantumSystemType, ServerConfig, ErrorCode, TaskStatus
)
from task_manager import TaskManager
from protocol_adapters import (
    SuperconductingAdapter, IonTrapAdapter, 
    NeutralAtomAdapter, PhotonicAdapter
)
from zmq_pub_server import ZmqPubServer
from chip_config_loader import ChipConfigLoader


class ZmqRouterServer:
    """ZMQ Router server for handling quantum simulation requests"""
    
    def __init__(self, system_type: QuantumSystemType):
        """
        Initialize ZMQ Router server
        
        Args:
            system_type: Type of quantum system to simulate
        """
        self.system_type = system_type
        self.port = ServerConfig.ROUTER_PORTS[system_type]
        self.context = zmq.Context()
        self.socket = None
        self.running = False
        
        # Initialize task manager
        self.task_manager = TaskManager(system_type.value)
        
        # Initialize queues
        self.request_queue = Queue()   # Queue for incoming requests
        self.reply_queue = Queue()     # Queue for outgoing replies
        
        # Initialize Pub server for status updates
        self.pub_server = ZmqPubServer(system_type)
        
        # Initialize chip config loader
        self.chip_config_loader = ChipConfigLoader()
        
        # Initialize protocol adapter based on system type
        if system_type == QuantumSystemType.SUPERCONDUCTING:
            self.adapter = SuperconductingAdapter()
        elif system_type == QuantumSystemType.ION_TRAP:
            self.adapter = IonTrapAdapter()
        elif system_type == QuantumSystemType.NEUTRAL_ATOM:
            self.adapter = NeutralAtomAdapter()
        elif system_type == QuantumSystemType.PHOTONIC:
            self.adapter = PhotonicAdapter()
        else:
            raise ValueError(f"Unknown system type: {system_type}")
        
        # Set default chip ID for each system type
        self.default_chip_id = {
            QuantumSystemType.SUPERCONDUCTING: "72",
            QuantumSystemType.ION_TRAP: "IonTrap",
            QuantumSystemType.NEUTRAL_ATOM: "HanYuan_01",
            QuantumSystemType.PHOTONIC: "PQPUMESH8"
        }[system_type]
        
        # Token storage for Ion Trap and Neutral Atom
        self.access_tokens = {}
        self.refresh_tokens = {}
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        os.makedirs('log', exist_ok=True)
        logging.basicConfig(
            level=getattr(logging, ServerConfig.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(ServerConfig.LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(f"ZmqRouter-{self.system_type.value}")
    
    def start(self):
        """Start the ZMQ Router server"""
        try:
            # Start Pub server first
            self.pub_server.start()
            
            # Create ROUTER socket
            self.socket = self.context.socket(zmq.ROUTER)
            self.socket.setsockopt(zmq.RCVTIMEO, ServerConfig.TIMEOUT)
            self.socket.setsockopt(zmq.SNDTIMEO, ServerConfig.TIMEOUT)
            self.socket.setsockopt(zmq.RCVHWM, ServerConfig.HWM)
            self.socket.setsockopt(zmq.ROUTER_MANDATORY, 1)
            
            # Bind to address
            bind_addr = f"tcp://{ServerConfig.BIND_ADDRESS}:{self.port}"
            self.socket.bind(bind_addr)
            self.logger.info(f"Server bound to {bind_addr}")
            
            # Start processing threads
            self.running = True
            
            # Thread 1: Receive messages from clients
            self.receive_thread = threading.Thread(target=self._receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # Thread 2: Process incoming requests
            self.process_thread = threading.Thread(target=self._process_requests)
            self.process_thread.daemon = True
            self.process_thread.start()
            
            # Thread 3: Send replies to clients
            self.send_thread = threading.Thread(target=self._send_replies)
            self.send_thread.daemon = True
            self.send_thread.start()
            
            self.logger.info(f"ZMQ Router Server started for {self.system_type.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            raise
    
    def stop(self):
        """Stop ZMQ Router server"""
        self.running = False
        
        # Stop Pub server
        self.pub_server.stop()
        
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        self.logger.info(f"ZMQ Router Server stopped for {self.system_type.value}")
    
    def _receive_messages(self):
        """Receive messages from clients and put into request queue"""
        self.logger.info("Message receiving thread started")
        
        while self.running:
            try:
                # Receive client identity
                identity = self.socket.recv()
                if not identity:
                    continue
                
                # Receive request message
                request = self.socket.recv()
                if not request:
                    continue
                
                identity_str = identity.decode('utf-8')
                request_str = request.decode('utf-8')
                
                self.logger.info(f"Received message from {identity_str}: {request_str}")
                
                # Put (identity, request) into request queue for processing
                self.request_queue.put((identity_str, request_str))
                
            except zmq.Again:
                # Timeout, continue
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error receiving message: {e}")
                continue
        
        self.logger.info("Message receiving thread stopped")
    
    def _process_requests(self):
        """Process requests from request queue and put replies into reply queue"""
        self.logger.info("Request processing thread started")
        
        while self.running:
            try:
                # Get (identity, request) from queue with timeout
                identity, request = self.request_queue.get(timeout=1)
                
                self.logger.info(f"Processing request from {identity}")
                
                # Handle message and get reply
                reply = self.handle_message(request, identity)
                
                if reply:
                    # Put (identity, reply) into reply queue for sending
                    self.reply_queue.put((identity, reply))
                
            except Empty:
                # Normal timeout, queue is empty - silently continue
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error processing request: {e}")
                continue
        
        self.logger.info("Request processing thread stopped")
    
    def _send_replies(self):
        """Send replies from reply queue to clients"""
        self.logger.info("Reply sending thread started")
        
        while self.running:
            try:
                # Get (identity, reply) from queue with timeout
                identity, reply = self.reply_queue.get(timeout=1)
                
                self.logger.info(f"Sending reply to {identity}: {reply[:500]}...")
                
                # Send reply to client (send identity then reply)
                self.socket.send(identity.encode('utf-8'), zmq.SNDMORE)
                self.socket.send(reply.encode('utf-8'))
                
            except Empty:
                # Normal timeout, queue is empty - silently continue
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error sending reply: {e}")
                continue
        
        self.logger.info("Reply sending thread stopped")
    
    def handle_message(self, msg: str, identity: str) -> Optional[str]:
        """
        Handle incoming message
        
        Args:
            msg: Message string
            identity: Client identity
            
        Returns:
            Reply message string or None if no reply needed
        """
        try:
            # Parse message based on type and system
            # Always use parse_general_message first to get all fields
            msg_data = self.adapter.parse_general_message(msg)
            
            # For task messages, also extract task-specific fields
            if msg_data.get('msg_type') == 'MsgTask':
                # Re-parse with task-specific method to get all task fields
                task_data = self.adapter.parse_task_message(msg)
                msg_data.update(task_data)
            
            msg_type = msg_data.get('msg_type')
            # Get SN - for Ion Trap and Neutral Atom, it's extracted by parse_general_message
            # For other systems, it's extracted by parse_task_message
            sn = msg_data.get('sn')
            
            self.logger.info(f"Processing message type: {msg_type}, SN: {sn}")
            
            # Route to appropriate handler
            if msg_type == 'MsgTask':
                return self._handle_task(msg_data, identity)
            elif msg_type == 'TaskStatus':
                return self._handle_task_status(msg_data)
            elif msg_type == 'MsgHeartbeat':
                return self._handle_heartbeat(msg_data)
            elif msg_type == 'GetChipConfig':
                return self._handle_get_chip_config(msg_data)
            elif msg_type == 'MsgGetToken':
                return self._handle_get_token(msg_data)
            elif msg_type == 'MsgUpdateToken':
                return self._handle_update_token(msg_data)
            elif msg_type == 'GetUpdateTime':
                return self._handle_get_update_time(msg_data)
            elif msg_type == 'GetRBData':
                return self._handle_get_rb_data(msg_data)
            elif msg_type == 'SetVip':
                return self._handle_set_vip(msg_data)
            elif msg_type == 'ReleaseVip':
                return self._handle_release_vip(msg_data)
            elif msg_type == 'MsgTaskAck':
                # Acknowledgment, no reply needed
                return None
            elif msg_type == 'MsgTaskResultAck':
                # Result acknowledgment, no reply needed
                return None
            elif msg_type == 'MsgTaskResult':
                # Task result (sent by server, no reply)
                return None
            else:
                self.logger.warning(f"Unknown message type: {msg_type}")
                return None
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            # Don't have msg_type yet for JSON errors, use UndefinedMsg
            return self.adapter.build_undefined_msg(0, ErrorCode.JSON_ERROR.value, str(e))
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            import traceback
            traceback.print_exc()
            # Don't have msg_type yet for general errors, use UndefinedMsg
            return self.adapter.build_undefined_msg(0, ErrorCode.UNDEFINED_ERROR.value, str(e))
    
    def _handle_task(self, msg_data: Dict, identity: str) -> str:
        """Handle task submission message"""
        task_id = msg_data.get('task_id')
        sn = msg_data.get('sn')
        
        self.logger.info(f"Received task: {task_id}")
        
        # Add task to manager
        success = self.task_manager.add_task(task_id, identity, msg_data)
        
        if not success:
            # Task ID already exists
            self.logger.warning(f"Task ID already exists: {task_id}")
            return self.adapter.build_task_ack(sn, ErrorCode.TASK_ID_DUPLICATE.value, "Task ID already exists")
        
        # Send acknowledgment
        ack = self.adapter.build_task_ack(sn)
        self.logger.info(f"Sent task acknowledgment for: {task_id}")
        
        # Publish task status: PENDING
        self.pub_server.publish_task_status(task_id, TaskStatus.PENDING.value, sn)
        
        # Start task processing in background thread
        threading.Thread(target=self._process_task_async, args=(task_id,), daemon=True).start()
        
        return ack
    
    def _process_task_async(self, task_id: str):
        """Process task asynchronously"""
        try:
            # Publish task status: RUNNING
            sn = 0
            self.pub_server.publish_task_status(task_id, TaskStatus.RUNNING.value, sn)
            
            # Process task
            result = self.task_manager.process_task(task_id)
            
            if result is None:
                self.logger.error(f"Failed to process task: {task_id}")
                self.pub_server.publish_task_status(task_id, TaskStatus.FAILED.value, sn)
                return
            
            # Get task info
            task = self.task_manager.get_task(task_id)
            if not task:
                self.logger.error(f"Task not found: {task_id}")
                return
            
            sn = task.msg_data.get('sn')
            
            # Build result message - all systems use the same unified format
            timing = self.task_manager.get_timing_info(task_id)
            
            # Extract keys and prob counts from result
            keys = []
            prob_counts = []
            if isinstance(result, list):
                for r in result:
                    keys.append(list(r.keys()))
                    prob_counts.append(list(r.values()))
            
            reply = self.adapter.build_task_result(
                sn, task_id, keys, prob_counts, timing
            )
            
            self.logger.info(f"Task completed: {task_id}")
            
            # Publish task status: SUCCESSED
            self.pub_server.publish_task_status(task_id, TaskStatus.SUCCESSED.value, sn)
            
            # Queue reply
            self.reply_queue.put((task.identity, reply))
            
        except Exception as e:
            self.logger.error(f"Error processing task {task_id}: {e}")
            import traceback
            traceback.print_exc()
            # Send error response as MsgTaskResult with error code
            task = self.task_manager.get_task(task_id)
            if task:
                reply = self.adapter.build_task_result(
                    task.msg_data.get('sn'),  # SN
                    task_id,                  # TaskId
                    [],                       # keys (empty for error)
                    [],                       # prob_counts (empty for error)
                    {},                       # note_time (empty for error)
                    ErrorCode.UNDEFINED_ERROR.value,  # err_code
                    str(e)                    # err_info
                )
                self.reply_queue.put((task.identity, reply))
    
    def _handle_task_status(self, msg_data: Dict) -> str:
        """Handle task status query"""
        task_id = msg_data.get('task_id')
        sn = msg_data.get('sn')
        
        status = self.task_manager.get_task_status(task_id)
        
        self.logger.info(f"Task {task_id} status: {status}")
        
        return self.adapter.build_task_status_ack(sn, task_id, status)
    
    def _handle_heartbeat(self, msg_data: Dict) -> str:
        """Handle heartbeat message"""
        sn = msg_data.get('sn')
        
        # Build heartbeat acknowledgment - all platforms now use same signature with topic
        reply = self.adapter.build_heartbeat_ack(
            sn, self.default_chip_id, "simulator_topic"
        )
        
        self.logger.info("Heartbeat acknowledged")
        
        return reply
    
    def _handle_get_chip_config(self, msg_data: Dict) -> str:
        """Handle get chip configuration"""
        sn = msg_data.get('sn')
        chip_id = msg_data.get('ChipID')
        
        # Convert chip_id to string (handle both string and int inputs)
        # If not provided, use system default chip ID
        chip_id = str(chip_id) if chip_id is not None else self.default_chip_id
        
        self.logger.info(f"Loading chip config for ChipID: {chip_id}")
        
        # Load chip configuration using loader
        chip_config, point_label_list = self.chip_config_loader.get_chip_config(chip_id)
        
        if not chip_config:
            self.logger.warning(f"No configuration found for chip ID: {chip_id}")
            # Return error response - all platforms now use same signature
            reply = self.adapter.build_get_chip_config_ack(
                sn, chip_id, [], {},
                ErrorCode.TASK_PARAM_ERROR.value,
                f"Unknown chip ID: {chip_id}"
            )
            return reply
        
        # Build response - all platforms now use same signature with point_label_list
        reply = self.adapter.build_get_chip_config_ack(
            sn, chip_id, point_label_list, chip_config
        )
        
        self.logger.info(f"Chip configuration sent for chip {chip_id} with {len(point_label_list)} work areas")
        
        return reply
    
    def _handle_get_token(self, msg_data: Dict) -> str:
        """Handle get token request (Ion Trap and Neutral Atom only)"""
        # Parse body from message data
        body = msg_data.get('body', {})
        app_id = body.get('APPId', '')
        api_key = body.get('APIKey', '')
        api_secret = body.get('APISecret', '')
        
        self.logger.info(f"Token request from APPId: {app_id}")
        
        # Verify credentials for Ion Trap
        if self.system_type == QuantumSystemType.ION_TRAP:
            if (app_id != ServerConfig.ION_TRAP_APP_ID or 
                api_key != ServerConfig.ION_TRAP_API_KEY or 
                api_secret != ServerConfig.ION_TRAP_API_SECRET):
                self.logger.warning(f"Authentication failed for APPId: {app_id}")
                reply = json.dumps({
                    'MsgType': 'MsgGetTokenAck',
                    'AccessToken': '',
                    'ErrCode': ErrorCode.AUTH_ERROR.value,
                    'ErrInfo': 'Authentication failed: Invalid credentials',
                    'Version': '1.0'
                })
                return reply
        
        # For Neutral Atom, allow any credentials for now (can be configured later)
        # or implement similar validation if needed
        
        # Authentication successful, generate tokens
        access_token = f"access_token_{app_id}_{int(time.time())}"
        refresh_token = f"refresh_token_{app_id}_{int(time.time())}"
        
        self.access_tokens[app_id] = access_token
        self.refresh_tokens[refresh_token] = access_token
        
        reply = json.dumps({
            'MsgType': 'MsgGetTokenAck',
            'Data': {
                'AccessToken': access_token,
                'RefreshToken': refresh_token
            },
            'ErrCode': 0,
            'ErrInfo': '',
            'Version': '1.0'
        })
        
        self.logger.info(f"Token generated successfully for APPId: {app_id}")
        
        return reply
    
    def _handle_update_token(self, msg_data: Dict) -> str:
        """Handle update token request (Ion Trap and Neutral Atom only)"""
        # Authorization is in header, parsed by parse_general_message
        refresh_token = msg_data.get('authorization', '')
        
        self.logger.info(f"Received refresh token update request: {refresh_token}")
        
        # Check refresh token and generate new tokens
        if refresh_token in self.refresh_tokens:
            # Get old access token associated with this refresh token
            old_access_token = self.refresh_tokens[refresh_token]
            
            # Generate new access token and new refresh token
            new_access_token = f"access_token_refreshed_{int(time.time())}"
            new_refresh_token = f"refresh_token_refreshed_{int(time.time())}"
            
            # Remove old refresh token mapping
            del self.refresh_tokens[refresh_token]
            # Remove old access token mapping
            if old_access_token in self.access_tokens:
                del self.access_tokens[old_access_token]
            
            # Store new tokens with new refresh token as key
            self.refresh_tokens[new_refresh_token] = new_access_token
            self.access_tokens[new_access_token] = new_access_token
            
            reply = json.dumps({
                'MsgType': 'MsgUpdateTokenAck',
                'AccessToken': new_access_token,
                'RefreshToken': new_refresh_token,
                'ErrCode': 0,
                'ErrInfo': '',
                'Version': '1.0'
            })
            
            self.logger.info(f"Tokens updated successfully: access={old_access_token}->{new_access_token}, refresh={refresh_token}->{new_refresh_token}")
        else:
            reply = json.dumps({
                'MsgType': 'MsgUpdateTokenAck',
                'AccessToken': '',
                'RefreshToken': '',
                'ErrCode': ErrorCode.AUTH_ERROR.value,
                'ErrInfo': 'Invalid refresh token',
                'Version': '1.0'
            })
            self.logger.warning(f"Invalid refresh token: {refresh_token}")
        
        return reply
    
    def _handle_get_update_time(self, msg_data: Dict) -> str:
        """Handle get update time request"""
        sn = msg_data.get('sn')
        
        # Mock update time data
        qubits = [0, 1, 2, 3, 4, 5]
        timestamps = [int(time.time() * 1000)] * len(qubits)
        
        # Build response - all platforms now use same signature
        reply = self.adapter.build_get_update_time_ack(
            sn, self.default_chip_id, qubits, timestamps
        )
        
        self.logger.info("Update time sent")
        
        return reply
    
    def _handle_get_rb_data(self, msg_data: Dict) -> str:
        """Handle get RB data request"""
        sn = msg_data.get('sn')
        
        # Mock RB data
        single_depth = [50, 50, 50, 50, 50]
        double_depth = [0, 50, 50, 50, 50]
        single_fidelity = {
            'qubit': ['0', '1', '2', '3', '4'],
            'fidelity': [0.99, 0.99, 0.99, 0.99, 0.99]
        }
        double_fidelity = {
            'qubitPair': ['0-1', '1-2', '2-3', '3-4'],
            'fidelity': [0.95, 0.95, 0.95, 0.95]
        }
        
        if self.system_type == QuantumSystemType.SUPERCONDUCTING:
            reply = self.adapter.build_get_rb_data_ack(
                sn, self.default_chip_id, single_depth, double_depth,
                single_fidelity, double_fidelity
            )
        else:  # Ion Trap, Neutral Atom, and Photonic
            reply = self.adapter.build_get_rb_data_ack(
                sn, self.default_chip_id, single_depth, double_depth,
                single_fidelity, double_fidelity
            )
        
        self.logger.info("RB data sent")
        
        return reply
    
    def _handle_set_vip(self, msg_data: Dict) -> str:
        """Handle set VIP request (Superconducting only)"""
        sn = msg_data.get('sn')
        reply = self.adapter.build_set_vip_ack(sn)
        self.logger.info("VIP set")
        return reply
    
    def _handle_release_vip(self, msg_data: Dict) -> str:
        """Handle release VIP request (Superconducting only)"""
        sn = msg_data.get('sn')
        reply = self.adapter.build_release_vip_ack(sn)
        self.logger.info("VIP released")
        return reply
    
    def _get_mock_chip_config(self) -> Dict:
        """Get mock chip configuration"""
        return {
            'QuantumChipArch': {
                'Chip': 'WuYuan_01',
                'QubitCount': 72,
                'AdjMatrix': {
                    '0': [{'v': 1, 'w': 0.9759}],
                    '1': [{'v': 0, 'w': 0.9759}, {'v': 2, 'w': 0.9577}],
                    '2': [{'v': 1, 'w': 0.9577}]
                },
                'QubitParams': {
                    '0': {
                        'T1': 14.67,
                        'T2': 0.5,
                        'ReadoutFidelity': 0.9169,
                        'SingleGateFidelity': 0.9973
                    },
                    '1': {
                        'T1': 15.525,
                        'T2': 1.082,
                        'ReadoutFidelity': 0.9433,
                        'SingleGateFidelity': 0.994
                    }
                },
                'AvailableQubits': [0, 1, 2],
                'QGateClock': {
                    'RX': 30,
                    'RY': 30,
                    'RZ': 30,
                    'CNOT': 40,
                    'CZ': 40,
                    'H': 30
                },
                'BasicQGate': ['X', 'Y', 'Z', 'H', 'RX', 'RY', 'RZ', 'CNOT', 'CZ', 'MEASURE'],
                'LastUpdateTime': int(time.time() * 1000),
                'MaxClockCycle': 10000,
                'MaxShots': 10000
            }
        }
    
    def _build_error_response(self, sn: int, msg_type: str, err_code: int, err_info: str) -> str:
        """
        Build error response with appropriate message type
        
        Args:
            sn: Sequence number
            msg_type: Original message type that caused the error
            err_code: Error code
            err_info: Error information
            
        Returns:
            Error response string with correct message type
        """
        if msg_type == 'MsgTask':
            # Task processing error: return MsgTaskResult with error code
            return self.adapter.build_task_result(
                sn,              # SN
                '',              # TaskId (empty for error)
                [],              # keys (empty for error)
                [],              # prob_counts (empty for error)
                {},              # note_time (empty for error)
                err_code,         # Error code
                err_info          # Error info
            )
        else:
            # Other message errors: use corresponding ack method
            # For most cases, use build_task_result_ack which returns generic error ack
            return self.adapter.build_task_result_ack(sn, err_code, err_info)


def run_server(system_type: QuantumSystemType):
    """Run ZMQ Router server for specific system type"""
    server = ZmqRouterServer(system_type)
    
    try:
        server.start()
        print(f"{system_type.value} server running on port {server.port}")
        print("Press Ctrl+C to stop")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()
    except Exception as e:
        print(f"Server error: {e}")
        server.stop()
