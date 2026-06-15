Neutral Atom Measurement and Control System Communication Protocol Document
===========================================================================

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
* **ConvertQProg** ("String"): [Required] Quantum program; the instructions to be executed by the measurement and control system (Neutral Atom platform specific format).
* **Configure.TaskPriority** ("Uint32_t"): [Optional, Default: 0] Task priority. Currently supports 2 levels: 0 (normal task) and 1 (high priority).
* **Configure.Shot** ("Uint32_t"): [Required] Number of repetitions (shots). Range: 100~10000; defaults to 1000 if the limit is exceeded.
* **Configure.IsExperiment** ("Bool"): [Optional] Indicates if the task is in experiment mode. true: Experiment mode; false: Non-experiment mode (normal user task mode). If this field is empty, it defaults to normal user task mode.
* **Configure.ClockCycle** ("Uint32_t"): [Optional] Execution timing sequence. Maximum circuit execution cycle, unit: microseconds. PilotOS automatically decides whether to pass this parameter based on the maximum execution cycle returned by the measurement and control system. For example, if the measurement and control system returns a normal execution cycle of 100us and a maximum of 500us for the current chip, and if a task's execution timing is greater than 100us but less than 500us, this parameter is adjusted according to the specific circuit timing; if the user circuit execution timing is less than 100us, this parameter does not need to be passed.
* **Configure.PointLabel** ("Uint32_t"): [Required] Application factory label, tentatively set to 128.

**Return Information:**
* **MsgType** ("String"): [Required] Message type, fixed as "MsgTaskAck".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information. Can be empty if there are no errors; required if an error occurs.

.. code-block:: text

   {
       "MsgType":"MsgTask",
       "SN":133,
       "TaskId":"11D919FA044846F3B4DF453A827AE901",
       "ConvertQProg":"Neutral Atom platform specific instruction format",
       "Configure":{
           "Shot":1000,
           "TaskPriority":1,
           "IsExperiment": true,
           "PointLabel":128
       }
   }

.. code-block:: text

   {
       "MsgType":"MsgTaskAck",
       "SN":133,
       "ErrCode":2,
       "ErrInfo":"configure error."
   }

Task Status Query
-----------------

**Function:** PilotOS sends a task status query to the measurement and control system to verify the current task computation state. When PilotOS fails to receive calculation results for an extended period, it uses this message to query the task status from the measurement and control system, preventing PilotOS from waiting indefinitely during abnormal conditions.

**Parameter Definitions:**
* **MsgType** ("String"): [Required] Message type, fixed as "TaskStatus".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **TaskId** ("String"): [Required] Task ID.

**Return Information:**
* **MsgType** ("String"): [Required] Message type, fixed as "TaskStatusAck".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **TaskId** ("String"): [Required] Task ID.
* **TaskStatus** ("Uint32_t"): [Required] Task status, refer to the "Type Definitions" section.

.. code-block:: text

   {
       "MsgType":"TaskStatus",
       "SN":10086,
       "TaskId":"11D919FA044846F3B4DF453A827AE901"
   }

.. code-block:: text

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
* **NoteTime.CompileTime** ("Int"): [Required] Compilation time cost information, unit: ms.
* **NoteTime.PendingTime** ("Int"): [Required] Queuing time cost information, unit: ms.
* **NoteTime.MeasureTime** ("Int"): [Required] Measurement time cost information, unit: ms.
* **NoteTime.PostProcessTime** ("Int"): [Required] Post-processing time cost information, unit: ms.
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information. Can be empty if there are no errors; required if an error occurs.

**Return Information:**
* **MsgType** ("String"): [Required] Message type, fixed as "MsgTaskResultAck".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information. Can be empty if there are no errors; required if an error occurs.

.. code-block:: text

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

.. code-block:: text

   {
       "MsgType":"MsgTaskResultAck",
       "SN":133,
       "ErrCode":3,
       "ErrInfo":"data error."
   }

Heartbeat Message
-----------------

**Function:** Used by the user to probe the connection status between PilotOS and the measurement and control system. The system service is maintained by the measurement and control system; PilotOS actively sends heartbeat packets, and upon receiving the heartbeat packet, the measurement system sends a heartbeat acknowledgment.

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

