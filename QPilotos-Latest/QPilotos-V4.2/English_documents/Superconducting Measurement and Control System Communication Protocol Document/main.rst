Superconducting Quantum Chip Measurement and Control System Communication Protocol Document
===========================================================================================

:Author: OriginQ
:Date: Today

.. contents:: Table of Contents
   :depth: 3
   :local:



Communication Protocol
======================

ZeroMQ + JSON message body.

ZeroMQ is a mature and highly efficient third-party communication library that facilitates seamless communication between C++ and Python applications.

ZeroMQ supports various working modes. Currently, the integration between the PilotOS system and the measurement and control system operates similarly to a remote procedure call; therefore, the "Request-Reply model" (Router-Dealer) is utilized here.

Message Definitions (Router-Dealer Mode)
========================================

Dispatch Computing Task
-----------------------

**Function:** This message is used by the PilotOS system to dispatch computing tasks to the measurement and control system.

**Parameter Definitions:**
* **MsgType** ("String"): [Required] Message type, fixed as "MsgTask".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **TaskId** ("String"): [Required] Task ID.
* **ConvertQProg** ("String"): [Required] Quantum program; the instructions to be executed by the measurement and control system.
* **Configure.TaskPriority** ("Uint32_t"): [Optional, Default: 0] Task priority. Currently supports 2 levels: 0 (normal task) and 1 (high priority).
* **Configure.Shot** ("Uint32_t"): [Required] Number of repetitions (shots). Range: 100~10000; defaults to 1000 if the limit is exceeded.
* **Configure.IsExperiment** ("Bool"): [Optional] Indicates if the task is in experiment mode. true: Experiment mode; false: Non-experiment mode (normal user task). If this field is empty, it defaults to normal user task mode.
* **Configure.ClockCycle** ("Uint32_t"): [Optional] Execution timing sequence. Maximum circuit execution cycle, unit: microseconds. PilotOS automatically decides whether to pass this parameter based on the maximum execution cycle returned by the chip.
* **Configure.PointLabel** ("Uint32_t"): [Required] Application factory label, tentatively set to 128.

**Return Information:**
* **MsgType** ("String"): [Required] Message type, fixed as "MsgTaskAck".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information. Can be empty if there are no errors; required if an error occurs.

.. code-block:: json

   {
       "MsgType":"MsgTask",
       "SN":133,
       "TaskId":"11D919FA044846F3B4DF453A827AE901",
       "ConvertQProg":"QProg-instructions json-string.",
       "Configure":{
           "Shot":1000,
           "TaskPriority":1,
           "IsExperiment": true,
           "PointLabel":128
       }
   }

.. code-block:: json

   {
       "MsgType":"MsgTaskAck",
       "SN":133,
       "ErrCode":2,
       "ErrInfo":"configure error."
   }

Task Status Query
-----------------

**Function:** PilotOS sends a task status query to the measurement and control system to verify the current computation state. When PilotOS fails to receive calculation results for an extended period, it uses this message to check the task status, preventing PilotOS from waiting indefinitely during abnormal conditions.

**Parameter Definitions:**
* **MsgType** ("String"): [Required] Message type, fixed as "TaskStatus".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **TaskId** ("String"): [Required] Task ID.

**Return Information:**
* **MsgType** ("String"): [Required] Message type, fixed as "TaskStatusAck".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **TaskId** ("String"): [Required] Task ID.
* **TaskStatus** ("Uint32_t"): [Required] Task status, refer to the "Type Definitions" section.

.. code-block:: json

   {
       "MsgType":"TaskStatus",
       "SN":10086,
       "TaskId":"11D919FA044846F3B4DF453A827AE901"
   }

.. code-block:: json

   {
       "MsgType":"TaskStatusAck",
       "SN":10086,
       "TaskId":"11D919FA044846F3B4DF453A827AE901",
       "TaskStatus":3
   }

Return Computing Results
------------------------

**Function:** The measurement and control system returns the computing results to the PilotOS system.

**Parameter Definitions:**
* **MsgType** ("String"): [Required] Message type, fixed as "MsgTaskResult".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **TaskId** ("String"): [Required] Task ID.
* **ProbCount** ("Int Array"): [Required] Collapse counts; the number of state collapses corresponding to each Key.
* **NoteTime.CompileTime** ("Int"): [Required] Compilation time cost, unit: ms.
* **NoteTime.PendingTime** ("Int"): [Required] Queuing time cost, unit: ms.
* **NoteTime.MeasureTime** ("Int"): [Required] Measurement time cost, unit: ms.
* **NoteTime.PostProcessTime** ("Int"): [Required] Post-processing time cost, unit: ms.
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information.

**Return Information:**
* **MsgType** ("String"): [Required] Message type, fixed as "MsgTaskResultAck".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information.

