"""
Task manager for quantum simulation
"""
import json
import time
import threading
from typing import Dict, Optional, List
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from config import TaskStatus, ServerConfig
from result_generator import generate_random_results_multiple


class TaskInfo:
    """Task information structure"""
    def __init__(self, task_id: str, identity: str, msg_data: Dict):
        self.task_id = task_id
        self.identity = identity
        self.msg_data = msg_data
        self.status = TaskStatus.PENDING
        self.timestamp = int(time.time() * 1000)  # milliseconds
        self.compile_start_time = 0
        self.compile_end_time = 0
        self.pending_start_time = 0
        self.pending_end_time = 0
        self.measure_start_time = 0
        self.measure_end_time = 0
        self.process_start_time = 0
        self.process_end_time = 0
        self.shots = 0
        self.measured_qubits = []


class TaskManager:
    """Manage task lifecycle and processing"""
    
    def __init__(self, system_type):
        self.system_type = system_type
        self.tasks: Dict[str, TaskInfo] = {}
        self.task_queue = deque(maxlen=ServerConfig.MAX_QUEUE_SIZE)
        self.lock = threading.Lock()
        self.thread_pool = ThreadPoolExecutor(max_workers=ServerConfig.THREAD_POOL_SIZE)
        
    def add_task(self, task_id: str, identity: str, msg_data: Dict) -> bool:
        """Add a new task to the manager"""
        with self.lock:
            if task_id in self.tasks:
                return False  # Task ID already exists
            
            task_info = TaskInfo(task_id, identity, msg_data)
            self.tasks[task_id] = task_info
            self.task_queue.append(task_id)
            
            # Remove old tasks if queue is full
            if len(self.task_queue) >= ServerConfig.MAX_QUEUE_SIZE:
                old_task_id = self.task_queue.popleft()
                del self.tasks[old_task_id]
                
        return True
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task information"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus):
        """Update task status"""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].status = status
                current_time = int(time.time() * 1000)
                
                if status == TaskStatus.COMPILING:
                    self.tasks[task_id].compile_start_time = current_time
                elif status == TaskStatus.COMPILED:
                    self.tasks[task_id].compile_end_time = current_time
                    self.tasks[task_id].pending_start_time = current_time                    
                elif status == TaskStatus.RUNNING:
                    self.tasks[task_id].measure_start_time = current_time
                    self.tasks[task_id].pending_end_time = current_time
                elif status == TaskStatus.SUCCESSED:
                    self.tasks[task_id].measure_end_time = current_time
                    self.tasks[task_id].process_start_time = current_time
                elif status == TaskStatus.FAILED:
                    self.tasks[task_id].measure_end_time = current_time
    
    def get_task_status(self, task_id: str) -> TaskStatus:
        """Get current task status"""
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                return task.status
            return TaskStatus.NOTASK
    
    def remove_task(self, task_id: str):
        """Remove task from manager"""
        with self.lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
    
    def get_timing_info(self, task_id: str) -> Dict[str, int]:
        """Get timing information for task"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return {}
            
            compile_time = task.compile_end_time - task.compile_start_time
            measure_time = task.measure_end_time - task.measure_start_time
            process_time = task.process_end_time - task.process_start_time
            pending_time = task.pending_end_time - task.pending_start_time
            
            return {
                'CompileTime': compile_time,
                'MeasureTime': measure_time,
                'PostProcessTime': process_time,
                'PendingTime': pending_time
            }
    
    def process_task(self, task_id: str):
        """Process task and generate results"""
        task = self.get_task(task_id)
        if not task:
            return None
        
        try:
            # Update status to COMPILING
            self.update_task_status(task_id, TaskStatus.COMPILING)
            
            # Simulate compile time
            #time.sleep(ServerConfig.COMPILE_TIME / 1000.0)
            self.update_task_status(task_id, TaskStatus.COMPILED)
            
            # Update status to RUNNING
            self.update_task_status(task_id, TaskStatus.RUNNING)
            
            # Extract shots and measured qubits
            shots = task.msg_data.get('configure', {}).get('Shot', 1000)
            
            # Generate random results based on system type
            if self.system_type == 'neutral_atom':
                # Neutral atom uses different format
                result = self._generate_neutral_atom_result(task_id, shots)
            else:
                # Other systems use standard format
                measured_qubits = task.msg_data.get('configure', {}).get('MeasureQubitNum', [5])
                result = generate_random_results_multiple(measured_qubits, shots)
            
            # Simulate run time
            #time.sleep(ServerConfig.RUN_TIME / 1000.0)
            
            # Update status to SUCCESSED
            self.update_task_status(task_id, TaskStatus.SUCCESSED)
            
            # Simulate post process time
            current_time = int(time.time() * 1000)
            task.process_start_time = current_time
            #time.sleep(ServerConfig.POST_PROCESS_TIME / 1000.0)
            task.process_end_time = int(time.time() * 1000)
            
            return result
            
        except Exception as e:
            self.update_task_status(task_id, TaskStatus.FAILED)
            raise e
    
    def _generate_neutral_atom_result(self, task_id: str, shots: int) -> list:
        """Generate result for neutral atom system
        
        Neutral atom now uses the same result format as other systems
        (Key and ProbCount arrays) to align with protocol specification.
        """
        # Use standard result generation to maintain protocol alignment
        # Neutral atom typically measures 5 qubits like other systems
        measured_qubits = [5]
        return generate_random_results_multiple(measured_qubits, shots)