.. code-block:: text

   {
       "MsgType":"MsgHeartbeat",
       "SN":133,
       "ChipID":72,
       "TimeStamp":1638769359507
   }

.. code-block:: text

   {
       "MsgType":"MsgHeartbeatAck",
       "SN":133,
       "backend":72,
       "TimeStamp":1638769359517,
       "Topic":"Y4-231011-Design_Validation-72bit_300pin_V9.2.3_Base-3#_|_Y4-231011-Design_Validation-72bit_300pin_V9.2.3_Base-3#"
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
* **LastUpdateTime.timeStamp** ("Uint64_t Array"): [Required] Timestamps corresponding to the qubits (64-bit integer timestamp, in milliseconds).
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information. Can be empty if there are no errors; required if an error occurs.

.. code-block:: text

   {
       "MsgType":"GetUpdateTime",
       "SN":133
   }

.. code-block:: text

   {
       "MsgType":"GetUpdateTimeAck",
       "SN":133,
       "backend":72,
       "LastUpdateTime":
       {
           "qubit":[43,45,46,48,49,52,53,54,60],
           "timeStamp":[1687243363189,1687243363189,1687243363189,
           1687243363189,1687243363189,1687243363189,
           1687243363189,1687243363189,1687243363189]
       },
       "ErrCode":0,
       "ErrInfo":""
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
* **SingleGateFidelity** ("Object"): [Required] Single-qubit fidelity (string-type map, where key is the qubit name and value is the corresponding fidelity).
* **DoubleGateFidelity** ("Object"): [Required] Two-qubit fidelity (string-type map, where key is the qubit pair name and value is the corresponding fidelity).
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information. Can be empty if there are no errors; required if an error occurs.

.. code-block:: text

   {
       "MsgType":"GetRBData",
       "SN":133,
       "ChipID":72
   }

.. code-block:: text

   {
       "MsgType":"GetRBDataAck",
       "SN":133,
       "backend":72,
       "SingleGateCircuitDepth":[50,50,50,50,50,50,50,50,50,50],
       "DoubleGateCircuitDepth":[0,50,50,50,50,50,50,0],
       "SingleGateFidelity":
       {
           "qubit":["45","46","48","52"],
           "fidelity":[0.9,0.9,0.9,0.9]
       },
       "DoubleGateFidelity":
       {
           "qubitPair":["45-46","46-52","48-54","52-53"],
      	    "fidelity":[0.9,0.9,0.9,0.9]
       },
       "ErrCode":0,
       "ErrInfo":"" 
   }

Get Chip Configuration Parameters
---------------------------------

**Function:** Fetches chip configuration parameters (JSON data), returned by the measurement and control system.

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
* **ErrInfo** ("String"): [Conditional] Error information. Can be empty if there are no errors; required if an error occurs.

.. code-block:: text

   {
       "MsgType":"GetChipConfig",
       "SN":133,
       "ChipID":72
   }

.. code-block:: text

   {
       "MsgType":"GetChipConfigAck",
       "SN":133,
       "backend":72,
       "PointLabelList":[1,2],
       "ChipConfig":{
         "1":"QuantumChipArch.json related configuration info",
         "2":"QuantumChipArch.json related configuration info"
       },
       "ErrCode":0,
       "ErrInfo":""
   }

Request Specific Task Result
----------------------------

**Function:** Used in abnormal scenarios where PilotOS fails to correctly receive the computing results returned by the measurement and control system, allowing PilotOS to actively request the computation result data for a specified task from the measurement system.

**Parameter Definitions:**
* **MsgType** ("String"): [Required] Message type, fixed as "GetTaskResult".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **TaskId** ("String"): [Required] Task ID.

**Return Information:**
The return result format is consistent with the return result format detailed in the "2.3 Return Computing Results" section, but the "TaskResult" and "FidelityMat" fields are removed.
**Note: The message sequence number in the returned result will be identical to the sequence number of the request message.**

.. code-block:: text

   {
       "MsgType":"GetTaskResult",
       "SN":134,
       "TaskId":"11D919FA044846F3B4DF453A827AE901"
   }

.. code-block:: text

   {
       "MsgType":"MsgTaskResult",
       "SN":134,
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

Set Exclusive VIP Time
----------------------

**Function:** Used in specific requirement scenarios where PilotOS configures an exclusive computing block, ensuring tasks submitted during this exclusive time window do not require queuing.

**Parameter Definitions:**
* **MsgType** ("String"): [Required] Message type, fixed as "SetVip".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **OffsetTime** ("Uint64_t"): [Required] Offset time relative to the current system time (unit: seconds).
* **ExclusiveTime** ("Uint64_t"): [Required] Duration of the exclusive time block (unit: seconds).

**Return Information:**
* **MsgType** ("String"): [Required] Message type, fixed as "SetVipAck".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **ErrCode** ("Uint32_t"): [Required] Error code.
* **ErrInfo** ("String"): [Conditional] Error information. Can be empty if there are no errors; required if an error occurs.

.. code-block:: text

   {
       "MsgType":"SetVip",
       "SN":134,
       "OffsetTime":120,
       "ExclusiveTime":600
   }

.. code-block:: text

   {
       "MsgType":"SetVipAck",
       "SN":134,
       "ErrCode":0,
       "ErrInfo":""
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
* **ErrInfo** ("String"): [Conditional] Error information. Can be empty if there are no errors; required if an error occurs.

.. code-block:: text

   {
       "MsgType":"ReleaseVip",
       "SN":135
   }

.. code-block:: text

   {
       "MsgType":"ReleaseVipAck",
       "SN":135,
       "ErrCode":0,
       "ErrInfo":""
   }

Subscribe Messages (PUB-SUB Mode)
=================================

Task Status
-----------

**Function:** When the calculation phase of a task updates, the measurement system pushes real-time task status information.

**Operation:** Fixed as bytes: "task_status".

**Pushed Message Format:**
* **MsgType** ("String"): [Required] Message type, fixed as "TaskStatus".
* **SN** ("Uint32_t"): [Required] Message sequence ID.
* **TaskId** ("String"): [Required] Task ID.
* **TaskStatus** ("Uint32_t"): [Required] Task status, refer to the task status definitions.

.. code-block:: text

   {
       "MsgType":"TaskStatus",
       "SN":0,
      	"TaskId":"11D919FA044846F3B4DF453A827AE901",
       "TaskStatus":3
   }

Chip Configuration Update Flag
------------------------------

**Function:** After chip parameters change, the measurement and control integrated machine pushes a message notifying PilotOS that it can send a fetch request via Router-Dealer mode to query the latest chip configuration information.

**Operation:** Fixed as bytes: "chip_update".

**Pushed Message Format:**
* **UpdateFlag** ("Bool"): [Required] Update identifier.
* **LastUpdateTime** ("Uint64_t"): [Required] Last update time.

.. code-block:: text

   {
       "UpdateFlag":true,
       "LastUpdateTime": 1705307288685
   }

Chip Resource Status
--------------------

**Function:** During task computation in multi-threading mode on the measurement and control integrated machine, whenever chip resources change (locked or released), the measurement and control service pushes detailed thread data to PilotOS (displaying the qubit usage of each measurement service thread); QPilot only needs to monitor the "use_bits" field for each thread (t0, t1, t2...).

**Operation:** Fixed as bytes: "probe".

**Pushed Message Format:**
* **core_thread.t0** ("Object"): [Required] Thread name of the measurement service.
* **core_thread.t0.use_bits** ("String Array"): [Required] All qubits for the current thread.

.. code-block:: text

   {
       "inst_status": 1,
       "linked": 1,
       "timestamp": 1695182448.7963016,
       "scheduler": {
           "status": "InitialState",
           "queue_len": 3
       },
       "core_status": {
           "empty_thread": 3,
           "pause_read": 0,
           "thread_num": 5
       },
       "core_thread": {
           "t0": {
               "status": "waiting",
               "thread_id": "t0",
               "task_id": "650a6e6f197b42e9aeaad6d6",
               "start_time": 1695182447.5371444,
               "user": "admin3",
               "env_bits": [
                   "<c45-46||0>",
                   "<q62||0>",
                   "<c40-46||0>",
                   "<q59||1>"],
               "use_bits": [
                   "q56",
                   "q18",
                   "q68",
                   "q69",
                   "q6",
                   "q2",
                   "q67"]
           },
           "t1": {
               "status": "ready",
               "task_id": null,
               "start_time": null,
               "user": null,
               "env_bits": [],
               "use_bits": []
           },
           "t2": {
               "status": "ready",
               "task_id": null,
               "start_time": null,
               "user": null,
               "env_bits": [],
               "use_bits": []
           },
           "t3": {
               "status": "waiting",
               "thread_id": "t3",
               "task_id": "650a6e6e197b42e9aeaad6d0",
               "start_time": 1695182446.8370538,
               "user": "admin3",
               "env_bits": [
                   "<q56||1>",
                   "<c45-46||2>",
                   "<q62||2>",
                   "<c40-46||2>",
                   "<c56-57||2>",
                   "<c43-44||2>",
                   "<c44-45||2>"
               ],
               "use_bits": [
                   "q59",
                   "q30",
                   "q50",
                   "q33",
                   "q47",
                   "q19",
                   "q38"
               ]
           },
           "t4": {
               "status": "ready",
               "task_id": null,
               "start_time": null,
               "user": null,
               "env_bits": [],
               "use_bits": []
           }
       }
   }

Automatic Calibration Start Information
---------------------------------------

**Function:** During automatic calibration routines on the measurement and control integrated machine, it pushes calibration qubit information to PilotOS; the qubits undergoing calibration are unavailable during this time period.

**Operation:** Fixed as bytes: "calibration_start".

**Pushed Message Format:**
* **qubits** ("String Array"): [Required] Single-qubit information undergoing calibration.
* **couplers** ("String Array"): [Required] Couplers.
* **pairs** ("String Array"): [Required] Qubit pair information undergoing calibration.
* **discriminators** ("String Array"): [Required] Discriminators.
* **point_label** ("Int"): [Required] Used to indicate which label the current calibration is applied to.

.. code-block:: text

   {
       "config_flag": false,
       "qubits":["q0", "q1", "q2", "q3"],
       "couplers":["c0-1", "c11-12", "c2-3"],
       "pairs": ["q0q1", "q2q3"],
       "discriminators":["q0_01.bin", "q1_01.bin", "q2_01.bin", "q3_01.bin"],
       "point_label": 2
   }

Automatic Calibration End Information
-------------------------------------

**Function:** Upon successful completion of the calibration, a completion message is pushed to PilotOS, and the qubits resume availability.

**Operation:** Fixed as bytes: "calibration_done".

**Pushed Message Format:**
* **qubits** ("String Array"): [Required] Calibrated single-qubit information.
* **couplers** ("String Array"): [Required] Couplers.
* **pairs** ("String Array"): [Required] Calibrated qubit pair information.
* **discriminators** ("String Array"): [Required] Discriminators.

.. code-block:: text

   {
       "qubits":["q0", "q1", "q2", "q3"],
       "couplers":["c0-1", "c11-12", "c2-3"],
       "pairs": ["q0q1", "q2q3"],
       "discriminators":["q0", "q1", "q2", "q3"],
       "config_flag":true,
       "point_label": 2
   }

Chip Maintenance Information
----------------------------

**Function:** Receives chip maintenance start and end notifications to implement automatic pausing in PilotOS. **If the maintenance period exceeds 2 hours, PilotOS pushes an offline maintenance notification to the cloud platform; if the maintenance period does not exceed 2 hours, only PilotOS pauses, while the cloud platform remains online normally.**

**Operation:** Fixed as bytes: "chip_protect".

**Pushed Message Format:**
* **ProtectFlag** ("Bool"): [Required] Maintenance flag. true means maintenance started, false means maintenance ended.
* **DurativeTime** ("Uint64_t"): [Required] Maintenance duration (unit: minutes).
* **LastTime** ("Uint64_t"): [Required] Timestamp.

.. code-block:: text

   {
     "ProtectFlag":true,
     "DurativeTime":10,
     "LastTime":1705307288685
   }

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

The basic gate types for the Neutral Atom platform differ from those of the superconducting platform. The "ConvertQProg" field maintains a dedicated format for the Neutral Atom platform and is not forced to be consistent with the superconducting platform.

Supported neutral atom gates include: U3, CZ, and other quantum gate operations specific to neutral atoms.
