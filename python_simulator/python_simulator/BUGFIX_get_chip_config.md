# Bug Fix: GetChipConfig 参数数量不匹配问题

## 问题描述

当客户端请求 GetChipConfig 接口时，服务器报错：

```
Error handling message: SuperconductingAdapter.build_get_chip_config_ack() 
takes 4 positional arguments but 6 were given
```

## 根本原因

在 `zmq_router_server.py` 中调用 `build_get_chip_config_ack()` 时传入了6个参数，但各个 adapter 的方法签名只接受4个参数。

**服务器调用代码（错误）：**
```python
reply = self.adapter.build_get_chip_config_ack(
    sn, chip_id, [], {},
    ErrorCode.TASK_PARAM_ERROR.value,  # 第5个参数 - 不支持
    f"Unknown chip ID: {chip_id}"      # 第6个参数 - 不支持
)
```

**Adapter 方法签名（原有）：**
```python
def build_get_chip_config_ack(sn: int, backend: int, point_label_list: list, 
                              chip_config: Dict) -> str:
    # 只有4个参数，没有错误码和错误信息
```

## 修复方案

为所有 adapter 的 `build_get_chip_config_ack()` 方法添加可选的错误码和错误信息参数：

```python
def build_get_chip_config_ack(sn: int, backend: int, point_label_list: list, 
                              chip_config: Dict, err_code: int = 0, 
                              err_info: str = "") -> str:
    """Build get chip config acknowledgment message"""
    return json.dumps({
        'MsgType': 'GetChipConfigAck',
        'SN': sn,
        'backend': backend,
        'PointLabelList': point_label_list,
        'ChipConfig': chip_config,
        'ErrCode': err_code,    # 使用参数而不是硬编码的0
        'ErrInfo': err_info     # 使用参数而不是硬编码的空字符串
    })
```

## 修改的文件

### 1. SuperconductingAdapter (`protocol_adapters/superconducting.py`)
- ✅ 添加 `err_code: int = 0` 参数
- ✅ 添加 `err_info: str = ""` 参数
- ✅ 使用参数而不是硬编码值

### 2. IonTrapAdapter (`protocol_adapters/ion_trap.py`)
- ✅ 添加 `err_code: int = 0` 参数
- ✅ 添加 `err_info: str = ""` 参数
- ✅ 保持 `version: str = "1.0"` 参数顺序

### 3. NeutralAtomAdapter (`protocol_adapters/neutral_atom.py`)
- ✅ 添加 `err_code: int = 0` 参数
- ✅ 添加 `err_info: str = ""` 参数
- ✅ 保持 `version: str = "1.0"` 参数顺序

### 4. PhotonicAdapter (`protocol_adapters/photonic.py`)
- ✅ 添加 `err_code: int = 0` 参数
- ✅ 添加 `err_info: str = ""` 参数

## 向后兼容性

使用默认参数值确保向后兼容性：

```python
# 旧代码仍然有效（使用默认错误码0和空错误信息）
adapter.build_get_chip_config_ack(sn, chip_id, [], config)

# 新代码可以传递错误信息
adapter.build_get_chip_config_ack(sn, chip_id, [], config, 
                                  ErrorCode.TASK_PARAM_ERROR.value, 
                                  "Unknown chip ID")
```

## 测试

### 测试1: 配置加载器测试
```bash
cd PilotPy/python_simulator
python test_chip_config.py
```
**结果：** ✅ 所有测试通过

### 测试2: 服务器接口测试
```bash
cd PilotPy/python_simulator
python test_get_chip_config_server.py
```
**测试内容：**
1. ✅ 请求有效的芯片配置（ChipID: 72）
2. ✅ 请求无效的芯片ID（错误处理）
3. ✅ 使用字符串类型的ChipID

## 使用示例

### 正常请求
```python
request = {
    "MsgType": "GetChipConfig",
    "SN": 100,
    "ChipID": 72
}
```

### 服务器响应（成功）
```json
{
  "MsgType": "GetChipConfigAck",
  "SN": 100,
  "backend": "72",
  "PointLabelList": [1],
  "ChipConfig": {
    "1": {
      "QuantumChipArch": {
        "Chip": "Superconducting_72",
        "QubitCount": 72,
        ...
      }
    }
  },
  "ErrCode": 0,
  "ErrInfo": ""
}
```

### 服务器响应（错误）
```json
{
  "MsgType": "GetChipConfigAck",
  "SN": 101,
  "backend": "INVALID_999",
  "PointLabelList": [],
  "ChipConfig": {},
  "ErrCode": 2,
  "ErrInfo": "Unknown chip ID: INVALID_999"
}
```

## 验证步骤

1. 启动服务器（确保端口7000可用）
   ```bash
   cd PilotPy/python_simulator
   python main.py
   ```

2. 在另一个终端运行测试
   ```bash
   cd PilotPy/python_simulator
   python test_get_chip_config_server.py
   ```

3. 检查输出，确认所有测试通过

## 影响范围

- ✅ 不影响现有功能
- ✅ 向后兼容
- ✅ 所有4个系统都已修复
- ✅ 支持正确的错误处理

## 相关文档

- `README_CHIP_CONFIG.md` - 芯片配置系统使用文档
- `test_chip_config.py` - 配置加载器测试
- `test_get_chip_config_server.py` - 服务器接口测试

## 修复日期

2026-02-05
