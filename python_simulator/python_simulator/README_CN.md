# 量子模拟ZMQ服务器

Python实现的量子计算模拟服务，支持四种量子系统：超导、离子阱、中性原子和光量子，用于联合本源司南操作系统使用；如需使用本服务，可参考司南图形界面中添加芯片功能，完成对应芯片信息配置后，即可使用。

## 功能特性

- **ZMQ路由-代理模式**：处理客户端请求并发送响应
- **ZMQ发布-订阅模式**：实时推送状态更新和通知
- **多协议支持**：支持四种不同的量子系统协议
- **任务管理**：异步任务处理，支持状态跟踪
- **状态发布**：通过发布-订阅自动推送任务状态更新
- **随机结果生成**：模拟量子计算结果
- **端口范围7000-7010**：路由端口用于客户端请求
- **端口范围8000-8010**：发布端口用于状态更新

## 系统架构

```
PilotPy/python_simulator/
├── config.py                 # 配置和枚举定义
├── result_generator.py       # 随机结果生成器
├── task_manager.py          # 任务生命周期管理
├── zmq_router_server.py     # 核心ZMQ路由服务器
├── zmq_pub_server.py       # ZMQ发布服务器（状态更新）
├── main.py                 # 程序入口
├── protocol_adapters/       # 协议适配器
│   ├── superconducting.py   # 超导协议适配器
│   ├── ion_trap.py        # 离子阱协议适配器
│   ├── neutral_atom.py     # 中性原子协议适配器
│   └── photonic.py       # 光量子协议适配器
└── README_CN.md           # 本文件（中文版说明）
```

### 通信模式

服务器使用两种互补的ZMQ通信模式：

#### 1. 路由-代理模式（请求-响应）
- **端口**：7000-7003
- **用途**：处理客户端请求并发送响应
- **连接方式**：客户端作为DEALER连接，服务器作为ROUTER
- **通信特点**：双向通信

#### 2. 发布-订阅模式（发布-订阅）
- **端口**：8000-8003
- **用途**：向订阅者推送状态更新和通知
- **连接方式**：服务器作为PUBLISHER，客户端作为SUBSCRIBER
- **通信特点**：单向推送通信，实时状态更新
- **消息结构**：三层消息结构（主题 + 操作 + 数据）

## 安装指南

### 环境要求

```bash
pip install pyzmq
```

### Python版本

- Python 3.8 或更高版本

## 快速开始

### 启动单个服务器

启动特定的量子系统服务器：

```bash
# 启动超导量子服务器（默认端口7000）
python main.py --system superconducting

# 启动离子阱量子服务器（默认端口7001）
python main.py --system ion_trap

# 启动中性原子量子服务器（默认端口7002）
python main.py --system neutral_atom

# 启动光量子服务器（默认端口7003）
python main.py --system photonic
```

### 启动所有服务器

同时启动所有四个量子系统服务器：

```bash
python main.py --all
```

### 启动服务器（自动包含发布服务器）

启动一个服务器时，会自动同时启动路由服务器和发布服务器：

```bash
python main.py --system superconducting
```

输出示例：
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

### 自定义配置

```bash
# 自定义端口（仅影响路由端口）
python main.py --system superconducting --port 7005

# 自定义绑定地址
python main.py --system superconducting --bind-address 192.168.1.100

# 设置日志级别
python main.py --system superconducting --log-level DEBUG
```

### 命令行参数说明

```
--system {superconducting,ion_trap,neutral_atom,photonic}
                        要模拟的量子系统类型
--all                   启动所有量子系统服务器
--port PORT             覆盖默认端口
--log-level {DEBUG,INFO,WARNING,ERROR}
                        设置日志级别（默认：INFO）
--bind-address ADDRESS   绑定地址（默认：*）
```

## 协议详情

### 1. 超导量子系统

**路由端口**：7000  
**发布端口**：8000

**支持的消息类型（路由）**：
- `MsgTask`：提交量子计算任务
- `TaskStatus`：查询任务状态
- `MsgHeartbeat`：心跳检测
- `GetChipConfig`：获取芯片配置
- `GetUpdateTime`：获取校准时间
- `GetRBData`：获取随机基准测试数据
- `SetVip`：设置独占时间片
- `ReleaseVip`：释放独占时间片

