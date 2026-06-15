# 芯片配置加载系统使用文档

## 概述

本系统实现了基于文件的芯片配置管理，支持从 `ChipConfig/` 目录动态加载芯片配置，并支持多工作区配置。

## 文件结构

```
PilotPy/python_simulator/
├── ChipConfig/
│   ├── chip_config_mapping.json      # 芯片ID映射表
│   ├── ChipArchConfig_72.json         # 超导72比特芯片
│   ├── ChipArchConfig_HanYuan_01.json # 汉源1号（中性原子）
│   ├── ChipArchConfig_IonTrap.json    # 离子阱芯片
│   └── ChipArchConfig_PQPUMESH8.json  # 光量子8比特芯片
├── chip_config_loader.py              # 配置加载器模块
├── zmq_router_server.py               # 已集成配置加载器
└── test_chip_config.py                # 测试脚本
```

## 芯片ID映射规则

ChipID 从配置文件名自动提取：
- 文件命名格式：`ChipArchConfig_<ChipID>.json`
- ChipID 类型：字符串
- 例如：
  - `ChipArchConfig_72.json` → ChipID = "72"
  - `ChipArchConfig_HanYuan_01.json` → ChipID = "HanYuan_01"

## 支持的芯片

### 1. 超导量子比特
- **ChipID**: "72"
- **芯片名称**: Superconducting_72
- **量子比特数**: 72
- **配置文件**: ChipArchConfig_72.json

### 2. 中性原子
- **ChipID**: "HanYuan_01"
- **芯片名称**: HanYuan_01（汉源1号）
- **量子比特数**: 225
- **配置文件**: ChipArchConfig_HanYuan_01.json

### 3. 离子阱
- **ChipID**: "IonTrap"
- **芯片名称**: IonTrap
- **量子比特数**: 6
- **配置文件**: ChipArchConfig_IonTrap.json

### 4. 光量子
- **ChipID**: "PQPUMESH8"
- **芯片名称**: PQPUMESH8
- **量子比特数**: 3
- **配置文件**: ChipArchConfig_PQPUMESH8.json

## 映射表配置

`chip_config_mapping.json` 结构：

```json
{
  "mappings": {
    "<ChipID>": {
      "chip_id": "<ChipID>",
      "chip_name": "<芯片名称>",
      "system_type": "<系统类型>",
      "work_areas": {
        "<工作区标签>": {
          "config_file": "<配置文件名>",
          "description": "<描述>"
        }
      },
      "default_work_area": "<默认工作区>"
    }
  }
}
```

### 系统类型
- `superconducting`: 超导量子系统
- `neutral_atom`: 中性原子量子系统
- `ion_trap`: 离子阱量子系统
- `photonic`: 光量子系统

## API 使用

### 1. 初始化配置加载器

```python
from chip_config_loader import ChipConfigLoader

# 使用默认路径（ChipConfig目录）
loader = ChipConfigLoader()

# 或指定自定义路径
loader = ChipConfigLoader(config_dir="/path/to/config/dir")
```

### 2. 获取芯片配置

```python
# 获取指定芯片的配置
chip_id = "72"
chip_config, point_label_list = loader.get_chip_config(chip_id)

# chip_config: {"1": {完整配置对象}, "2": {...}}
# point_label_list: [1, 2, ...]
```

### 3. 获取可用芯片列表

```python
chips = loader.get_available_chips()
for chip in chips:
    print(f"Chip ID: {chip['chip_id']}")
    print(f"Name: {chip['chip_name']}")
    print(f"Type: {chip['system_type']}")
```

### 4. 获取芯片信息

```python
info = loader.get_chip_info("72")
# 返回映射表中的芯片信息，不加载完整配置
```

## 服务器集成

`zmq_router_server.py` 已自动集成配置加载器：

```python
def _handle_get_chip_config(self, msg_data: Dict) -> str:
    """处理获取芯片配置请求"""
    sn = msg_data.get('sn')
    chip_id = msg_data.get('ChipID')  # 支持字符串和数字
    
    # 自动转换为字符串
    chip_id = str(chip_id) if chip_id is not None else str(self.port)
    
    # 使用配置加载器加载真实配置
    chip_config, point_label_list = self.chip_config_loader.get_chip_config(chip_id)
    
    # 构建响应...
```

