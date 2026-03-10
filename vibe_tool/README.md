# vibe_tool

将 vibe coding CLI 工具（`ccr` / `opencode`）封装为 [agno](https://docs.agno.com) 兼容的 `Toolkit`，供 agno agent 直接调用。

## 目录结构

```
vibe_tool/
├── __init__.py          # 模块入口，暴露 VibeCodingToolkit
├── cli_runner.py        # 异步进程管理、高并发（Semaphore）、流式读取
├── vibe_toolkit.py      # agno Toolkit 封装
├── main.py              # 快速示例
├── requirements.txt     # 仅需 agno>=1.5.0
└── README.md
```

解析逻辑（`parser.py`、`opencode_parser.py`、`datamodel.py`）直接复用上级 `backend/` 目录，**保持不变**。

---

## 快速开始

### 1. 安装依赖

```bash
pip install agno>=1.5.0
```

> 确保 `ccr` 或 `opencode` 已在系统 PATH 中可用。

### 2. 在 agno Agent 中使用

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from vibe_tool import VibeCodingToolkit

toolkit = VibeCodingToolkit(
    agent_type="ccr",    # "ccr" 或 "opencode"
    max_concurrent=16,   # 最大并发量
)

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[toolkit],
    show_tool_calls=True,
)

agent.print_response("帮我用 React 写一个 Todo App")
```

### 3. 异步调用（带实时回调）

```python
import asyncio
from vibe_tool import VibeCodingToolkit

toolkit = VibeCodingToolkit(agent_type="ccr")

def on_chunk(chunk):
    if chunk.get("new_text"):
        print(chunk["new_text"], end="", flush=True)

async def main():
    result = await toolkit.arun_prompt(
        prompt="写一个 Python 爬虫",
        on_chunk=on_chunk,
    )
    print("\n完成！耗时:", result["elapsed"], "秒")

asyncio.run(main())
```

### 4. 任务管理

```python
# 查询状态
status_json = toolkit.get_task_status(task_id)

# 取消任务
cancel_json = toolkit.cancel_task(task_id)

# 列出活跃任务
active_json = toolkit.list_active_tasks()
```

---

## Toolkit 工具方法（agno 可见）

| 方法 | 说明 |
|------|------|
| `cancel_task(task_id)` | 取消指定任务 |
| `get_task_status(task_id)` | 查询任务状态 |
| `list_active_tasks()` | 列出所有活跃任务 |

### 异步调用接口（直接 await）

| 方法 | 说明 |
|------|------|
| `arun_prompt(prompt, ...)` | 异步提交 prompt 并等待完成 |

---

## 设计要点

- **真正异步**：使用 `asyncio.create_subprocess_exec` 启动子进程，`await readline()` 非阻塞读取 stdout
- **并发控制**：`CliRunner` 使用 `asyncio.Semaphore(max_concurrent)` 限制并发数
- **无后台挂起**：所有任务必须被 `await` 等待完成，不支持 fire-and-forget
- **进程树终止**：Windows 使用 `taskkill /F /T`，Linux 使用 `os.killpg` + `SIGTERM/SIGKILL`