**发布的消息类型（发布）**：
- `task_status`：任务状态更新（PENDING、RUNNING、SUCCESSED、FAILED）
- `chip_update`：芯片配置更新通知
- `probe`：芯片资源状态（量子比特使用情况、线程状态）
- `calibration_start`：校准开始通知
- `calibration_done`：校准完成通知
- `chip_protect`：芯片维护开始/结束通知

**协议特点**：
- 扁平JSON结构
- 支持任务优先级
- 支持实验模式
- VIP时间片管理
- 实时状态更新

### 2. 离子阱量子系统

**路由端口**：7001  
**发布端口**：8001

**支持的消息类型（路由）**：
- `MsgGetToken`：获取访问令牌（认证）
- `MsgUpdateToken`：刷新访问令牌
- `MsgTask`：提交量子计算任务
- `TaskStatus`：查询任务状态
- `MsgHeartbeat`：心跳检测
- `GetChipConfig`：获取芯片配置
- `GetUpdateTime`：获取校准时间
- `GetRBData`：获取随机基准测试数据

**发布的消息类型（发布）**：
- `task_status`：任务状态更新（PENDING、RUNNING、SUCCESSED、FAILED）

**协议特点**：
- Header/Body JSON结构
- 基于Token的认证机制
- 支持版本号字段
- 支持保真度矩阵

### 3. 中性原子量子系统

**路由端口**：7002  
**发布端口**：8002

**支持的消息类型（路由）**：
- `MsgGetToken`：获取访问令牌（认证）
- `MsgTask`：提交量子计算任务
- `MsgTaskStatus`：查询任务状态
- `MsgHeartbeat`：心跳检测
- `GetUpdateTime`：获取校准时间
- `MsgAtomConfig`：获取原子配置

**发布的消息类型（发布）**：
- `task_status`：任务状态更新（SUBMIT、RUNNING、FINISH、CANCEL等）

**协议特点**：
- Header/Body JSON结构
- 基于Token的认证机制
- OPENQASM任务格式
- 自定义结果格式（包含grid和waveform）

### 4. 光量子系统

**路由端口**：7003  
**发布端口**：8003

**支持的消息类型（路由）**：
- `MsgTask`：提交量子计算任务
- `TaskStatus`：查询任务状态
- `MsgHeartbeat`：心跳检测
- `GetChipConfig`：获取芯片配置

**发布的消息类型（发布）**：
- `task_status`：任务状态更新（PENDING、RUNNING、SUCCESSED、FAILED）

**协议特点**：
- 扁平JSON结构
- 支持基本量子门（X、Y、Z、H、RX、RY、RZ、CNOT、CZ等）
- QASM风格任务格式

## 任务流程

### 1. 提交任务（路由）

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

### 2. 接收确认（路由）

```json
{
    "MsgType": "MsgTaskAck",
    "SN": 1,
    "ErrCode": 0,
    "ErrInfo": ""
}
```

### 3. 任务状态更新（发布）

任务状态通过发布-订阅自动推送：

**PENDING**（接收任务后）：
```json
{
    "MsgType": "TaskStatus",
    "SN": 0,
    "TaskId": "unique-task-id",
    "TaskStatus": 1
}
```

**RUNNING**（处理中）：
```json
{
    "MsgType": "TaskStatus",
    "SN": 0,
    "TaskId": "unique-task-id",
    "TaskStatus": 2
}
```

**SUCCESSED**（完成后）：
```json
{
    "MsgType": "TaskStatus",
    "SN": 0,
    "TaskId": "unique-task-id",
    "TaskStatus": 5
}
```

### 4. 接收结果（路由）

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

## 配置说明

### 服务器配置（config.py）

