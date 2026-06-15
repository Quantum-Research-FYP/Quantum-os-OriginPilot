# Quantum Simulation ZMQ Server

A Python implementation of quantum simulation services supporting four quantum systems: Superconducting (超导), Ion Trap (离子阱), Neutral Atom (中性原子), and Photonic (光量子).

## Features

- **ZMQ Router-Dealer Pattern**: Handle client requests and send responses
- **ZMQ Pub-Sub Pattern**: Push status updates and notifications in real-time
- **Multi-Protocol Support**: Four different quantum system protocols
- **Task Management**: Async task processing with status tracking
- **Status Publishing**: Automatic task status updates via Pub-Sub
- **Random Result Generation**: Simulate quantum computation results
- **Port Range 7000-7010**: Router ports for client requests
- **Port Range 8000-8010**: Pub ports for status updates

## Architecture

```
PilotPy/python_simulator/
├── config.py                 # Configuration and enums
├── result_generator.py       # Random result generation
├── task_manager.py          # Task lifecycle management
├── zmq_router_server.py     # Core ZMQ Router server
├── zmq_pub_server.py       # ZMQ Pub server for status updates
├── main.py                 # Entry point
├── protocol_adapters/       # Protocol-specific adapters
│   ├── superconducting.py
│   ├── ion_trap.py
│   ├── neutral_atom.py
│   └── photonic.py
└── README.md               # This file
```

### Communication Patterns

The server uses two complementary ZMQ communication patterns:

1. **Router-Dealer (Request-Response)**
   - Ports: 7000-7003
   - Purpose: Handle client requests and send responses
   - Clients connect as DEALER, server acts as ROUTER
   - Bidirectional communication

2. **Pub-Sub (Publish-Subscribe)**
   - Ports: 8000-8003
   - Purpose: Push status updates and notifications to subscribers
   - Server acts as PUBLISHER, clients connect as SUBSCRIBER
   - Unidirectional push communication
   - Real-time status updates
   - Three-layer message structure: topic + operation + data

## Installation

### Requirements

```bash
pip install pyzmq
```

### Python Version

- Python 3.8+

## Usage

### Starting a Single Server

Start a specific quantum system server:

```bash
# Superconducting quantum (default port 7000)
python main.py --system superconducting

# Ion trap quantum (default port 7001)
python main.py --system ion_trap

# Neutral atom quantum (default port 7002)
python main.py --system neutral_atom

# Photonic quantum (default port 7003)
python main.py --system photonic
```

### Starting All Servers

Start all four quantum system servers simultaneously:

```bash
python main.py --all
```

### Starting Server with Pub

When you start a server, both Router and Pub servers are started automatically:

```bash
python main.py --system superconducting
```

Output:
```
============================================================
Starting superconducting Quantum Simulation Server
============================================================

superconducting server is running
  - Router Port: 7000
  - Pub Port: 8000
  - Bind Address: 0.0.0.0
  - Log Level: INFO
  - Thread Pool Size: 4
  - Max Queue Size: 1000

Press Ctrl+C to stop server
```

Both Router and Pub servers are started automatically when you start a system. The Pub server is used for real-time status updates (task status, chip updates, calibration notifications, etc.).

### Custom Configuration

```bash
# Custom port (only affects Router port)
python main.py --system superconducting --port 7005

# Custom bind address
python main.py --system superconducting --bind-address 192.168.1.100

# Log level
python main.py --system superconducting --log-level DEBUG
```

### Command Line Options

```
--system {superconducting,ion_trap,neutral_atom,photonic}
                        Type of quantum system to simulate
--all                   Start all quantum system servers
--port PORT             Override default port
--log-level {DEBUG,INFO,WARNING,ERROR}
                        Set logging level (default: INFO)
--bind-address ADDRESS   Bind address (default: *)
```

## Protocol Details

### 1. Superconducting Quantum (超导)

**Router Port**: 7000
**Pub Port**: 8000

**Supported Messages (Router)**:
- `MsgTask`: Submit quantum computation task
- `TaskStatus`: Query task status
- `MsgHeartbeat`: Heartbeat ping
- `GetChipConfig`: Get chip configuration
- `GetUpdateTime`: Get calibration time
- `GetRBData`: Get Randomized Benchmark data
- `SetVip`: Set exclusive time slot
- `ReleaseVip`: Release exclusive time slot