.. code-block:: json

   {
       "MsgType":"MsgTaskResult",
       "SN":133,
       "TaskId":"11D919FA044846F3B4DF453A827AE901",
       "#key":"Quantum states are uniformly represented by hexadecimal strings",
       "Key": [["0x0","0x1"],["0x0","0x1"]],
       "ProbCount": [[111,656],[103,703]],
       "NoteTime":
       {
           "CompileTime":1,
           "PendingTime":94,
           "MeasureTime":2306,
           "PostProcessTime":105
       },
       "ErrCode":0,
       "ErrInfo":""
   }

Heartbeat Message
-----------------

**Function:** Used to probe the connection status between PilotOS and the measurement and control system. The service is maintained by the measurement system; PilotOS actively sends heartbeat packets, and upon receiving them, the measurement system returns a heartbeat acknowledgment.

**Parameter Definitions:**
* **MsgType** ("String"): [Required] Message type, fixed as "MsgHeartbeat".
* **SN** ("Uint32_t"): [Required] Heartbeat message sequence ID.
* **TimeStamp** ("Uint64_t"): [Required] 64-bit integer timestamp, in milliseconds.
* **ChipID** ("Uint32_t"): [Required] Chip name, e.g., 72.

**Return Information:**
* **MsgType** ("String"): [Required] Message type, fixed as "MsgHeartbeatAck".
* **SN** ("Uint32_t"): [Required] Heartbeat message sequence ID.
* **backend** ("Uint32_t"): [Required] Backend chip ID.
* **TimeStamp** ("Uint64_t"): [Required] 64-bit integer timestamp, in milliseconds.
* **Topic** ("String"): [Required] Subscribed message topic.

.. code-block:: json

   {
       "MsgType":"MsgHeartbeat",
       "SN":133,
       "ChipID":72,
       "TimeStamp":1638769359507
   }

Get Chip Calibration Time
-------------------------

**Function:** The user actively fetches the timestamp of the last chip calibration performed by the measurement and control system. Returned by the measurement system.

**Parameter Definitions:**
* **MsgType** ("String"): [Required] Message type, fixed as "GetUpdateTime".
* **SN** ("Uint32_t"): [Required] Message sequence ID.

**Return Information:**
* **MsgType** ("String"): [Required] Message type, fixed as "GetUpdateTimeAck".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **backend** ("Uint32_t"): [Required] Backend chip ID.
* **LastUpdateTime.qubit** ("Uint32_t Array"): [Required] Qubit names for the chip calibration timestamp (integer data).
* **LastUpdateTime.timeStamp** ("Uint64_t Array"): [Required] Timestamps corresponding to the qubits (64-bit integer timestamp, in ms).
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information.

.. code-block:: json

   {
       "MsgType":"GetUpdateTime",
       "SN":133
   }

Get RB Experimental Data
------------------------

**Function:** The user actively fetches Randomized Benchmarking (RB) experimental data. Returned by the measurement system.

**Parameter Definitions:**
* **MsgType** ("String"): [Required] Message type, fixed as "GetRBData".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **ChipID** ("Uint32_t"): [Required] Chip name, e.g., 72.

**Return Information:**
* **MsgType** ("String"): [Required] Message type, fixed as "GetRBDataAck".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **backend** ("Uint32_t"): [Required] Backend chip ID.
* **SingleGateCircuitDepth** ("Uint32_t Array"): [Required] Maximum circuit depth for the single-gate RB experiment.
* **DoubleGateCircuitDepth** ("Uint32_t Array"): [Required] Maximum circuit depth for the double-gate RB experiment.
* **SingleGateFidelity** ("Object"): [Required] Single-qubit fidelity (string-type map).
* **DoubleGateFidelity** ("Object"): [Required] Two-qubit fidelity (string-type map).
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information.

.. code-block:: json

   {
       "MsgType":"GetRBData",
       "SN":133,
       "ChipID":72
   }

Get Chip Configuration Parameters
---------------------------------

**Function:** Fetches chip configuration parameters (JSON data), returned by the measurement system.

**Parameter Definitions:**
* **MsgType** ("String"): [Required] Message type, fixed as "GetChipConfig".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **ChipID** ("Uint32_t"): [Required] Chip name, e.g., 72.

**Return Information:**
* **MsgType** ("String"): [Required] Message type, fixed as "GetChipConfigAck".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **backend** ("Uint32_t"): [Required] Backend chip ID.
* **PointLabelList** ("Uint32_t Array"): [Required] List of workspace modes supported by the current chip.
* **ChipConfig** ("String"): [Required] Chip parameter JSON string.
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information.

.. code-block:: json

   {
       "MsgType":"GetChipConfig",
       "SN":133,
       "ChipID":72
   }

Request Specific Task Result
----------------------------

**Function:** Used in abnormal scenarios where PilotOS fails to correctly receive the computing results from the measurement system. PilotOS actively requests the computation result data for a specified task.

