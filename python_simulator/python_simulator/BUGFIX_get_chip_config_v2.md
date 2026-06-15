# Bug Fix: GetChipConfig 接口无法正确返回数据

## 问题描述

当客户端请求 GetChipConfig 接口时，服务器无法正确返回芯片配置数据。

**错误日志示例：**
```
2026-02-05 16:15:30,710 - ZmqRouter-superconducting - INFO - Received message: {"MsgType": "GetChipConfig", "SN": 2, "ChipID": "72"}
2026-02-05 16:15:30,716 - ZmqRouter-superconducting - INFO - Sending reply: {"MsgType": "GetChipConfigAck", "SN": 2, "backend": "7000", "PointLabelList": [], "ChipConfig": {}, "ErrCode": 2, "ErrInfo": "Unknown chip ID: 7000"}
```

**问题现象：**
- 客户端发送的 ChipID 是 "72"
- 服务器却使用端口号 "7000" 去查找配置
- 导致找不到配置，返回错误

## 根本原因

### 原因1: 消息解析不完整

在 `zmq_router_server.py` 的 `handle_message` 方法中，对超导和光子系统使用了 `parse_task_message` 来解析消息：

```python
# 错误的代码
if self.system_type in [QuantumSystemType.ION_TRAP, QuantumSystemType.NEUTRAL_ATOM]:
    msg_data = self.adapter.parse_general_message(msg)
    # ...
else:
    # Superconducting and Photonic use flat structure
    msg_data = self.adapter.parse_task_message(msg)  # ❌ 不提取 ChipID！
```

**问题：** `parse_task_message` 只提取任务相关字段（msg_type, sn, task_id等），**不包括 `ChipID`**。

因此，`msg_data.get('ChipID')` 返回 `None`。

### 原因2: 错误的默认 ChipID

当 ChipID 为 None 时，代码使用了错误的默认值：

```python
# 错误的代码
chip_id = str(chip_id) if chip_id is not None else '72_2'  # ❌ 这个ID在映射中不存在
```

### 原因3: 心跳和其他接口也使用错误的 ChipID

多个接口使用端口号或硬编码值作为 ChipID：

```python
# _handle_heartbeat 中的错误代码
reply = self.adapter.build_heartbeat_ack(
    sn, self.port, "simulator_topic"  # ❌ 使用端口7000而不是芯片ID
)
```

## 修复方案

### 修复1: 统一使用 parse_general_message

修改 `handle_message` 方法，所有消息类型都使用 `parse_general_message` 来确保获取所有字段：

```python
# 修复后的代码
# Always use parse_general_message first to get all fields
msg_data = self.adapter.parse_general_message(msg)

# For task messages, also extract task-specific fields
if msg_data.get('msg_type') == 'MsgTask':
    task_data = self.adapter.parse_task_message(msg)
    msg_data.update(task_data)
```

### 修复2: 为每个系统配置正确的默认 ChipID

在 `__init__` 方法中添加系统特定的默认 ChipID：

```python
# Set default chip ID for each system type
self.default_chip_id = {
    QuantumSystemType.SUPERCONDUCTING: "72",
    QuantumSystemType.ION_TRAP: "IonTrap",
    QuantumSystemType.NEUTRAL_ATOM: "HanYuan_01",
    QuantumSystemType.PHOTONIC: "PQPUMESH8"
}[system_type]
```

### 修复3: 修正所有使用 ChipID 的方法

#### 修复 _handle_heartbeat:
```python
def _handle_heartbeat(self, msg_data: Dict) -> str:
    """Handle heartbeat message"""
    sn = msg_data.get('sn')
    
    # 使用正确的默认 chip ID
    if self.system_type == QuantumSystemType.SUPERCONDUCTING:
        reply = self.adapter.build_heartbeat_ack(
            sn, self.default_chip_id, "simulator_topic"
        )
    elif self.system_type == QuantumSystemType.PHOTONIC:
        reply = self.adapter.build_heartbeat_ack(sn, self.default_chip_id)
    else:
        reply = self.adapter.build_heartbeat_ack(sn, self.default_chip_id)
    
    return reply
```

#### 修复 _handle_get_update_time:
```python
def _handle_get_update_time(self, msg_data: Dict) -> str:
    """Handle get update time request"""
    sn = msg_data.get('sn')
    
    qubits = [0, 1, 2, 3, 4, 5]
    timestamps = [int(time.time() * 1000)] * len(qubits)
    
    if self.system_type == QuantumSystemType.SUPERCONDUCTING:
        reply = self.adapter.build_get_update_time_ack(
            sn, self.default_chip_id, qubits, timestamps
        )
    elif self.system_type == QuantumSystemType.NEUTRAL_ATOM:
        reply = self.adapter.build_get_update_time_ack(
            sn, int(time.time() * 1000)
        )
    else:
        reply = self.adapter.build_get_update_time_ack(
            sn, self.default_chip_id, qubits, timestamps
        )
    
    return reply
```

#### 修复 _handle_get_rb_data:
```python
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
    
    # 所有系统都使用正确的默认 chip ID
    reply = self.adapter.build_get_rb_data_ack(
        sn, self.default_chip_id, single_depth, double_depth,
        single_fidelity, double_fidelity
    )
    
    return reply
```

