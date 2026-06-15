"""
ZMQ Pub Server for quantum simulation status updates
"""
import json
import time
import threading
import zmq
import logging
from typing import Optional, Dict, List
from config import (
    QuantumSystemType, ServerConfig
)


class ZmqPubServer:
    """ZMQ Pub server for pushing status updates"""
    
    def __init__(self, system_type: QuantumSystemType):
        """
        Initialize ZMQ Pub server
        
        Args:
            system_type: Type of quantum system to simulate
        """
        self.system_type = system_type
        self.port = ServerConfig.PUB_PORTS[system_type]
        self.context = zmq.Context()
        self.socket = None
        self.running = False
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger(f"ZmqPub-{self.system_type.value}")
    
    def start(self):
        """Start the ZMQ Pub server"""
        try:
            # Create PUB socket
            self.socket = self.context.socket(zmq.PUB)
            
            # Bind to address
            bind_addr = f"tcp://{ServerConfig.BIND_ADDRESS}:{self.port}"
            self.socket.bind(bind_addr)
            self.logger.info(f"Pub server bound to {bind_addr}")
            
            self.running = True
            
            # Add console print for visibility
            print(f"  - Pub Port: {self.port}")
            
            self.logger.info(f"ZMQ Pub Server started for {self.system_type.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to start Pub server: {e}")
            raise
    
    def stop(self):
        """Stop the ZMQ Pub server"""
        self.running = False
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        self.logger.info(f"ZMQ Pub Server stopped for {self.system_type.value}")
    
    def publish_task_status(self, task_id: str, status: int, sn: int = 0):
        """
        Publish task status update
        
        Args:
            task_id: Task identifier
            status: Task status code
            sn: Sequence number (default 0)
        """
        if not self.running:
            return
        
        try:
            # Three-layer structure: topic + operation + data
            topic = b'simulator_topic'
            operation = b'task_status'
            
            # Data format
            data = {
                'MsgType': 'TaskStatus',
                'SN': sn,
                'TaskId': task_id,
                'TaskStatus': status
            }
            
            self.socket.send(topic, zmq.SNDMORE)
            self.socket.send(operation, zmq.SNDMORE)
            self.socket.send_string(json.dumps(data))
            
            self.logger.info(f"Published task status: {task_id} -> {status}")
            
        except Exception as e:
            self.logger.error(f"Error publishing task status: {e}")
    
    def publish_chip_update(self, update_flag: bool, timestamp: int):
        """
        Publish chip configuration update (superconducting only)
        
        Args:
            update_flag: Whether configuration needs update
            timestamp: Last update timestamp
        """
        if not self.running or self.system_type != QuantumSystemType.SUPERCONDUCTING:
            return
        
        try:
            # Three-layer structure: topic + operation + data
            topic = b'simulator_topic'
            operation = b'chip_update'
            
            # Data format
            data = {
                'UpdateFlag': update_flag,
                'LastUpdateTime': timestamp
            }
            
            self.socket.send(topic, zmq.SNDMORE)
            self.socket.send(operation, zmq.SNDMORE)
            self.socket.send_string(json.dumps(data))
            
            self.logger.info(f"Published chip update: flag={update_flag}, time={timestamp}")
            
        except Exception as e:
            self.logger.error(f"Error publishing chip update: {e}")
    
    def publish_chip_resource_status(self, inst_status: int = 1, linked: int = 1):
        """
        Publish chip resource status (superconducting only)
        
        Args:
            inst_status: Instance status
            linked: Linked status
        """
        if not self.running or self.system_type != QuantumSystemType.SUPERCONDUCTING:
            return
        
        try:
            # Three-layer structure: topic + operation + data
            topic = b'simulator_topic'
            operation = b'probe'
            
            # Mock resource status data
            data = {
                'inst_status': inst_status,
                'linked': linked,
                'timestamp': time.time(),
                'scheduler': {
                    'status': 'InitialState',
                    'queue_len': 0
                },
                'core_status': {
                    'empty_thread': 4,
                    'pause_read': 0,
                    'thread_num': 5
                },
                'core_thread': {
                    't0': {
                        'status': 'ready',
                        'thread_id': 't0',
                        'task_id': None,
                        'start_time': None,
                        'user': None,
                        'env_bits': [],
                        'use_bits': []
                    },
                    't1': {
                        'status': 'ready',
                        'thread_id': 't1',
                        'task_id': None,
                        'start_time': None,
                        'user': None,
                        'env_bits': [],
                        'use_bits': []
                    },
                    't2': {
                        'status': 'ready',
                        'thread_id': 't2',
                        'task_id': None,
                        'start_time': None,
                        'user': None,
                        'env_bits': [],
                        'use_bits': []
                    },
                    't3': {
                        'status': 'ready',
                        'thread_id': 't3',
                        'task_id': None,
                        'start_time': None,
                        'user': None,
                        'env_bits': [],
                        'use_bits': []
                    },
                    't4': {
                        'status': 'ready',
                        'thread_id': 't4',
                        'task_id': None,
                        'start_time': None,
                        'user': None,
                        'env_bits': [],
                        'use_bits': []
                    }
                }
            }
            
            self.socket.send(topic, zmq.SNDMORE)
            self.socket.send(operation, zmq.SNDMORE)
            self.socket.send_string(json.dumps(data))
            
            self.logger.info("Published chip resource status")
            
        except Exception as e:
            self.logger.error(f"Error publishing chip resource status: {e}")
    
    def publish_calibration_start(self, qubits: List[str], couplers: List[str], 
                              pairs: List[str], discriminators: List[str], 
                              point_label: int = 2):
        """
        Publish calibration start information (superconducting only)
        
        Args:
            qubits: Qubit indices being calibrated
            couplers: Coupler list
            pairs: Qubit pairs
            discriminators: Discriminator list
            point_label: Point label for current calibration
        """
        if not self.running or self.system_type != QuantumSystemType.SUPERCONDUCTING:
            return
        
        try:
            # Three-layer structure: topic + operation + data
            topic = b'simulator_topic'
            operation = b'calibration_start'
            
            # Data format
            data = {
                'config_flag': False,
                'qubits': qubits,
                'couplers': couplers,
                'pairs': pairs,
                'discriminators': discriminators,
                'point_label': point_label
            }
            
            self.socket.send(topic, zmq.SNDMORE)
            self.socket.send(operation, zmq.SNDMORE)
            self.socket.send_string(json.dumps(data))
            
            self.logger.info(f"Published calibration start: {len(qubits)} qubits")
            
        except Exception as e:
            self.logger.error(f"Error publishing calibration start: {e}")
    
    def publish_calibration_done(self, qubits: List[str], couplers: List[str],
                             pairs: List[str], discriminators: List[str],
                             point_label: int = 2):
        """
        Publish calibration done information (superconducting only)
        
        Args:
            qubits: Qubit indices that were calibrated
            couplers: Coupler list
            pairs: Qubit pairs
            discriminators: Discriminator list
            point_label: Point label for current calibration
        """
        if not self.running or self.system_type != QuantumSystemType.SUPERCONDUCTING:
            return
        
        try:
            # Three-layer structure: topic + operation + data
            topic = b'simulator_topic'
            operation = b'calibration_done'
            
            # Data format
            data = {
                'qubits': qubits,
                'couplers': couplers,
                'pairs': pairs,
                'discriminators': discriminators,
                'config_flag': True,
                'point_label': point_label
            }
            
            self.socket.send(topic, zmq.SNDMORE)
            self.socket.send(operation, zmq.SNDMORE)
            self.socket.send_string(json.dumps(data))
            
            self.logger.info(f"Published calibration done: {len(qubits)} qubits")
            
        except Exception as e:
            self.logger.error(f"Error publishing calibration done: {e}")
    
    def publish_chip_protect(self, protect_flag: bool, durative_time: int, last_time: int):
        """
        Publish chip protection information (superconducting only)
        
        Args:
            protect_flag: True for maintenance start, False for maintenance end
            durative_time: Maintenance duration in minutes
            last_time: Timestamp
        """
        if not self.running or self.system_type != QuantumSystemType.SUPERCONDUCTING:
            return
        
        try:
            # Three-layer structure: topic + operation + data
            topic = b'simulator_topic'
            operation = b'chip_protect'
            
            # Data format
            data = {
                'ProtectFlag': protect_flag,
                'DurativeTime': durative_time,
                'LastTime': last_time
            }
            
            self.socket.send(topic, zmq.SNDMORE)
            self.socket.send(operation, zmq.SNDMORE)
            self.socket.send_string(json.dumps(data))
            
            self.logger.info(f"Published chip protect: flag={protect_flag}, time={durative_time}min")
            
        except Exception as e:
            self.logger.error(f"Error publishing chip protect: {e}")


def run_pub_server(system_type: QuantumSystemType):
    """Run ZMQ Pub server for specific system type"""
    server = ZmqPubServer(system_type)
    
    try:
        server.start()
        print(f"{system_type.value} Pub server running on port {server.port}")
        print("Press Ctrl+C to stop")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down Pub server...")
        server.stop()
    except Exception as e:
        print(f"Pub server error: {e}")
        server.stop()