**Parameter Definitions:**
* **MsgType** ("String"): [Required] Message type, fixed as "GetTaskResult".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **TaskId** ("String"): [Required] Task ID.

**Return Information:**
The return result format is consistent with the one detailed in the "2.3 Return Computing Results" section, but the "TaskResult" and "FidelityMat" fields are removed. \\
Note: The message sequence number in the returned result will be identical to the sequence number of the request message.

.. code-block:: json

   {
       "MsgType":"GetTaskResult",
       "SN":134,
       "TaskId":"11D919FA044846F3B4DF453A827AE901"
   }

Set Exclusive VIP Time
----------------------

**Function:** Used in specific scenarios where PilotOS configures an exclusive computing block, ensuring tasks submitted during this window do not require queuing.

**Parameter Definitions:**
* **MsgType** ("String"): [Required] Message type, fixed as "SetVip".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **OffsetTime** ("Uint64_t"): [Required] Offset time relative to the current system time (unit: seconds).
* **ExclusiveTime** ("Uint64_t"): [Required] Duration of the exclusive time block (unit: seconds).

**Return Information:**
* **MsgType** ("String"): [Required] Message type, fixed as "SetVipAck".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information.

.. code-block:: json

   {
       "MsgType":"SetVip",
       "SN":134,
       "OffsetTime":120,
       "ExclusiveTime":600
   }

Release Exclusive VIP Time
--------------------------

**Function:** Used to release the exclusive computing block operation and restore normal mode after tasks within the exclusive VIP period are completed.

**Parameter Definitions:**
* **MsgType** ("String"): [Required] Message type, fixed as "ReleaseVip".
* **SN** ("Uint32_t"): [Required] Message sequence ID.

**Return Information:**
* **MsgType** ("String"): [Required] Message type, fixed as "ReleaseVipAck".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information.

.. code-block:: json

   {
       "MsgType":"ReleaseVip",
       "SN":135
   }

Subscribe Messages (PUB-SUB Mode)
=================================

Task Status
-----------

**Function:** When the calculation phase of a task updates, the measurement system pushes real-time task status info.

**Operation**: Fixed as bytes: "task_status".

**Pushed Message Format:**
* **MsgType** ("String"): [Required] Message type, fixed as "TaskStatus".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **TaskId** ("String"): [Required] Task ID.
* **TaskStatus** ("Uint32_t"): [Required] Task status, refer to the task status definitions.

.. code-block:: json

   {
       "MsgType":"TaskStatus",
       "SN":0,
       "TaskId":"11D919FA044846F3B4DF453A827AE901",
       "TaskStatus":3
   }

Chip Configuration Update Flag
------------------------------

**Function:** After chip parameters change, the measurement system pushes a message notifying PilotOS that it can send a fetch request via Router-Dealer mode to query the updated chip configuration info.

**Operation**: Fixed as bytes: "chip_update".

**Pushed Message Format:**
* **UpdateFlag** ("Bool"): [Required] Update identifier.
* **LastUpdateTime** ("Uint64_t"): [Required] Last update timestamp.

.. code-block:: json

   {
       "UpdateFlag":true,
       "LastUpdateTime": 1705307288685
   }

Chip Resource Status
--------------------

**Function:** During task computation in multi-threading mode, whenever chip resources change (locked or released), the measurement service pushes detailed thread data to PilotOS (displaying the qubit usage of each measurement thread). QPilot only needs to monitor the "use_bits" field for each thread (t0, t1, t2...).

**Operation**: Fixed as bytes: "probe".

**Pushed Message Format:**
* **core_thread.t0** ("Object"): [Required] Thread name of the measurement service.
* **core_thread.t0.use_bits** ("String Array"): [Required] All qubits currently utilized by the thread.

.. code-block:: json

   {
       "inst_status": 1,
       "linked": 1,
       "timestamp": 1695182448.7963016,
       "scheduler": { "status": "InitialState", "queue_len": 3 },
       "core_status": { "empty_thread": 3, "pause_read": 0, "thread_num": 5 },
       "core_thread": {
           "t0": {
               "status": "waiting",
               "thread_id": "t0",
               "task_id": "650a6e6f197b42e9aeaad6d6",
               "start_time": 1695182447.5371444,
               "user": "admin3",
               "use_bits": ["q56", "q18", "q68", "q69", "q6", "q2", "q67"]
           },
           "t1": { "status": "ready", "use_bits": [] }
       }
   }

Automatic Calibration Start Information
---------------------------------------

**Function:** During automatic calibration routines, the measurement system pushes calibration qubit info to PilotOS; the qubits undergoing calibration are marked unavailable during this period.

**Operation**: Fixed as bytes: "calibration_start".

