# WebSocket 服务（基于新 DataModel）

基于统一的 `datamodel.py` 重写的 WebSocket 微服务，支持流式推送、异步并行处理和统一消息格式。

## 主要特性

### 1. 统一消息格式
- 基于 `ParseData` 数据模型
- 自动解析工具调用（ToolCall）
- 自动提取 TODO 列表（TodoItem）
- 自动识别文件写入操作
- 统一的 Usage 信息（Token 使用情况）

### 2. WebSocket 实时连接
- 支持多客户端并发连接
- 实时双向通信
- 心跳检测（ping/pong）
- 自动重连机制

### 3. 流式推送
- 实时推送 AI 响应
- 增量文本传输
- 降低首字节延迟
- 支持大规模输出

### 4. 异步并行处理
- 多任务并发执行
- 任务隔离和管理
- 支持任务中断
- 资源自动清理

### 5. 会话管理
- 自动保存 session_id
- 支持会话继续
- 历史消息记录

## 项目结构

```
backend_new/
├── datamodel.py          # 核心数据模型（ParseData, ToolCall, TodoItem, Usage）
├── parser.py             # 流式消息解析器（StreamParser, MessageExtractor）
├── service.py            # WebSocket 服务主程序
├── config.py             # 配置文件
├── session_manager.py    # 会话管理
├── requirements.txt      # Python 依赖
├── test_service.py       # 测试脚本
└── history/              # 消息历史记录目录
```

## 核心组件

### datamodel.py
定义统一的数据模型：
- `ParseData`: 核心数据结构
- `ToolCall`: 工具调用信息
- `TodoItem`: TODO 项
- `Usage`: Token 使用统计

### parser.py
- `StreamParser`: 异步流式解析器，将 JSON 转换为 ParseData 对象
- `MessageExtractor`: 消息内容提取工具

### service.py
- `TaskManager`: 任务管理器，支持并发和中断
- `execute_command_stream`: 流式执行命令
- WebSocket 端点处理

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
python service.py
```

默认监听 `0.0.0.0:10086`

## 配置

修改 `config.py`:

```python
PORT = 10086          # 服务端口
HOST = "0.0.0.0"      # 监听地址
LOG_LEVEL = "INFO"    # 日志级别
```

## API 接口

### WebSocket 端点: `/ws`

#### 消息类型

**1. execute - 执行命令**
```json
{
  "type": "execute",
  "prompt": "你的问题或命令",
  "session_id": "optional_session_id",
  "task_id": "optional_task_id"
}
```

**2. cancel - 取消任务**
```json
{
  "type": "cancel",
  "task_id": "task_id_to_cancel"
}
```

**3. ping - 心跳检测**
```json
{
  "type": "ping"
}
```

#### 响应消息

**1. task_start - 任务开始**
```json
{
  "type": "task_start",
  "task_id": "...",
  "timestamp": "..."
}
```

**2. chunk - 流式数据块**
```json
{
  "type": "chunk",
  "task_id": "...",
  "parse_data": {
    "type": "...",
    "message": {...},
    "model": "...",
    "usage": {...},
    "tool_calls": [...],
    "todo_list": [...],
    "write_files": [...]
  },
  "new_text": "增量文本",
  "full_content": "完整内容",
  "raw_json": "原始 JSON",
  "has_tool_calls": true/false,
  "has_todo_list": true/false,
  "has_write_files": true/false,
  "timestamp": "..."
}
```

**3. task_complete - 任务完成**
```json
{
  "type": "task_complete",
  "task_id": "...",
  "exit_code": 0,
  "timestamp": "..."
}
```

**4. error - 错误**
```json
{
  "type": "error",
  "message": "错误信息",
  "timestamp": "..."
}
```

### HTTP 端点

**GET `/health`** - 健康检查
```json
{
  "status": "healthy",
  "active_tasks": 0,
  "timestamp": "..."
}
```

**GET `/`** - 服务信息
```json
{
  "service": "WebSocket Stream Service with DataModel",
  "version": "2.0.0",
  "websocket_endpoint": "/ws",
  "datamodel": "ParseData-based unified message format"
}
```

## 测试

运行测试脚本：

```bash
python test_service.py
```

测试内容：
- WebSocket 连接
- 流式推送
- 消息解析（ParseData）
- 工具调用检测
- TODO 列表检测
- 文件写入检测
- 心跳检测

## 核心优势

### 与旧版本对比

| 特性 | 旧版本 | 新版本 |
|------|--------|--------|
| 消息格式 | 自定义字典 | 统一 ParseData 模型 |
| 解析器 | AsyncMessageParser | StreamParser（基于 datamodel） |
| 工具调用 | 手动提取 | 自动解析到 ToolCall 对象 |
| TODO 列表 | 手动提取 | 自动解析到 TodoItem 对象 |
| 文件操作 | 分散在各处 | 统一到 write_files 列表 |
| 扩展性 | 需修改多处 | 只需扩展 datamodel |
| 类型安全 | 弱类型字典 | 强类型数据类 |

### 新版本优势

1. **统一消息格式**: 所有消息使用 `ParseData` 模型，易于维护和扩展
2. **自动化解析**: 自动提取工具调用、TODO、文件操作等
3. **类型安全**: 使用 `dataclass` 提供类型提示和验证
4. **异步优化**: 使用线程池并行解析，提升性能
5. **易于集成**: 统一的数据模型便于前后端集成

## 使用示例

### Python 客户端

```python
import asyncio
import websockets
import json

async def chat():
    uri = "ws://localhost:10086/ws"

    async with websockets.connect(uri) as websocket:
        # 发送消息
        await websocket.send(json.dumps({
            "type": "execute",
            "prompt": "写一个 Python 函数计算斐波那契数列"
        }))

        # 接收响应
        while True:
            response = await websocket.recv()
            data = json.loads(response)

            if data["type"] == "chunk":
                # 获取 ParseData
                parse_data = data.get("parse_data")

                # 打印增量文本
                print(data.get("new_text", ""), end='', flush=True)

                # 检查工具调用
                if data.get("has_tool_calls"):
                    print(f"\n检测到工具调用: {parse_data['tool_calls']}")

            elif data["type"] == "task_complete":
                print("\n任务完成!")
                break

asyncio.run(chat())
```

### JavaScript 客户端

```javascript
const ws = new WebSocket('ws://localhost:10086/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'execute',
    prompt: '你好'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'chunk') {
    // 获取 ParseData
    const parseData = data.parse_data;

    // 显示增量文本
    console.log(data.new_text);

    // 检查特殊内容
    if (data.has_tool_calls) {
      console.log('工具调用:', parseData.tool_calls);
    }
  } else if (data.type === 'task_complete') {
    console.log('任务完成');
  }
};
```

## 部署

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10086

CMD ["python", "service.py"]
```

### 构建和运行

```bash
docker build -t websocket-service .
docker run -p 10086:10086 websocket-service
```

## 日志和监控

- 所有消息自动保存到 `history/` 目录
- 按 session_id 分文件存储（JSONL 格式）
- 支持实时日志输出
- 提供 `/health` 端点监控服务状态

## 故障排查

### 连接失败
- 检查端口是否被占用
- 检查防火墙设置
- 确认服务已启动

### 解析错误
- 检查 ccr 命令是否正常
- 查看服务日志
- 验证 datamodel 版本

### 性能问题
- 调整线程池大小（StreamParser max_workers）
- 优化缓存策略
- 检查系统资源

## 许可

本项目基于原有 backend 服务重构，保持相同的功能，但使用统一的 datamodel。
