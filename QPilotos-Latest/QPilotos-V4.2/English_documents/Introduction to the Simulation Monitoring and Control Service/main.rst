Quantum Simulation ZMQ Server Documentation
===========================================

:Author: OriginQ
:Date: Today

.. contents:: Table of Contents
   :depth: 3
   :local:



Project Introduction
====================

This is a Python-implemented quantum computing simulation service that supports four types of quantum systems: Superconducting, Ion Trap, Neutral Atom, and Photonic. It is designed to be used in conjunction with the Origin PilotOS operating system. To use this service, please refer to the "Add Chip" feature in the PilotOS graphical interface; once the corresponding chip information is configured, the service will be ready for use.

Features
========

* **ZMQ Router-Dealer Mode**: Handles client requests and dispatches responses.
* **ZMQ Pub-Sub Mode**: Pushes real-time status updates and notifications.
* **Multi-Protocol Support**: Supports distinct protocols for four different quantum systems.
* **Task Management**: Asynchronous task processing with status tracking.
* **Status Publishing**: Automatically pushes task status updates via Pub-Sub.
* **Random Result Generation**: Simulates quantum computing execution results.
* **Port Range 7000-7010**: Router ports dedicated to client requests.
* **Port Range 8000-8010**: Publisher ports dedicated to status updates.

System Architecture
===================

.. code-block:: bash

   PilotPy/python_simulator/
   ├── config.py                 # Configuration and enumeration definitions
   ├── result_generator.py       # Random result generator
   ├── task_manager.py           # Task lifecycle management
   ├── zmq_router_server.py      # Core ZMQ Router server
   ├── zmq_pub_server.py         # ZMQ Pub server (status updates)
   ├── main.py                   # Program entry point
   ├── protocol_adapters/        # Protocol adapters
   │   ├── superconducting.py    # Superconducting protocol adapter
   │   ├── ion_trap.py           # Ion Trap protocol adapter
   │   ├── neutral_atom.py       # Neutral Atom protocol adapter
   │   └── photonic.py           # Photonic protocol adapter
   └── README_EN.md              # This file (Documentation)

Communication Modes
-------------------

The server utilizes two complementary ZMQ communication patterns:

1. Router-Dealer Mode (Request-Response)
* **Ports**: 7000-7003
* **Purpose**: Handle client requests and return responses.
* **Connection**: The client connects as a DEALER, and the server acts as a ROUTER.
* **Characteristics**: Bidirectional communication.

2. Pub-Sub Mode (Publish-Subscribe)
* **Ports**: 8000-8003
* **Purpose**: Push status updates and notifications to subscribers.
* **Connection**: The server acts as a PUBLISHER, and the client connects as a SUBSCRIBER.
* **Characteristics**: Unidirectional push communication, real-time status updates.
* **Message Structure**: Three-layer structure (Topic + Operation + Data).

Installation Guide
==================

Environment Requirements
------------------------

.. code-block:: bash

   pip install pyzmq

Python Version
--------------

* Python 3.8 or higher.

Quick Start
===========

Start a Single Server
---------------------

Start a specific quantum system server:

.. code-block:: bash

   # Start the Superconducting quantum server (Default port: 7000)
   python main.py --system superconducting
   
   # Start the Ion Trap quantum server (Default port: 7001)
   python main.py --system ion_trap
   
   # Start the Neutral Atom quantum server (Default port: 7002)
   python main.py --system neutral_atom
   
   # Start the Photonic quantum server (Default port: 7003)
   python main.py --system photonic

Start All Servers
-----------------

Simultaneously start all four quantum system servers:

.. code-block:: bash

   python main.py --all

Server Startup (Automatically Includes Pub Server)
--------------------------------------------------

When starting a server, both the Router server and Pub server will launch automatically:

.. code-block:: bash

   python main.py --system superconducting

**Example Output:**

.. code-block:: text

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

Custom Configuration
--------------------