## 客户端请求示例

### 获取芯片配置

```json
{
  "MsgType": "GetChipConfig",
  "SN": 133,
  "ChipID": "72"
}
```

### 服务器响应（超导系统）

```json
{
  "MsgType": "GetChipConfigAck",
  "SN": 133,
  "backend": "72",
  "PointLabelList": [1],
  "ChipConfig": {
    "1": {
      "QuantumChipArch": {
        // ChipArchConfig_72.json 的完整内容
      }
    }
  },
  "ErrCode": 0,
  "ErrInfo": ""
}
```

## 多工作区支持

映射表支持一个芯片有多个工作区配置：

```json
{
  "mappings": {
    "72": {
      "chip_id": "72",
      "work_areas": {
        "1": {
          "config_file": "ChipArchConfig_72.json",
          "description": "默认工作区"
        },
        "2": {
          "config_file": "ChipArchConfig_72_Label_2.json",
          "description": "工作区2"
        }
      }
    }
  }
}
```

返回的配置会包含所有工作区：
```json
{
  "ChipConfig": {
    "1": {工作区1的配置},
    "2": {工作区2的配置}
  },
  "PointLabelList": [1, 2]
}
```

## 添加新芯片

### 步骤 1: 添加配置文件

将新芯片配置文件放到 `ChipConfig/` 目录：
```
ChipConfig/ChipArchConfig_<NewChipID>.json
```

### 步骤 2: 更新映射表

在 `chip_config_mapping.json` 中添加映射：

```json
{
  "mappings": {
    "<NewChipID>": {
      "chip_id": "<NewChipID>",
      "chip_name": "<芯片名称>",
      "system_type": "<系统类型>",
      "work_areas": {
        "1": {
          "config_file": "ChipArchConfig_<NewChipID>.json",
          "description": "默认工作区"
        }
      },
      "default_work_area": "1"
    }
  }
}
```

### 步骤 3: 测试

运行测试脚本验证：

```bash
cd PilotPy/python_simulator
python test_chip_config.py
```

## 错误处理

### 未知芯片ID

当请求不存在的芯片ID时，服务器返回错误：

```json
{
  "MsgType": "GetChipConfigAck",
  "SN": 133,
  "backend": "UNKNOWN_999",
  "ChipConfig": {},
  "ErrCode": 2,
  "ErrInfo": "Unknown chip ID: UNKNOWN_999"
}
```

### 配置文件缺失

如果映射表中的配置文件不存在，会记录错误日志并返回空配置。

## 测试

运行完整测试：

```bash
cd PilotPy/python_simulator
python test_chip_config.py
```

测试内容：
1. 列出所有可用芯片
2. 加载每个芯片的配置
3. 测试无效的芯片ID
4. 测试芯片信息检索

## 日志

配置加载器会输出详细的日志信息：

```
INFO - Loaded 4 chip mappings from ChipConfig/chip_config_mapping.json
INFO -   - Chip 72: 1 work areas ['1']
INFO -   - Chip HanYuan_01: 1 work areas ['1']
INFO -   - Chip IonTrap: 1 work areas ['1']
INFO -   - Chip PQPUMESH8: 1 work areas ['1']
```

## 注意事项

1. **ChipID 类型**：始终使用字符串类型
2. **配置文件路径**：相对于 `ChipConfig/` 目录
3. **工作区标签**：使用字符串作为键（如 "1", "2"）
4. **JSON 格式**：确保所有配置文件都是有效的 JSON
5. **字符编码**：配置文件使用 UTF-8 编码

## 性能考虑

- 配置在首次访问时加载并缓存
- 服务器启动时加载映射表
- 支持运行时重新加载映射表：`loader.reload_mappings()`

## 更新历史

- 2026-02-05: 初始版本，支持4个芯片配置
  - 超导72比特
  - 汉源1号（中性原子）
  - 离子阱
  - 光量子8比特
