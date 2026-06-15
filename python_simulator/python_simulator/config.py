"""
Configuration management for quantum simulator
"""
import os
from enum import Enum
from typing import Dict

class QuantumSystemType(Enum):
    """Quantum system types"""
    SUPERCONDUCTING = "superconducting"  # 超导
    ION_TRAP = "ion_trap"  # 离子阱
    NEUTRAL_ATOM = "neutral_atom"  # 中性原子
    PHOTONIC = "photonic"  # 光量子

class ServerConfig:
    """Server configuration"""
    # Router ports (7000-7010)
    ROUTER_PORTS = {
        QuantumSystemType.SUPERCONDUCTING: 7000,
        QuantumSystemType.ION_TRAP: 7001,
        QuantumSystemType.NEUTRAL_ATOM: 7002,
        QuantumSystemType.PHOTONIC: 7003,
    }
    
    # PUB ports (8000-8010)
    PUB_PORTS = {
        QuantumSystemType.SUPERCONDUCTING: 8000,
        QuantumSystemType.ION_TRAP: 8001,
        QuantumSystemType.NEUTRAL_ATOM: 8002,
        QuantumSystemType.PHOTONIC: 8003,
    }
    
    # Default settings
    BIND_ADDRESS = "0.0.0.0"
    TIMEOUT = 2000  # milliseconds
    HWM = 10000  # High water mark
    
    # Task processing settings
    MAX_QUEUE_SIZE = 1000
    THREAD_POOL_SIZE = 4
    
    # Timing settings (milliseconds)
    COMPILE_TIME = 100
    RUN_TIME = 100
    POST_PROCESS_TIME = 100
    PENDING_TIME = 0
    
    # Log settings
    LOG_LEVEL = "INFO"
    LOG_FILE = "./log/python_simulator.log"
    
    # Ion Trap authentication credentials
    ION_TRAP_APP_ID = "0317507f"
    ION_TRAP_API_KEY = "1ab3cd05c35b5904e8faf48e068edc30"
    ION_TRAP_API_SECRET = "8709f99360763d2cae4d4b669383445c"

class ErrorCode(Enum):
    """Error codes"""
    NO_ERROR = 0
    UNDEFINED_ERROR = 1
    TASK_PARAM_ERROR = 2
    JSON_ERROR = 3
    QUEUE_FULL = 4
    AUTH_ERROR = 5
    TASK_ID_DUPLICATE = 10
    TASK_ID_NOT_EXIST = 40

class TaskStatus(Enum):
    """Task status codes"""
    UNKNOWN = 0
    PENDING = 1
    RUNNING = 2
    NOTASK = 3
    FAILED = 4
    SUCCESSED = 5
    RETRY = 6
    COMPILING = 7
    COMPILED = 8
    
    # Neutral atom specific
    SUBMIT = 9
    FINISH = 10
    CANCEL = 11
    SUBMITFAIL = 12
    RUNFAIL = 13
    WAITING = 14