**Published Messages (Pub)**:
- `task_status`: Task status updates (PENDING, RUNNING, SUCCESSED, FAILED)
- `chip_update`: Chip configuration update notification
- `probe`: Chip resource status (qubit usage, thread status)
- `calibration_start`: Calibration start notification
- `calibration_done`: Calibration completion notification
- `chip_protect`: Chip maintenance start/end notification

**Protocol Features**:
- Flat JSON structure
- Task priority support
- Experiment mode support
- VIP time slot management
- Real-time status updates

### 2. Ion Trap Quantum (离子阱)

**Router Port**: 7001
**Pub Port**: 8001

**Supported Messages (Router)**:
- `MsgGetToken`: Get access token (authentication)
- `MsgUpdateToken`: Refresh access token
- `MsgTask`: Submit quantum computation task
- `TaskStatus`: Query task status
- `MsgHeartbeat`: Heartbeat ping
- `GetChipConfig`: Get chip configuration
- `GetUpdateTime`: Get calibration time
- `GetRBData`: Get Randomized Benchmark data

**Published Messages (Pub)**:
- `task_status`: Task status updates (PENDING, RUNNING, SUCCESSED, FAILED)

**Protocol Features**:
- Header/Body JSON structure
- Token-based authentication
- Version field support
- Fidelity matrix support

### 3. Neutral Atom Quantum (中性原子)

**Router Port**: 7002
**Pub Port**: 8002

**Supported Messages (Router)**:
- `MsgGetToken`: Get access token (authentication)
- `MsgTask`: Submit quantum computation task
- `MsgTaskStatus`: Query task status
- `MsgHeartbeat`: Heartbeat ping
- `GetUpdateTime`: Get calibration time
- `MsgAtomConfig`: Get atom configuration

**Published Messages (Pub)**:
- `task_status`: Task status updates (SUBMIT, RUNNING, FINISH, CANCEL, etc.)

**Protocol Features**:
- Header/Body JSON structure
- Token-based authentication
- OPENQASM task format
- Custom result format with grid and waveform

### 4. Photonic Quantum (光量子)

**Router Port**: 7003
**Pub Port**: 8003

**Supported Messages (Router)**:
- `MsgTask`: Submit quantum computation task
- `TaskStatus`: Query task status
- `MsgHeartbeat`: Heartbeat ping
- `GetChipConfig`: Get chip configuration

**Published Messages (Pub)**:
- `task_status`: Task status updates (PENDING, RUNNING, SUCCESSED, FAILED)

**Protocol Features**:
- Flat JSON structure
- Basic quantum gates support (X, Y, Z, H, RX, RY, RZ, CNOT, CZ, etc.)
- QASM-like task format

## Task Flow

### 1. Submit Task (Router)

```json
{
    "MsgType": "MsgTask",
    "SN": 1,
    "TaskId": "unique-task-id",
    "ConvertQProg": "...",
    "Configure": {
        "Shot": 1000
    }
}
```

### 2. Receive Acknowledgment (Router)

```json
{
    "MsgType": "MsgTaskAck",
    "SN": 1,
    "ErrCode": 0,
    "ErrInfo": ""
}
```

### 3. Task Status Updates (Pub)

Task status is automatically published via Pub-Sub:

**PENDING** (after receiving task):
```json
{
    "MsgType": "TaskStatus",
    "SN": 0,
    "TaskId": "unique-task-id",
    "TaskStatus": 1
}
```

**RUNNING** (during processing):
```json
{
    "MsgType": "TaskStatus",
    "SN": 0,
    "TaskId": "unique-task-id",
    "TaskStatus": 2
}
```

**SUCCESSED** (after completion):
```json
{
    "MsgType": "TaskStatus",
    "SN": 0,
    "TaskId": "unique-task-id",
    "TaskStatus": 5
}
```

### 4. Receive Result (Router)

```json
{
    "MsgType": "MsgTaskResult",
    "SN": 1,
    "TaskId": "unique-task-id",
    "Key": [["0x0", "0x1"]],
    "ProbCount": [[500, 500]],
    "NoteTime": {
        "CompileTime": 100,
        "MeasureTime": 2000,
        "PostProcessTime": 50
    }
}
```

## Configuration

### Server Config (config.py)