```python
class ServerConfig:
    # 网络设置
    BIND_ADDRESS = "*"          # 绑定到所有网络接口
    TIMEOUT = 1000              # Socket超时时间（毫秒）
    HWM = 1000                 # 高水位标记
    
    # 路由端口分配
    ROUTER_PORTS = {
        QuantumSystemType.SUPERCONDUCTING: 7000,
        QuantumSystemType.ION_TRAP: 7001,
        QuantumSystemType.NEUTRAL_ATOM: 7002,
        QuantumSystemType.PHOTONIC: 7003
    }
    
    # 发布端口分配
    PUB_PORTS = {
        QuantumSystemType.SUPERCONDUCTING: 8000,
        QuantumSystemType.ION_TRAP: 8001,
        QuantumSystemType.NEUTRAL_ATOM: 8002,
        QuantumSystemType.PHOTONIC: 8003
    }
    
    # 性能设置
    THREAD_POOL_SIZE = 10       # 并发任务工作线程数
    MAX_QUEUE_SIZE = 200        # 最大待处理任务数
    
    # 模拟时间（毫秒）
    COMPILE_TIME = 100          # 模拟编译时间
    RUN_TIME = 2000             # 模拟运行时间
    POST_PROCESS_TIME = 50      # 模拟后处理时间
    
    # 日志设置
    LOG_LEVEL = "INFO"
    LOG_FILE = "log/simulator.log"
```

## 任务状态枚举

```python
class TaskStatus(Enum):
    UNKNOW_STATE = 0    # 未知状态
    PENDING = 1          # 任务在队列中
    COMPILING = 7         # 任务编译中
    COMPILED = 8          # 任务已编译
    RUNNING = 2           # 任务运行中
    SUCCESSED = 5         # 任务成功完成
    FAILED = 4            # 任务失败
    NOTASK = 3            # 任务不存在
    RETRY = 6             # 任务重试
    
    # 中性原子专用
    SUBMIT = 9            # 任务已提交
    FINISH = 10           # 任务已完成
    CANCEL = 11           # 任务已取消
    SUBMITFAIL = 12       # 提交失败
    RUNFAIL = 13          # 运行失败
    WAITING = 14           # 任务等待中
```

## 错误码

```python
class ErrorCode(Enum):
    NO_ERROR = 0                   # 成功
    UNDEFINED_ERROR = 1            # 未知错误
    TASK_PARAM_ERROR = 2            # 任务参数错误
    JSON_ERROR = 3                  # JSON解析错误
    QUEUE_FULL = 4                   # 队列已满
    AUTH_ERROR = 5                    # 认证错误
    TASK_ID_DUPLICATE = 10          # 任务ID重复
    TASK_ID_NOT_EXIST = 40           # 任务ID不存在
```

## 客户端示例

### 路由-代理客户端示例

```python
import zmq
import json

# 连接到路由服务器
context = zmq.Context()
socket = context.socket(zmq.DEALER)
socket.connect("tcp://localhost:7000")

# 提交任务
task = {
    "MsgType": "MsgTask",
    "SN": 1,
    "TaskId": "test-task-001",
    "ConvertQProg": "[[{'H': [0]}, {'Measure': [[0]]}]]",
    "Configure": {"Shot": 1000}
}

# 发送请求
socket.send_json(task)

# 接收确认
ack = socket.recv_json()
print(f"确认消息: {ack}")

# 接收结果（异步）
result = socket.recv_json()
print(f"任务结果: {result}")
```

### 发布-订阅客户端示例

```python
import zmq
import json

# 连接到发布服务器
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:8000")

# 订阅主题 'simulator_topic' 以接收所有消息
socket.setsockopt_string(zmq.SUBSCRIBE, b'simulator_topic')

# 接收状态更新
while True:
    # 接收主题
    topic = socket.recv()
    
    # 接收操作类型
    operation = socket.recv()
    
    # 接收数据
    data = socket.recv_json()
    
    print(f"接收消息: topic={topic}, operation={operation}")
    print(f"数据: {data}")
```

## 测试

### 启动所有服务器

```bash
python main.py --all
```

预期输出：
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

### 使用测试客户端

```bash
python test_client.py
```

测试特定服务器：
```bash
# 测试超导服务器
python test_client.py --port 7000

# 测试离子阱服务器
python test_client.py --port 7001

# 测试所有服务器
python test_client.py --all
```

## 日志

日志存储在 `log/` 目录中：

```
log/
├── ZmqRouter-superconducting.log
├── ZmqRouter-ion_trap.log
├── ZmqRouter-neutral_atom.log
└── ZmqRouter-photonic.log
```

日志级别：
- **DEBUG**：详细的调试信息
- **INFO**：一般信息消息（默认）
- **WARNING**：警告消息
- **ERROR**：仅错误消息