.. code-block:: bash

   # Custom port (Affects Router port only)
   python main.py --system superconducting --port 7005
   
   # Custom bind address
   python main.py --system superconducting --bind-address 192.168.1.100
   
   # Set log level
   python main.py --system superconducting --log-level DEBUG

Command Line Arguments
----------------------

.. code-block:: text

   --system {superconducting,ion_trap,neutral_atom,photonic}
                           The type of quantum system to simulate
   --all                   Start all quantum system servers
   --port PORT             Override the default port
   --log-level {DEBUG,INFO,WARNING,ERROR}
                           Set the log level (Default: INFO)
   --bind-address ADDRESS  Bind address (Default: *)

Protocol Details
================

1. Superconducting Quantum System
---------------------------------

* **Router Port**: 7000
* **Pub Port**: 8000

**Supported Message Types (Router):**
* "MsgTask": Submit a quantum computing task
* "TaskStatus": Query task status
* "MsgHeartbeat": Heartbeat check
* "GetChipConfig": Get chip configuration
* "GetUpdateTime": Get calibration time
* "GetRBData": Get Randomized Benchmarking (RB) data
* "SetVip": Set exclusive VIP time slot
* "ReleaseVip": Release exclusive VIP time slot

**Published Message Types (Pub):**
* "task_status": Task status update (PENDING, RUNNING, SUCCESSED, FAILED)
* "chip_update": Chip configuration update notification
* "probe": Chip resource status (Qubit usage, thread status)
* "calibration_start": Calibration start notification
* "calibration_done": Calibration completion notification
* "chip_protect": Chip maintenance start/end notification

**Protocol Characteristics:** Flat JSON structure; supports task prioritization, experimental modes, VIP time slot management, and real-time status updates.

2. Ion Trap Quantum System
--------------------------

* **Router Port**: 7001
* **Pub Port**: 8001

**Supported Message Types (Router):**
* "MsgGetToken": Get access token (Authentication)
* "MsgUpdateToken": Refresh access token
* "MsgTask": Submit a quantum computing task
* "TaskStatus": Query task status
* "MsgHeartbeat": Heartbeat check
* "GetChipConfig": Get chip configuration
* "GetUpdateTime": Get calibration time
* "GetRBData": Get Randomized Benchmarking (RB) data

**Published Message Types (Pub):** "task_status"

**Protocol Characteristics:** Header/Body JSON structure, token-based authentication mechanism, supports version fields and fidelity matrices.

3. Neutral Atom Quantum System
------------------------------

* **Router Port**: 7002
* **Pub Port**: 8002

**Supported Message Types (Router):**
* "MsgGetToken": Get access token (Authentication)
* "MsgTask": Submit a quantum computing task
* "MsgTaskStatus": Query task status
* "MsgHeartbeat": Heartbeat check
* "GetUpdateTime": Get calibration time
* "MsgAtomConfig": Get atom configuration

**Published Message Types (Pub):** "task_status"

**Protocol Characteristics:** Header/Body JSON structure, token-based authentication mechanism, OPENQASM task format, custom result format (including grid and waveform).

4. Photonic Quantum System
--------------------------

* **Router Port**: 7003
* **Pub Port**: 8003

**Supported Message Types (Router):**
* "MsgTask": Submit a quantum computing task
* "TaskStatus": Query task status
* "MsgHeartbeat": Heartbeat check
* "GetChipConfig": Get chip configuration

**Published Message Types (Pub):** "task_status"

**Protocol Characteristics:** Flat JSON structure, supports basic quantum gates, QASM-style task format.

Task Workflow
=============

1. Submit Task (Router)
-----------------------

.. code-block:: Python

   {
       "MsgType": "MsgTask",
       "SN": 1,
       "TaskId": "unique-task-id",
       "ConvertQProg": "...",
       "Configure": {
           "Shot": 1000
       }
   }

2. Receive Acknowledgement (Router)
-----------------------------------

.. code-block:: Python

   {
       "MsgType": "MsgTaskAck",
       "SN": 1,
       "ErrCode": 0,
       "ErrInfo": ""
   }