```python
class ServerConfig:
    # Network settings
    BIND_ADDRESS = "*"          # Bind to all interfaces
    TIMEOUT = 1000              # Socket timeout (ms)
    HWM = 1000                 # High water mark
    
    # Router port assignments
    ROUTER_PORTS = {
        QuantumSystemType.SUPERCONDUCTING: 7000,
        QuantumSystemType.ION_TRAP: 7001,
        QuantumSystemType.NEUTRAL_ATOM: 7002,
        QuantumSystemType.PHOTONIC: 7003
    }
    
    # Pub port assignments
    PUB_PORTS = {
        QuantumSystemType.SUPERCONDUCTING: 8000,
        QuantumSystemType.ION_TRAP: 8001,
        QuantumSystemType.NEUTRAL_ATOM: 8002,
        QuantumSystemType.PHOTONIC: 8003
    }
    
    # Performance settings
    THREAD_POOL_SIZE = 10       # Concurrent task workers
    MAX_QUEUE_SIZE = 200         # Max pending tasks
    
    # Simulation timing (ms)
    COMPILE_TIME = 100          # Simulated compile time
    RUN_TIME = 2000             # Simulated run time
    POST_PROCESS_TIME = 50      # Simulated post-process time
    
    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = "log/simulator.log"
```

## Task Status Enum

```python
class TaskStatus(Enum):
    UNKNOW_STATE = 0    # Unknown state
    PENDING = 1          # Task in queue
    COMPILING = 7         # Task compiling
    COMPILED = 8          # Task compiled
    RUNNING = 2           # Task running
    SUCCESSED = 5         # Task completed successfully
    FAILED = 4            # Task failed
    NOTASK = 3            # Task not found
    RETRY = 6             # Task retry
    
    # Neutral atom specific
    SUBMIT = 9            # Task submitted
    FINISH = 10           # Task finished
    CANCEL = 11           # Task cancelled
    SUBMITFAIL = 12       # Submit failed
    RUNFAIL = 13          # Run failed
    WAITING = 14           # Task waiting
```

## Error Codes

```python
class ErrorCode(Enum):
    NO_ERROR = 0                   # Success
    UNDEFINED_ERROR = 1            # Unknown error
    TASK_PARAM_ERROR = 2            # Task parameter error
    JSON_ERROR = 3                  # JSON parse error
    QUEUE_FULL = 4                   # Queue full
    AUTH_ERROR = 5                    # Authentication error
    TASK_ID_DUPLICATE = 10          # Duplicate task ID
    TASK_ID_NOT_EXIST = 40           # Task ID not found
```

## Example Client

### Router-Dealer Client Example

```python
import zmq
import json

# Connect to Router
context = zmq.Context()
socket = context.socket(zmq.DEALER)
socket.connect("tcp://localhost:7000")

# Submit task
task = {
    "MsgType": "MsgTask",
    "SN": 1,
    "TaskId": "test-task-001",
    "ConvertQProg": "[[{'H': [0]}, {'Measure': [[0]]}]]",
    "Configure": {"Shot": 1000}
}

# Send request
socket.send_json(task)

# Receive acknowledgment
ack = socket.recv_json()
print(f"Acknowledgment: {ack}")

# Receive result (async)
result = socket.recv_json()
print(f"Result: {result}")
```

### Pub-Sub Client Example

```python
import zmq
import json

# Connect to Pub server
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:8000")

# Subscribe to topic 'simulator_topic' to receive all messages
socket.setsockopt_string(zmq.SUBSCRIBE, b'simulator_topic')

# Receive status updates
while True:
    # Receive topic
    topic = socket.recv()
    
    # Receive operation
    operation = socket.recv()
    
    # Receive data
    data = socket.recv_json()
    
    print(f"Received: topic={topic}, operation={operation}")
    print(f"Data: {data}")
```

## Testing

### Start All Servers

```bash
python main.py --all
```

Expected output:
```
============================================================
Starting All Quantum Simulation Servers
============================================================

All servers started successfully!

Running servers:
  - superconducting      : Router 7000, Pub 8000
  - ion_trap           : Router 7001, Pub 8001
  - neutral_atom        : Router 7002, Pub 8002
  - photonic           : Router 7003, Pub 8003

Press Ctrl+C to stop all servers
```

### Test with Client

```bash
python test_client.py
```

## Logging

Logs are stored in the `log/` directory:

```
log/
├── ZmqRouter-superconducting.log
├── ZmqRouter-ion_trap.log
├── ZmqRouter-neutral_atom.log
└── ZmqRouter-photonic.log
```