## 最近修复和改进

### SN字段处理
- **已修复**：所有协议适配器现在都有 `parse_general_message()` 方法
- **已修复**：SN（序列号）从所有消息类型中正确提取
- **改进**：四种量子系统的一致性SN处理
- **影响**：任务确认和结果现在包含正确的SN值

### Token管理（离子阱和中性原子）
- **已修复**：`MsgUpdateToken` 现在返回 `AccessToken` 和 `RefreshToken`
- **改进**：Token刷新流程正确更新两个令牌
- **影响**：认证流程现在完整且正确

### 消息字段访问（关键修复）
- **已修复**：`parse_general_message()` 现在将所有消息字段展开到顶层
- **已修复**：所有处理器现在可以直接访问消息字段（如 `msg_data.get('ChipID')`）
- **影响**：之前，处理器无法访问 `ChipID`、`APPId`、`APIKey`、`APISecret`、`TaskId` 等非任务消息的字段。现在所有字段都可以通过 `result.update(body)`（离子阱/中性原子）或 `result.update(data)`（超导/光量子）访问。

### 消息解析
- **改进**：所有适配器支持通用解析和任务特定解析
- **已修复**：离子阱和中性原子正确处理Header/Body结构
- **已修复**：超导和光量子正确处理扁平JSON结构
- **影响**：所有消息类型一致解析，所有字段都可访问

## 常见问题排查

### 端口已被占用

如果看到 `Address already in use` 错误：

```bash
# 查找使用端口的进程
lsof -i :7000
lsof -i :8000

# 终止进程
kill -9 <PID>
```

### 响应中缺少SN字段

**问题**：响应消息不包含SN或SN值不正确。

**解决方案**：已在所有协议适配器中修复。确保使用最新代码：

```bash
git pull  # 获取最新更改
python main.py --all  # 重启服务器
```

### Token刷新失败（离子阱和中性原子）

**问题**：`MsgUpdateToken` 返回空或无效的令牌。

**解决方案**：
1. 确保在 `Authorization` 头中发送 `RefreshToken`
2. 检查刷新令牌是否之前从 `MsgGetToken` 获得
3. 验证令牌未过期（模拟令牌不会过期，但实际系统会）

正确的请求示例：
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

### 任务状态未发布

**问题**：客户端未通过发布-订阅接收到任务状态更新。

**解决方案**：
1. 验证发布服务器正在运行（检查端口8000-8003）
2. 确保订阅者订阅了正确的主题：
   ```python
   socket.setsockopt_string(zmq.SUBSCRIBE, b'simulator_topic')
   ```
3. 检查防火墙是否允许发布服务器端口
4. 验证三层消息接收（主题、操作、数据）：
   ```python
   topic = socket.recv()  # 第一层：主题
   operation = socket.recv()  # 第二层：操作
   data = socket.recv_json()  # 第三层：数据
   ```

### ZMQ连接失败

检查是否安装了pyzmq：

```bash
pip install pyzmq
```

### 任务队列已满

如果任务被拒绝并返回错误码4，说明队列已满（最多1000个任务）。可以：
- 等待任务完成
- 在config.py中增加 `MAX_QUEUE_SIZE`

### 发布-订阅未接收消息

如果订阅者未接收消息：
- 检查发布服务器是否运行（检查端口8000-8003）
- 验证调用了 socket.setsockopt_string(zmq.SUBSCRIBE, b'simulator_topic')
- 检查防火墙设置

## 发布-订阅消息结构

发布服务器使用三层消息结构：

1. **主题**：所有消息固定为 `b'simulator_topic'`
2. **操作**：消息类型（如 `b'task_status'`、`b'chip_update'`）
3. **数据**：JSON数据载荷

这允许客户端订阅单个主题（`simulator_topic`）并接收所有消息类型，然后根据需要进行操作过滤。

## 许可证

这是一个用于开发和测试目的的模拟服务器。

## 技术支持

如有问题或疑问，请参考协议文档：
- 超导：`超导通信协议文档.md`
- 离子阱：`离子阱通信协议文档.md`
- 中性原子：`中性原子通信协议文档.md`
- 光量子：`光量子通信协议文档.md`