3. Task Status Update (Pub)
---------------------------

Task statuses are automatically pushed via Pub-Sub:

**PENDING** (After receiving the task):

.. code-block:: Python

   {
       "MsgType": "TaskStatus",
       "SN": 0,
       "TaskId": "unique-task-id",
       "TaskStatus": 1
   }

**RUNNING** (Processing):

.. code-block:: Python

   {
       "MsgType": "TaskStatus",
       "SN": 0,
       "TaskId": "unique-task-id",
       "TaskStatus": 2
   }

**SUCCESSED** (Completed):

.. code-block:: Python

   {
       "MsgType": "TaskStatus",
       "SN": 0,
       "TaskId": "unique-task-id",
       "TaskStatus": 5
   }

4. Receive Result (Router)
--------------------------

.. code-block:: Python

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

Configuration Instructions
==========================

Server Configuration (config.py)
--------------------------------

.. code-block:: Python

   class ServerConfig:
       # Network Settings
       BIND_ADDRESS = "*"          # Bind to all network interfaces
       TIMEOUT = 1000              # Socket timeout (milliseconds)
       HWM = 1000                  # High Water Mark
       
       # Router Port Allocation
       ROUTER_PORTS = {
           QuantumSystemType.SUPERCONDUCTING: 7000,
           QuantumSystemType.ION_TRAP: 7001,
           QuantumSystemType.NEUTRAL_ATOM: 7002,
           QuantumSystemType.PHOTONIC: 7003
       }
       
       # Pub Port Allocation
       PUB_PORTS = {
           QuantumSystemType.SUPERCONDUCTING: 8000,
           QuantumSystemType.ION_TRAP: 8001,
           QuantumSystemType.NEUTRAL_ATOM: 8002,
           QuantumSystemType.PHOTONIC: 8003
       }
       
       # Performance Settings
       THREAD_POOL_SIZE = 10       # Number of concurrent task worker threads
       MAX_QUEUE_SIZE = 200        # Maximum number of pending tasks
       
       # Simulation Times (milliseconds)
       COMPILE_TIME = 100          # Simulated compilation time
       RUN_TIME = 2000             # Simulated execution time
       POST_PROCESS_TIME = 50      # Simulated post-processing time
       
       # Logging Settings
       LOG_LEVEL = "INFO"
       LOG_FILE = "log/simulator.log"

Task Status Enumerations and Error Codes
========================================

Task Status Enumerations
------------------------

.. code-block:: Python

   class TaskStatus(Enum):
       UNKNOW_STATE = 0      # Unknown state
       PENDING = 1           # Task is queued
       COMPILING = 7         # Task is compiling
       COMPILED = 8          # Task compiled successfully
       RUNNING = 2           # Task is running
       SUCCESSED = 5         # Task completed successfully
       FAILED = 4            # Task failed
       NOTASK = 3            # Task does not exist
       RETRY = 6             # Task retry
       
       # Specific to Neutral Atom
       SUBMIT = 9            # Task submitted
       FINISH = 10           # Task finished
       CANCEL = 11           # Task cancelled
       SUBMITFAIL = 12       # Submission failed
       RUNFAIL = 13          # Execution failed
       WAITING = 14          # Task waiting

Error Codes
-----------

.. code-block:: Python

   class ErrorCode(Enum):
       NO_ERROR = 0                   # Success
       UNDEFINED_ERROR = 1            # Unknown error
       TASK_PARAM_ERROR = 2           # Task parameter error
       JSON_ERROR = 3                 # JSON parsing error
       QUEUE_FULL = 4                 # Queue is full
       AUTH_ERROR = 5                 # Authentication error
       TASK_ID_DUPLICATE = 10         # Duplicate Task ID
       TASK_ID_NOT_EXIST = 40         # Task ID does not exist

Client Examples
===============

Router-Dealer Client Example
----------------------------