Log levels:
- DEBUG: Detailed information for debugging
- INFO: General informational messages (default)
- WARNING: Warning messages
- ERROR: Error messages only

## Recent Fixes and Improvements

### SN Field Handling
- **Fixed**: All protocol adapters now have `parse_general_message()` method
- **Fixed**: SN (Sequence Number) is properly extracted from all message types
- **Improved**: Consistent SN handling across all four quantum systems
- **Impact**: Task acknowledgments and results now include correct SN values

### Token Management (Ion Trap & Neutral Atom)
- **Fixed**: `MsgUpdateToken` now returns both `AccessToken` and `RefreshToken`
- **Improved**: Token refresh flow properly updates both tokens
- **Impact**: Authentication flow is now complete and correct

### Message Field Access (CRITICAL FIX)
- **Fixed**: `parse_general_message()` now expands all message fields to top-level
- **Fixed**: All handlers can now access message fields directly (e.g., `msg_data.get('ChipID')`)
- **Impact**: Previously, handlers couldn't access fields like `ChipID`, `APPId`, `APIKey`, `APISecret`, `TaskId`, etc. for non-Task messages. Now all fields are accessible through `result.update(body)` for Ion Trap/Neutral Atom or `result.update(data)` for Superconducting/Photonic.

### Message Parsing
- **Improved**: All adapters support both general parsing and task-specific parsing
- **Fixed**: Ion Trap and Neutral Atom correctly handle Header/Body structure
- **Fixed**: Superconducting and Photonic correctly handle flat JSON structure
- **Impact**: All message types are parsed consistently and all fields are accessible

## Troubleshooting

### Port Already in Use

If you see `Address already in use` error:

```bash
# Find process using port
lsof -i :7000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### SN (Sequence Number) Missing in Responses

**Problem**: Response messages don't include SN or have incorrect SN value.

**Solution**: This has been fixed in all protocol adapters. Ensure you're using the latest code:

```bash
git pull  # Get latest changes
python main.py --all  # Restart servers
```

### Token Refresh Fails (Ion Trap & Neutral Atom)

**Problem**: `MsgUpdateToken` returns empty or invalid tokens.

**Solution**: 
1. Ensure you're sending `RefreshToken` in the `Authorization` header
2. Check that the refresh token was previously obtained from `MsgGetToken`
3. Verify the token hasn't expired (simulation tokens don't expire, but real systems do)

Example correct request:
```json
{
    "Header": {
        "MsgType": "MsgUpdateToken",
        "Version": "1.0",
        "Authorization": "refresh_token_testid1234_1234567890"
    },
    "Body": {}
}
```

### Task Status Not Published

**Problem**: Client doesn't receive task status updates via Pub-Sub.

**Solution**:
1. Verify Pub server is running (check port 8000-8003)
2. Ensure subscriber is subscribed to correct topic:
   ```python
   socket.setsockopt_string(zmq.SUBSCRIBE, b'simulator_topic')
   ```
3. Check firewall allows Pub server port
4. Verify three-layer message receiving (topic, operation, data):
   ```python
   topic = socket.recv()  # First: topic
   operation = socket.recv()  # Second: operation
   data = socket.recv_json()  # Third: data
   ```

### ZMQ Connection Failed

Check if pyzmq is installed:

```bash
pip install pyzmq
```

### Task Queue Full

If tasks are rejected with error code 4, queue is full (1000 tasks max). Either:
- Wait for tasks to complete
- Increase `MAX_QUEUE_SIZE` in config.py

### Pub-Sub Not Receiving Messages

If subscriber is not receiving messages:
- Check if Pub server is running (check port 8000-8003)
- Verify socket.setsockopt_string(zmq.SUBSCRIBE, b'simulator_topic') is called
- Check firewall settings

## Pub-Sub Message Structure

The Pub server uses a three-layer message structure:

1. **Topic**: Fixed as `b'simulator_topic'` for all messages
2. **Operation**: The message type (e.g., `b'task_status'`, `b'chip_update'`)
3. **Data**: The JSON data payload

This allows clients to subscribe to a single topic (`simulator_topic`) and receive all message types, then filter by operation as needed.

## License

This is a simulation server for development and testing purposes.

## Support

For issues or questions, please refer to protocol documentation:
- Superconducting: `超导通信协议文档.md`
- Ion Trap: `离子阱通信协议文档.md`
- Neutral Atom: `中性原子通信协议文档.md`
- Photonic: `光量子通信协议文档.md`