**Pushed Message Format:**
* **qubits** ("String Array"): [Required] Single-qubit info undergoing calibration.
* **couplers** ("String Array"): [Required] Couplers.
* **pairs** ("String Array"): [Required] Qubit pair info undergoing calibration.
* **discriminators** ("String Array"): [Required] Discriminators.
* **point_label** ("Int"): [Required] Indicates which label the current calibration is applied to.

Automatic Calibration End Information
-------------------------------------

**Function:** Upon successful completion of the calibration, a completion message is pushed to PilotOS, and the qubits become available again.

**Operation**: Fixed as bytes: "calibration_done".

**Pushed Message Format:**
* **qubits** ("String Array"): [Required] Calibrated single-qubit info.
* **couplers** ("String Array"): [Required] Couplers.
* **pairs** ("String Array"): [Required] Calibrated qubit pair info.
* **discriminators** ("String Array"): [Required] Discriminators.

Chip Maintenance Information
----------------------------

**Function:** Receives chip maintenance start and end notifications to trigger automatic pausing in PilotOS. If the maintenance period exceeds 2 hours, PilotOS pushes an offline maintenance notification to the cloud platform; if it is under 2 hours, only PilotOS pauses, while the cloud platform remains online normally.

**Operation**: Fixed as bytes: "chip_protect".

**Pushed Message Format:**
* **ProtectFlag** ("Bool"): [Required] Maintenance flag. true means maintenance started, false means maintenance ended.
* **DurativeTime** ("Uint64_t"): [Required] Maintenance duration (unit: minutes).
* **LastTime** ("Uint64_t"): [Required] Timestamp.

Type Definitions
================

Task Status Types
-----------------

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - **Status Code**
     - **Description**
   * - 0
     - Unknown status
   * - 1
     - Task is still queuing
   * - 2
     - Task is running
   * - 3
     - Cannot find corresponding task information
   * - 4
     - Task computation failed
   * - 5
     - Task computation completed
   * - 6
     - Task resent
   * - 7
     - Task is compiling
   * - 8
     - Task compilation completed

Error Code Types
----------------

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - **Error Code**
     - **Description**
   * - 0
     - No error
   * - 1
     - Unknown error
   * - 2
     - Computing task parameter error
   * - 3
     - JSON error
   * - 4
     - Task queue full (returned when PilotOS sends more than 200 tasks)

Instruction Definitions
=======================

Supported Basic Gate Types and Parameter Descriptions
-----------------------------------------------------

* **RPhi** (Single Gate)
  * **qubit** ("uint32_t"): Target qubit
  * **axis** ("double"): Rotation axis phase
  * **angle** ("double"): Rotation angle theta
  * **order** ("uint32_t"): Timing sequence

* **ECHO** (Single Gate)
  * **qubit** ("uint32_t"): Target qubit
  * **order** ("uint32_t"): Timing sequence

* **IDLE** (Single Gate)
  * **qubit** ("uint32_t"): Target qubit
  * **delay** ("uint32_t"): Delay, variable, affects subsequent gate timing
  * **order** ("uint32_t"): Timing sequence

* **CZ** (Double Gate)
  * **qubit** ("uint32_t"): Target qubit
  * **ctrl** ("uint32_t"): Control qubit
  * **order** ("uint32_t"): Timing sequence

Instruction Format
------------------

The instruction format utilizes nested JSON array objects. The innermost gate object contains a combination of a basic gate described in Section 5.1 with its parameters, plus a Measure gate object, formatted as follows:

.. code-block:: json

   {"Gate": [Qubit..., Other parameters..., Execution sequence]}

The Measure gate object is formatted as follows:

.. code-block:: json

   {"Measure": [[Qubit...], Execution sequence]}

A complete single-circuit instruction is generally composed of multiple basic gate objects and a Measure gate object wrapped within a JSON array, formatted as follows:

.. code-block:: json

   [
       {"Gate0": [Qubit..., Other parameters..., Execution sequence]},
       {"Gate1": [Qubit..., Other parameters..., Execution sequence]},
       ...
       {"Gaten": [Qubit..., Other parameters..., Execution sequence]},
       {"Measure": [[Qubit...], Execution sequence]}
   ]

A task is usually composed of instructions from multiple circuits, which means a collection of the single-circuit instructions mentioned above. A complete instruction for a task is formatted as follows:

.. code-block:: json

   [
       [
           {"Gate0": [Qubit..., Other parameters..., Execution sequence]},
           {"Gate1": [Qubit..., Other parameters..., Execution sequence]},
           ...
           {"Measure": [[Qubit...], Execution sequence]}
       ],
       ...
       [
           {"Gate0": [Qubit..., Other parameters..., Execution sequence]},
           {"Gate1": [Qubit..., Other parameters..., Execution sequence]},
           ...
           {"Measure": [[Qubit...], Execution sequence]}
       ]
   ]