.. code-block:: Python

   import zmq
   import json
   
   # Connect to the Router server
   context = zmq.Context()
   socket = context.socket(zmq.DEALER)
   socket.connect("tcp://localhost:7000")
   
   # Submit a task
   task = {
       "MsgType": "MsgTask",
       "SN": 1,
       "TaskId": "test-task-001",
       "ConvertQProg": "[[{'H': [0]}, {'Measure': [[0]]}]]",
       "Configure": {"Shot": 1000}
   }
   
   # Send the request
   socket.send_json(task)
   
   # Receive acknowledgement
   ack = socket.recv_json()
   print(f"ACK Message: {ack}")
   
   # Receive result (Asynchronous)
   result = socket.recv_json()
   print(f"Task Result: {result}")

Pub-Sub Client Example
----------------------

.. code-block:: Python

   import zmq
   import json
   
   # Connect to the Pub server
   context = zmq.Context()
   socket = context.socket(zmq.SUB)
   socket.connect("tcp://localhost:8000")
   
   # Subscribe to the topic 'simulator_topic' to receive all messages
   socket.setsockopt_string(zmq.SUBSCRIBE, b'simulator_topic')
   
   # Receive status updates
   while True:
       # Receive topic
       topic = socket.recv()
       
       # Receive operation type
       operation = socket.recv()
       
       # Receive data payload
       data = socket.recv_json()
       
       print(f"Received Message: topic={topic}, operation={operation}")
       print(f"Data: {data}")

Testing
=======

Start All Servers
-----------------

.. code-block:: bash

   python main.py --all

Use Test Client
---------------

.. code-block:: bash

   python test_client.py

Test a specific server:

.. code-block:: bash

   # Test Superconducting server
   python test_client.py --port 7000
   
   # Test Ion Trap server
   python test_client.py --port 7001
   
   # Test all servers
   python test_client.py --all

Logging
=======

Logs are stored in the "log/" directory. Log levels include:
* **DEBUG**: Detailed debugging information.
* **INFO**: General informational messages (Default).
* **WARNING**: Warning messages.
* **ERROR**: Error messages only.

Troubleshooting
===============

Port Already in Use
-------------------

If you encounter the "Address already in use" error:

.. code-block:: bash

   # Find the process occupying the port
   lsof -i :7000
   lsof -i :8000
   
   # Terminate the process
   kill -9 <PID>

Missing SN Field in Response
----------------------------

**Issue**: The response message does not contain the "SN" field or the "SN" value is incorrect.\\
**Solution**: Ensure you are running the latest code version:

.. code-block:: bash

   git pull  # Fetch the latest changes
   python main.py --all  # Restart the server

Token Refresh Failed (Ion Trap and Neutral Atom)
------------------------------------------------

**Issue**: "MsgUpdateToken" returns an empty or invalid token.\\
**Solution**:
1. Ensure the "RefreshToken" is sent in the "Authorization" header.
2. Verify that the refresh token was previously obtained via "MsgGetToken".
3. Verify that the token has not expired.

Task Status Not Published
-------------------------

**Issue**: The client does not receive task status updates via Pub-Sub.\\
**Solution**:
1. Verify that the Publisher server is running (Check ports 8000-8003).
2. Ensure the subscriber has subscribed to the correct topic.
3. Check if the firewall permits traffic on the Publisher server ports.

Pub-Sub Message Structure
=========================

The Publisher server uses a three-layer message structure:
enumerate
* **Topic**: Fixed to "b'simulator_topic'" for all messages.
* **Operation**: The message type (e.g., "b'task_status'", "b'chip_update'").
* **Data**: The JSON data payload.
enumerate

License
=======

This is a simulation server designed for development and testing purposes.

Technical Support
=================

If you have any questions or issues, please refer to the specific protocol documentation:
* Superconducting: "Superconducting_Communication_Protocol.md"
* Ion Trap: "Ion_Trap_Communication_Protocol.md"
* Neutral Atom: "Neutral_Atom_Communication_Protocol.md"
* Photonic: "Photonic_Communication_Protocol.md"