#### 修复 _handle_get_chip_config:
```python
def _handle_get_chip_config(self, msg_data: Dict) -> str:
    """Handle get chip configuration"""
    sn = msg_data.get('sn')
    chip_id = msg_data.get('ChipID')
    
    # 如果未提供，使用系统默认的 chip ID
    chip_id = str(chip_id) if chip_id is not None else self.default_chip_id
    
    self.logger.info(f"Loading chip config for ChipID: {chip_id}")
    
    # Load chip configuration using loader
    chip_config, point_label_list = self.chip_config_loader.get_chip_config(chip_id)
    
    if not chip_config:
        self.logger.warning(f"No configuration found for chip ID: {chip_id}")
        # Return error response
        if self.system_type == QuantumSystemType.SUPERCONDUCTING:
            reply = self.adapter.build_get_chip_config_ack(
                sn, chip_id, [], {},
                ErrorCode.TASK_PARAM_ERROR.value,
                f"Unknown chip ID: {chip_id}"
            )
        else:
            reply = self.adapter.build_get_chip_config_ack(
                sn, chip_id, {},
                ErrorCode.TASK_PARAM_ERROR.value,
                f"Unknown chip ID: {chip_id}"
            )
        return reply
    
    # Build response based on system type
    if self.system_type == QuantumSystemType.SUPERCONDUCTING:
        reply = self.adapter.build_get_chip_config_ack(
            sn, chip_id, point_label_list, chip_config
        )
    else:
        reply = self.adapter.build_get_chip_config_ack(
            sn, chip_id, chip_config
        )
    
    self.logger.info(f"Chip configuration sent for chip {chip_id} with {len(point_label_list)} work areas")
    
    return reply
```

## 修改的文件

### 1. zmq_router_server.py

**修改内容：**
- ✅ 添加 `default_chip_id` 属性，为每个系统配置正确的默认 ChipID
- ✅ 修改 `handle_message` 方法，统一使用 `parse_general_message`
- ✅ 修改 `_handle_heartbeat` 方法，使用 `default_chip_id` 而不是端口
- ✅ 修改 `_handle_get_update_time` 方法，使用 `default_chip_id`
- ✅ 修改 `_handle_get_rb_data` 方法，使用 `default_chip_id`
- ✅ 修改 `_handle_get_chip_config` 方法，使用 `default_chip_id` 作为默认值

## 测试验证

### 测试1: 验证 ChipID 提取

```bash
cd PilotPy/python_simulator
python test_chipid_fix.py
```

**预期结果：**
- ✓ ChipID 成功从消息中提取
- ✓ 支持字符串和数字类型的 ChipID
- ✓ 默认 ChipID 配置正确

### 测试2: 集成测试

```bash
# 启动服务器
cd PilotPy/python_simulator
python main.py --system superconducting

# 在另一个终端运行测试
cd PilotPy/python_simulator
python test_get_chip_config_server.py
```

**预期结果：**
- ✓ 请求 ChipID 72 返回正确的配置
- ✓ 错误的 ChipID 返回正确的错误信息
- ✓ 字符串类型的 ChipID 正常工作

### 测试3: 验证其他接口

```python
# 心跳消息
request = {"MsgType": "MsgHeartbeat", "SN": 100, "ChipID": 72}
# 应该返回 backend: "72" 而不是 "7000"

# UpdateTime 消息
request = {"MsgType": "GetUpdateTime", "SN": 101, "ChipID": 72}
# 应该返回 backend: "72" 而不是 "7000"

# RBData 消息
request = {"MsgType": "GetRBData", "SN": 102, "ChipID": 72}
# 应该返回 backend: "72" 而不是 "7000"
```

## 影响范围

- ✅ 修复了 GetChipConfig 接口无法正确返回数据的问题
- ✅ 修复了心跳接口使用错误 ChipID 的问题
- ✅ 修复了 UpdateTime 和 RBData 接口使用错误 ChipID 的问题
- ✅ 向后兼容，不影响现有功能
- ✅ 所有四个系统都已修复

## 系统默认 ChipID 映射

| 系统类型 | 默认 ChipID | 映射文件 |
|---------|------------|-----------|
| Superconducting (超导) | "72" | ChipArchConfig_72.json |
| Ion Trap (离子阱) | "IonTrap" | ChipArchConfig_IonTrap.json |
| Neutral Atom (中性原子) | "HanYuan_01" | ChipArchConfig_HanYuan_01.json |
| Photonic (光量子) | "PQPUMESH8" | ChipArchConfig_PQPUMESH8.json |

## 对比原始 BUGFIX 文档

原始的 `BUGFIX_get_chip_config.md` 文档描述的是参数数量不匹配的问题，但实际上真正的问题是：

1. **原始问题**: adapter 方法签名缺少错误参数
   - 状态: 已在之前的修复中解决

2. **真正的问题**: ChipID 无法正确提取和使用
   - 状态: 本次修复解决
   - 包括: 消息解析不完整、错误的默认值、多个接口使用错误 ChipID

## 修复日期

2026-02-05

## 相关文档

- `README_CHIP_CONFIG.md` - 芯片配置系统使用文档
- `test_chip_config.py` - 配置加载器测试
- `test_get_chip_config_server.py` - 服务器接口测试
- `test_chipid_fix.py` - ChipID 提取单元测试
