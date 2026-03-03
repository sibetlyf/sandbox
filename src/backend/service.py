#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于新 datamodel 的 WebSocket 微服务
支持流式推送、异步并行处理、心跳机制和优化的历史保存
"""

import asyncio
import json
import os
import shlex
import subprocess
import platform
import time
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Optional, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging

from parser import StreamParser, MessageExtractor
from session_manager import save_session_id, get_latest_session_id
from datamodel import ParseData
from opencode_parser import OpenCodeStreamParser, OpenCodeMessageExtractor
import config

# 配置日志
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)

# 检测操作系统
IS_WINDOWS = platform.system() == 'Windows'

# 创建history目录
HISTORY_DIR = os.path.join(os.path.dirname(__file__), 'history')
os.makedirs(HISTORY_DIR, exist_ok=True)

# 心跳配置
HEARTBEAT_INTERVAL = 60  # 心跳间隔（秒）
HEARTBEAT_TIMEOUT = 180   # 心跳超时（秒）


class HistoryManager:
    """优化的历史记录管理器"""

    @staticmethod
    def save_raw_message(session_id: str, message_type: str, message_data: dict):
        """保存原始消息为 JSON Lines 格式"""
        if not session_id:
            return

        try:
            raw_file = os.path.join(HISTORY_DIR, f"{session_id}_raw.json")

            # 直接保存原始JSON数据，每行一个JSON对象 (JSONL)
            with open(raw_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(message_data, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"保存原始消息失败: {e}")

    @staticmethod
    def save_parsed_content(session_id: str, content: str):
        """保存解析后的内容为 TXT"""
        if not session_id or not content:
            return

        try:
            # 解析后的文本文件
            parsed_file = os.path.join(HISTORY_DIR, f"{session_id}_parsed.txt")
            with open(parsed_file, 'a', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            logger.error(f"保存解析内容失败: {e}")

    @staticmethod
    def save_parsed_structured(session_id: str, parse_data: ParseData):
        """保存结构化的解析数据为 JSON"""
        if not session_id:
            return

        try:
            # 结构化JSON文件（JSONL格式）
            structured_file = os.path.join(HISTORY_DIR, f"{session_id}_structured.json")
            with open(structured_file, 'a', encoding='utf-8') as f:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "parse_data": parse_data.to_dict()
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"保存结构化数据失败: {e}")



# 锁文件清理函数
def clean_claude_lock_file():
    try:
        home_dir = os.path.expanduser("~")
        lock_file = os.path.join(home_dir, ".claude", "history.jsonl.lock")
        if os.path.exists(lock_file):
            os.remove(lock_file)
            logger.info(f"====== 启动时自动清理锁文件: {lock_file} ======")
        else:
            logger.info("====== 启动检查: 无残留锁文件 ======")
    except Exception as e:
        logger.error(f"清理锁文件失败: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    clean_claude_lock_file()
    
    # 启动 Browser Service
    browser_process = None
    try:
        browser_script = os.path.join(os.path.dirname(__file__), 'browser_service.py')
        if os.path.exists(browser_script):
            env = dict(os.environ, PYTHONUNBUFFERED='1')
            logger.info(f"启动 Browser Service: {browser_script}")
            if IS_WINDOWS:
                browser_process = subprocess.Popen(['python', browser_script], env=env)
            else:
                browser_process = subprocess.Popen(['python3', browser_script], env=env)
    except Exception as e:
        logger.error(f"启动 Browser Service 失败: {e}")
        
    yield
    
    # 关闭时执行 (如有需要)
    if browser_process:
        try:
            browser_process.terminate()
            browser_process.wait(timeout=5)
        except:
            if browser_process.poll() is None:
                browser_process.kill()

app = FastAPI(title="WebSocket Stream Service with DataModel", lifespan=lifespan)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HeartbeatManager:
    """心跳管理器，为每个连接维护独立的心跳"""

    def __init__(self):
        self.connections: Dict[str, Dict] = {}  # conn_id -> {websocket, last_pong, task}
        self.lock = asyncio.Lock()

    async def register_connection(self, conn_id: str, websocket: WebSocket):
        """注册连接并启动心跳"""
        async with self.lock:
            if conn_id in self.connections:
                # 取消旧的心跳任务
                old_task = self.connections[conn_id].get('task')
                if old_task:
                    old_task.cancel()

            self.connections[conn_id] = {
                'websocket': websocket,
                'last_pong': time.time(),
                'task': None
            }

        # 启动心跳任务
        task = asyncio.create_task(self._heartbeat_loop(conn_id))
        async with self.lock:
            if conn_id in self.connections:
                self.connections[conn_id]['task'] = task

    async def unregister_connection(self, conn_id: str):
        """取消注册连接"""
        async with self.lock:
            if conn_id in self.connections:
                task = self.connections[conn_id].get('task')
                if task:
                    task.cancel()
                del self.connections[conn_id]

    async def update_pong(self, conn_id: str):
        """更新pong时间"""
        async with self.lock:
            if conn_id in self.connections:
                self.connections[conn_id]['last_pong'] = time.time()

    async def _heartbeat_loop(self, conn_id: str):
        """心跳循环"""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)

                async with self.lock:
                    if conn_id not in self.connections:
                        break

                    conn_info = self.connections[conn_id]
                    websocket = conn_info['websocket']
                    last_pong = conn_info['last_pong']

                # 检查超时
                if time.time() - last_pong > HEARTBEAT_TIMEOUT:
                    logger.warning(f"连接 {conn_id} 心跳超时，关闭连接")
                    try:
                        await websocket.close(code=1000, reason="Heartbeat timeout")
                    except Exception:
                        pass
                    break

                # 发送ping
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.now().isoformat()
                    })
                    logger.debug(f"发送心跳到连接 {conn_id}")
                except Exception as e:
                    logger.error(f"发送心跳失败 {conn_id}: {e}")
                    break

        except asyncio.CancelledError:
            logger.debug(f"心跳任务已取消 {conn_id}")
        except Exception as e:
            logger.error(f"心跳循环错误 {conn_id}: {e}")


class TaskManager:
    """任务管理器，支持高并发和中断"""

    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
        self.websockets: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def register_task(self, task_id: str, process: subprocess.Popen, websocket: WebSocket):
        """注册任务"""
        async with self.lock:
            self.tasks[task_id] = {
                'process': process,
                'started_at': time.time(),
                'status': 'running'
            }
            if task_id not in self.websockets:
                self.websockets[task_id] = set()
            self.websockets[task_id].add(websocket)
        await asyncio.sleep(0.001)

    async def unregister_task(self, task_id: str, websocket: WebSocket):
        """取消注册任务"""
        async with self.lock:
            if task_id in self.websockets:
                self.websockets[task_id].discard(websocket)
                if not self.websockets[task_id]:
                    del self.websockets[task_id]
            if task_id in self.tasks:
                del self.tasks[task_id]
        await asyncio.sleep(0.001)

    async def cancel_task(self, task_id: str) -> bool:
        """中断任务，确保杀掉整个进程树"""
        async with self.lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            process = task.get('process')

            if process and process.poll() is None:
                try:
                    logger.info(f"正在终止任务 {task_id} (PID: {process.pid})")
                    parent_pid = process.pid
                    
                    if IS_WINDOWS:
                        # Windows下需要终止进程树
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(parent_pid)], 
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        # Linux/Mac: 使用 ps 获取所有子进程并递归杀死
                        try:
                            # 1. 查找所有子进程（包括孙子进程）
                            # pgrep -P <pid> 只能查直接子进程，需要递归或者是用 pstree
                            # 更简单的方法是杀掉进程组，但在 Popen 中如果没有 setsid 可能无效
                            # 这里采用查找所有子孙进程的方式
                            
                            def get_children(pid):
                                try:
                                    cmd = f"pgrep -P {pid}"
                                    output = subprocess.check_output(cmd, shell=True).decode().strip()
                                    if output:
                                        return [int(x) for x in output.split()]
                                except:
                                    return []
                                return []

                            # 递归获取所有后代 PID
                            all_pids = [parent_pid]
                            queue = [parent_pid]
                            while queue:
                                current_pid = queue.pop(0)
                                children = get_children(current_pid)
                                for child in children:
                                    if child not in all_pids:
                                        all_pids.append(child)
                                        queue.append(child)
                            
                            # 反向杀死（先杀孙子，再杀儿子，最后杀老子）
                            for pid in reversed(all_pids):
                                try:
                                    logger.info(f"Kill PID: {pid}")
                                    os.kill(pid, 9) # SIGKILL
                                except ProcessLookupError:
                                    pass
                                except Exception as e:
                                    logger.error(f"Failed to kill {pid}: {e}")

                        except Exception as e:
                            logger.error(f"递归终止进程失败: {e}")
                            # 降级方案：只杀父进程
                            process.terminate()
                            await asyncio.sleep(0.1)
                            if process.poll() is None:
                                process.kill()

                    task['status'] = 'cancelled'
                    return True
                except Exception as e:
                    logger.error(f"中断任务失败: {e}")
                    return False
            return False

    async def has_active_connections(self, task_id: str) -> bool:
        """检查任务是否有活跃连接"""
        async with self.lock:
            if task_id not in self.websockets:
                return False
            return len(self.websockets[task_id]) > 0
    
    async def broadcast(self, task_id: str, message: dict):
        """向所有连接的WebSocket广播消息"""
        if task_id not in self.websockets:
            return

        disconnected = set()
        for ws in self.websockets[task_id]:
            try:
                await ws.send_json(message)
                await asyncio.sleep(0.001)
            except WebSocketDisconnect:
                # 确认是真正的断开连接
                logger.info(f"WebSocket 已断开，将从任务 {task_id} 中移除")
                disconnected.add(ws)
            except Exception as e:
                # 其他异常可能是临时网络问题，记录但不移除连接
                logger.debug(f"发送消息时出现临时错误（不移除连接）: {e}")

        # 清理断开的连接
        if disconnected:
            async with self.lock:
                if task_id in self.websockets:
                    self.websockets[task_id] -= disconnected
                    logger.info(f"任务 {task_id} 移除了 {len(disconnected)} 个断开的连接，剩余 {len(self.websockets[task_id])} 个")
                    # 如果没有连接了，删除key
                    if not self.websockets[task_id]:
                        logger.warning(f"任务 {task_id} 所有连接已断开")
                        del self.websockets[task_id]
        await asyncio.sleep(0.001)


# 全局管理器
task_manager = TaskManager()
heartbeat_manager = HeartbeatManager()


def get_or_create_workspace() -> str:
    """获取或创建workspace目录"""
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    workspace_path = os.path.join(project_root, 'workspace')
    os.makedirs(workspace_path, exist_ok=True)
    return workspace_path



async def execute_edgeone_deploy(project_name: str, token: str, task_id: str, websocket: WebSocket, environment: str='preview'):
    """直接执行 EdgeOne 部署命令并包装输出为工具调用格式"""
    workspace_path = get_or_create_workspace()
    
    # 搜索正确的项目目录
    target_dir = workspace_path
    relative_path = ""
    
    # 1. 尝试直接匹配项目名称的目录
    exact_match_path = os.path.join(workspace_path, project_name)
    if os.path.isdir(exact_match_path):
        target_dir = exact_match_path
        relative_path = project_name
    else:
        # 2. 搜索子目录
        found = False
        try:
            for item in os.listdir(workspace_path):
                sub_dir = os.path.join(workspace_path, item)
                if os.path.isdir(sub_dir) and not item.startswith('.'):
                    # 检查是否包含项目标识文件
                    if any(os.path.exists(os.path.join(sub_dir, f)) for f in ['package.json', 'index.html', 'next.config.js', 'vite.config.js']):
                        # 如果项目名包含在目录名中，或者目录名包含在项目名中，可能是目标
                        if project_name.lower() in item.lower() or item.lower() in project_name.lower():
                            target_dir = sub_dir
                            relative_path = item
                            found = True
                            break
        except Exception as e:
            logger.error(f"搜索目录出错: {e}")
            
    logger.info(f"部署目标目录: {target_dir} ")
    
    # 构建显示用的命令
    display_cmd = f"cd {target_dir} && edgeone pages deploy -n {project_name} -e {environment} -t {token}" if relative_path else f"cd workspace && edgeone pages deploy -n {project_name} -e {environment} -t {token}"
            
    # 发送任务开始消息
    await task_manager.broadcast(task_id, {
        "type": "task_start",
        "task_id": task_id,
        "timestamp": datetime.now().isoformat()
    })
    
    # 发送工具调用开始消息
    tool_call_id = f"toolu_{task_id}"
    await task_manager.broadcast(task_id, {
        "type": "chunk",
        "task_id": task_id,
        "parse_data": {
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{
                    "type": "tool_use",
                    "id": tool_call_id,
                    "name": "edgeone",
                    "input": {
                        "command": display_cmd
                    }
                }]
            }
        },
        "timestamp": datetime.now().isoformat()
    })
    
    env = dict(os.environ, PYTHONUNBUFFERED='1', PYTHONIOENCODING='utf-8')
    
    logger.info(f"部署命令: {display_cmd}")
    logger.info(f"工作目录: {target_dir}")
    
    if IS_WINDOWS:
        shell_command = ['cmd.exe', '/c', f'chcp 65001 >nul & {display_cmd}']
    else:
        shell_command = ['/bin/bash', '-c', display_cmd]
    
    # 执行命令
    logger.info(f"Shell command: {shell_command}")
    process = subprocess.Popen(
        shell_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        bufsize=0,
        universal_newlines=False,
        env=env,
        shell=False,
        cwd=target_dir
    )
    
    # 注册任务
    await task_manager.register_task(task_id, process, websocket)
    
    try:
        output_lines = []
        full_log = ""
        buffer = ""
        
        logger.info(f"开始执行部署命令: {display_cmd}")
        
        # 读取输出
        while True:
            await asyncio.sleep(0.1)
            
            chunk = process.stdout.read(2048)  # 减小块大小以更快响应
            if not chunk:
                if process.poll() is not None:
                    break
                continue
            
            # 解码
            try:
                if IS_WINDOWS:
                    try:
                        output = chunk.decode('utf-8', errors='strict')
                    except UnicodeDecodeError:
                        output = chunk.decode('gbk', errors='replace')
                else:
                    output = chunk.decode('utf-8', errors='replace')
            except Exception:
                output = chunk.decode('utf-8', errors='ignore')
            
            buffer += output
            
            # 按行处理输出
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                output_lines.append(line + '\n')
                full_log += line + '\n'
                
                # 实时发送每一行
                logger.info(f"部署输出: {line}")
                await task_manager.broadcast(task_id, {
                    "type": "chunk",
                    "task_id": task_id,
                    "text_content": full_log,
                    "new_text": line + '\n',
                    "timestamp": datetime.now().isoformat()
                })
            
            # 如果有剩余的不完整行，也发送（用于实时显示）
            if buffer and not buffer.endswith('\n'):
                logger.debug(f"部署输出（部分）: {buffer}")
                await task_manager.broadcast(task_id, {
                    "type": "chunk",
                    "task_id": task_id,
                    "text_content": full_log + buffer,
                    "new_text": buffer,
                    "timestamp": datetime.now().isoformat()
                })
        
        # 发送剩余的 buffer
        if buffer:
            output_lines.append(buffer)
            full_log += buffer
            await task_manager.broadcast(task_id, {
                "type": "chunk",
                "task_id": task_id,
                "text_content": full_log,
                "new_text": buffer,
                "timestamp": datetime.now().isoformat()
            })
        
        # 发送工具调用结果
        full_output = "".join(output_lines)
        await task_manager.broadcast(task_id, {
            "type": "chunk",
            "task_id": task_id,
            "parse_data": {
                "type": "tool_use_result",
                "tool_use_result": {
                    "tool_use_id": tool_call_id,
                    "content": full_output,
                    "is_error": process.returncode != 0
                }
            },
            "timestamp": datetime.now().isoformat()
        })
        
        # 发送任务完成消息
        await task_manager.broadcast(task_id, {
            "type": "task_complete",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "exit_code": process.returncode
        })
        
    except Exception as e:
        logger.error(f"部署执行出错: {e}")
        await task_manager.broadcast(task_id, {
            "type": "error",
            "task_id": task_id,
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        })
    finally:
        # 清理进程
        try:
            if process.poll() is None:
                process.terminate()
                await asyncio.sleep(0.1)
                if process.poll() is None:
                    process.kill()
        except Exception:
            pass
        
        # 取消注册任务
        await task_manager.unregister_task(task_id, websocket)


async def execute_local_deploy(project_path: str, task_id: str, websocket: WebSocket):
    """执行本地部署命令 (npm install && npm run dev) 并流式返回结果"""
    workspace_path = get_or_create_workspace()
    
    # 确定目标目录
    target_dir = os.path.join(workspace_path, project_path) if project_path else workspace_path
    
    if not os.path.exists(target_dir):
        await task_manager.broadcast(task_id, {
            "type": "error",
            "task_id": task_id,
            "message": f"项目目录不存在: {target_dir}",
            "timestamp": datetime.now().isoformat()
        })
        return

    # 构建命令
    # 使用 concurrently 或者顺序执行，这里为了简单使用 && (Windows 使用 &)
    if IS_WINDOWS:
        cmd = "npm install & npm run dev"
        shell_cmd = ['cmd.exe', '/c', f'chcp 65001 >nul & {cmd}']
    else:
        cmd = "npm install && npm run dev"
        shell_cmd = ['/bin/bash', '-c', cmd]
            
    # 发送任务开始消息
    await task_manager.broadcast(task_id, {
        "type": "task_start",
        "task_id": task_id,
        "timestamp": datetime.now().isoformat()
    })
    
    # 发送工具调用开始消息 (为了前端显示)
    tool_call_id = f"deploy_{task_id}"
    await task_manager.broadcast(task_id, {
        "type": "chunk",
        "task_id": task_id,
        "parse_data": {
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{
                    "type": "tool_use",
                    "id": tool_call_id,
                    "name": "local_deploy",
                    "input": {
                        "command": cmd,
                        "directory": target_dir
                    }
                }]
            }
        },
        "timestamp": datetime.now().isoformat()
    })
    
    env = dict(os.environ, PYTHONUNBUFFERED='1', PYTHONIOENCODING='utf-8')
    
    logger.info(f"执行本地部署: {cmd} at {target_dir}")
    
    # 执行命令
    process = subprocess.Popen(
        shell_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        bufsize=0,
        universal_newlines=False,
        env=env,
        shell=False,
        cwd=target_dir
    )
    
    # 注册任务
    await task_manager.register_task(task_id, process, websocket)
    
    try:
        full_log = ""
        buffer = ""
        deployed_url = None
        
        # 读取输出
        while True:
            # 检查任务是否被中断
            async with task_manager.lock:
                if task_manager.tasks.get(task_id, {}).get('status') == 'cancelled':
                    logger.info(f"Task {task_id} cancelled during execution")
                    # 发送取消消息
                    await task_manager.broadcast(task_id, {
                        "type": "task_cancelled",
                        "task_id": task_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    break

            await asyncio.sleep(0.1)
            
            chunk = process.stdout.read(2048)
            if not chunk:
                if process.poll() is not None:
                    break
                continue
            
            # 解码
            try:
                if IS_WINDOWS:
                    try:
                        output = chunk.decode('utf-8', errors='strict')
                    except UnicodeDecodeError:
                        output = chunk.decode('gbk', errors='replace')
                else:
                    output = chunk.decode('utf-8', errors='replace')
            except Exception:
                output = chunk.decode('utf-8', errors='ignore')
            
            buffer += output
            
            # 按行处理输出
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                clean_line = line.strip()
                full_log += line + '\n'
                
                # 去除ANSI转义字符以便匹配
                import re
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                text_only = ansi_escape.sub('', clean_line)
                
                # 尝试从日志中提取 URL
                if "http://localhost:" in text_only or "http://127.0.0.1:" in text_only:
                    match = re.search(r'(http://(?:localhost|127\.0\.0\.1):\d+)', text_only)
                    if match:
                        found_url = match.group(1)
                        if not deployed_url:
                            deployed_url = found_url
                            logger.info(f"检测到部署 URL: {deployed_url}")
                            # 发送部署成功事件
                            await task_manager.broadcast(task_id, {
                                "type": "deploy_success",
                                "task_id": task_id,
                                "url": deployed_url,
                                "timestamp": datetime.now().isoformat()
                            })

                # 实时发送每一行
                await task_manager.broadcast(task_id, {
                    "type": "chunk",
                    "task_id": task_id,
                    "text_content": full_log,
                    "new_text": line + '\n',
                    "timestamp": datetime.now().isoformat()
                })
            
            # 发送剩余 buffer
            if buffer and not buffer.endswith('\n'):
                await task_manager.broadcast(task_id, {
                    "type": "chunk",
                    "task_id": task_id,
                    "text_content": full_log + buffer,
                    "new_text": buffer,
                    "timestamp": datetime.now().isoformat()
                })
        
        # 任务结束
        await task_manager.broadcast(task_id, {
            "type": "task_complete",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "exit_code": process.returncode
        })
        
    except Exception as e:
        logger.error(f"本地部署出错: {e}")
        await task_manager.broadcast(task_id, {
            "type": "error",
            "task_id": task_id,
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        })
    finally:
        # 注意：这里不自动取消注册任务，因为 WebDev server 需要一直运行
        if process.poll() is not None:
             await task_manager.unregister_task(task_id, websocket)


async def execute_command_stream(code: str, session_id: Optional[str], task_id: str, websocket: WebSocket, use_resume: bool = False, agent_type: str = "ccr"):
    """执行命令并流式返回结果（基于 datamodel）"""
    workspace_path = get_or_create_workspace()

    # 根据 agent_type 选择解析器
    if agent_type == "opencode":
        parser = OpenCodeStreamParser(max_workers=4)
        extractor = OpenCodeMessageExtractor()
        logger.info("使用 OpenCode 解析器")
    else:
        parser = StreamParser(max_workers=4)
        extractor = MessageExtractor()
        logger.info("使用 CCR 解析器")
    
    history_manager = HistoryManager()

    # 检测并处理部署请求
    import json
    
    if code.strip().startswith('{'):
        # 解析 JSON 格式的部署请求
        deploy_data = json.loads(code.strip())
        if deploy_data.get('action') == 'deploy_edgeone':
            # 直接执行部署命令，不通过 CCR
            project_name = deploy_data.get('project_name')
            token = deploy_data.get('token')
            environment = deploy_data.get('environment', 'preview')
            
            logger.info(f"直接执行部署: project={project_name}, env={environment}")
            
            # 异步执行部署命令
            asyncio.create_task(execute_edgeone_deploy(
                project_name, token, task_id, websocket, environment
            ))
            return  # 直接返回，不继续执行 CCR
        elif deploy_data.get('action') == 'deploy_local':
            # 执行本地部署命令 (npm install && npm run dev)
            project_path = deploy_data.get('project_path', '')
            
            logger.info(f"执行本地部署: project_path={project_path}")
            
            # 异步执行部署命令
            asyncio.create_task(execute_local_deploy(
                project_path, task_id, websocket
            ))
            return  # 直接返回，不继续执行 CCR
        else:
            escaped_code = shlex.quote(code)
    else:
        # 普通命令：直接传递给 CCR 或 OpenCode
        escaped_code = shlex.quote(code)

    # 根据 agent_type 选择命令
    if agent_type == "opencode":
        # 使用 OpenCode
        if session_id and use_resume:
            cmd = f'opencode run {escaped_code} --format json --session {session_id}'
        else:
            cmd = f'opencode run {escaped_code} --format json'
        logger.info(f"使用 OpenCode: {cmd}")
    else:
        # 默认使用 CCR
        if session_id and use_resume:
            cmd = f'ccr code -p -r {session_id} --output-format stream-json --verbose --dangerously-skip-permissions {escaped_code}'
        else:
            cmd = f'ccr code -p --output-format stream-json --verbose --dangerously-skip-permissions {escaped_code}'
        logger.info(f"使用 CCR: {cmd}")

    # 构建执行命令
    env = dict(os.environ, PYTHONUNBUFFERED='1')

    if IS_WINDOWS:
        work_command = f'chcp 65001 >nul & set PYTHONUNBUFFERED=1 & {cmd}'
        shell_command = ['cmd.exe', '/c', work_command]
    else:
        work_command = f'cd {shlex.quote(workspace_path)} && export PYTHONUNBUFFERED=1 && {cmd}'
        shell_command = ['/bin/bash', '-c', work_command]

    # 启动进程
    process = subprocess.Popen(
        shell_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
        universal_newlines=False,
        env=env,
        shell=False,
        cwd=workspace_path if IS_WINDOWS else None
    )

    # 注册任务
    await task_manager.register_task(task_id, process, websocket)

    try:
        # 发送任务开始消息
        await task_manager.broadcast(task_id, {
            "type": "task_start",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        })
        await asyncio.sleep(0.001)

        buffer = ""
        session_id_found = session_id
        last_content_by_type = {}  # 按类型跟踪内容
        
        # 连接检查相关变量
        loop_counter = 0
        no_connection_count = 0
        CONNECTION_CHECK_INTERVAL = 100  # 每100次循环检查一次
        MAX_NO_CONNECTION_COUNT = 3  # 连续3次无连接才终止

        # 流式读取输出
        while True:
            await asyncio.sleep(0.001)  # 防止阻塞
            loop_counter += 1
            
            # 降低连接检查频率，增加容错机制
            if loop_counter % CONNECTION_CHECK_INTERVAL == 0:
                if not await task_manager.has_active_connections(task_id):
                    no_connection_count += 1
                    logger.warning(f"任务 {task_id} 检测到无活跃连接 ({no_connection_count}/{MAX_NO_CONNECTION_COUNT})")
                    if no_connection_count >= MAX_NO_CONNECTION_COUNT:
                        logger.info(f"任务 {task_id} 连续 {MAX_NO_CONNECTION_COUNT} 次无活跃连接，正在终止...")
                        break
                else:
                    # 重置计数器
                    if no_connection_count > 0:
                        logger.info(f"任务 {task_id} 恢复活跃连接，重置计数器")
                    no_connection_count = 0

            # 检查任务是否被中断
            async with task_manager.lock:
                if task_id in task_manager.tasks:
                    task_status = task_manager.tasks[task_id].get('status')
                    if task_status == 'cancelled':
                        await task_manager.broadcast(task_id, {
                            "type": "task_cancelled",
                            "task_id": task_id,
                            "timestamp": datetime.now().isoformat()
                        })
                        break

            chunk = process.stdout.read(4096)
            if not chunk:
                if process.poll() is not None:
                    break
                continue

            # 解码chunk
            try:
                if IS_WINDOWS:
                    try:
                        output = chunk.decode('utf-8', errors='strict')
                    except UnicodeDecodeError:
                        output = chunk.decode('gbk', errors='replace')
                else:
                    output = chunk.decode('utf-8', errors='replace')
            except Exception:
                output = chunk.decode('utf-8', errors='ignore')

            buffer += output

            # 处理完整行
            while '\n' in buffer:
                await asyncio.sleep(0) # 关键：让出控制权
                line, buffer = buffer.split('\n', 1)
                line = line.strip()

                if not line:
                    continue

                # 保存原始JSON行
                raw_json = line if line.startswith('{') else None

                # 使用 StreamParser 异步解析
                parse_data = None
                if line.startswith('{'):
                    try:
                        async for parse_data in parser.parse_line_async(line):
                            break  # 只取第一个值
                    except Exception as e:
                        logger.debug(f"解析失败: {e}")
                        parse_data = None

                # 构建消息
                if parse_data:
                    # 提取内容
                    text_content = await extractor.extract_text_content(parse_data)
                    thinking_content = await extractor.extract_thinking_content(parse_data)

                    # 检查是否有内容更新
                    has_update = False
                    new_text = ""
                    msg_id = parse_data.uuid or "default"
                    
                    # 检查文本更新
                    last_text = last_content_by_type.get(f"{msg_id}_text", "")
                    if len(text_content) > len(last_text):
                        new_text = text_content[len(last_text):]
                        last_content_by_type[f"{msg_id}_text"] = text_content
                        has_update = True
                    
                    # 检查思考更新
                    last_thinking = last_content_by_type.get(f"{msg_id}_thinking", "")
                    if len(thinking_content) > len(last_thinking):
                        if not new_text: # 如果没有文本更新，new_text设为思考的增量（兼容旧前端）
                             new_text = thinking_content[len(last_thinking):]
                        last_content_by_type[f"{msg_id}_thinking"] = thinking_content
                        has_update = True

                    # 如果有更新或者是工具调用等重要改变，则广播
                    if has_update or await extractor.has_tool_calls(parse_data) or await extractor.has_todo_list(parse_data):
                        # 构建广播消息
                        message = {
                            "type": "chunk",
                            "task_id": task_id,
                            "parse_data": parse_data.to_dict(),
                            "new_text": new_text,
                            "text_content": text_content, # 添加完整处理后的文本
                            "thinking_content": thinking_content, # 添加完整思考内容
                            "full_content": text_content, # 保持兼容, 优先使用 processed text
                            "raw_json": raw_json,
                            "has_tool_calls": await extractor.has_tool_calls(parse_data),
                            "has_todo_list": await extractor.has_todo_list(parse_data),
                            "has_write_files": await extractor.has_write_files(parse_data),
                            "timestamp": datetime.now().isoformat()
                        }

                        # 打印原始JSON
                        if raw_json:
                            print(raw_json, flush=True)

                        await task_manager.broadcast(task_id, message)

                        # 记录历史
                        log_session_id = session_id or session_id_found
                        if log_session_id:
                            history_manager.save_raw_message(log_session_id, "sent", message)
                            if new_text:
                                history_manager.save_parsed_content(log_session_id, new_text)
                            history_manager.save_parsed_structured(log_session_id, parse_data)

                    # 提取session_id
                    if not session_id_found and parse_data.session_id:
                        session_id_found = parse_data.session_id
                        save_session_id(session_id_found)

                else:
                    # 解析失败，发送原始文本
                    message = {
                        "type": "chunk",
                        "task_id": task_id,
                        "parse_data": None,
                        "new_text": line,
                        "full_content": line,
                        "raw_json": line,
                        "timestamp": datetime.now().isoformat()
                    }

                    # 打印原始JSON
                    print(line, flush=True)

                    await task_manager.broadcast(task_id, message)
                    await asyncio.sleep(0.001)

        # 发送任务完成消息
        await task_manager.broadcast(task_id, {
            "type": "task_complete",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "exit_code": process.returncode
        })
        await asyncio.sleep(0.001)

    except Exception as e:
        logger.error(f"执行命令时出错: {e}")
        await task_manager.broadcast(task_id, {
            "type": "error",
            "task_id": task_id,
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        })
        await asyncio.sleep(0.001)
    finally:
        # 清理进程
        try:
            if process.poll() is None:
                process.terminate()
                await asyncio.sleep(0.001)
                if process.poll() is None:
                    process.kill()
        except Exception:
            pass

        # 清理解析器
        parser.shutdown()

        # 取消注册任务
        await task_manager.unregister_task(task_id, websocket)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，处理所有消息"""
    await websocket.accept()

    # 生成连接ID
    conn_id = f"conn_{int(time.time() * 1000)}_{id(websocket)}"

    # 注册心跳
    await heartbeat_manager.register_connection(conn_id, websocket)
    logger.info(f"连接已建立: {conn_id}")

    history_manager = HistoryManager()

    try:
        while True:
            await asyncio.sleep(0.001)

            # 接收消息
            data = await websocket.receive_json()
            message_type = data.get("type")

            # 记录接收到的消息
            session_id = data.get("session_id")
            if session_id:
                history_manager.save_raw_message(session_id, "received", data)

            if message_type == "execute":
                # 执行命令
                code = data.get("prompt") or data.get("code", "")
                session_id = data.get("session_id")
                use_resume = data.get("use_resume", False)  # 默认不使用 resume
                task_id = data.get("task_id") or f"task_{int(time.time())}"
                agent_type = data.get("agent_type", "ccr")  # 获取 agent 类型，默认 ccr

                if not code:
                    await websocket.send_json({
                        "type": "error",
                        "message": "prompt不能为空"
                    })
                    await asyncio.sleep(0.001)
                    continue

                # 异步执行命令（不阻塞）
                asyncio.create_task(execute_command_stream(code, session_id, task_id, websocket, use_resume, agent_type))
                await asyncio.sleep(0.001)

            elif message_type == "cancel":
                # 取消任务
                task_id = data.get("task_id")
                if task_id:
                    success = await task_manager.cancel_task(task_id)
                    await websocket.send_json({
                        "type": "cancel_result",
                        "task_id": task_id,
                        "success": success
                    })
                    await asyncio.sleep(0.001)
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "task_id不能为空"
                    })
                    await asyncio.sleep(0.001)

            elif message_type == "ping":
                # 心跳检测 - 客户端发送的ping
                await heartbeat_manager.update_pong(conn_id)
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
                await asyncio.sleep(0.001)

            elif message_type == "pong":
                # 更新心跳时间 - 响应服务器发送的ping
                await heartbeat_manager.update_pong(conn_id)

            elif message_type == "tool_result":
                # 记录工具调用结果
                logger.info(f"收到工具调用结果: tool_use_id={data.get('tool_use_id')}")
                # 可以在这里添加工具结果的处理逻辑
                await websocket.send_json({
                    "type": "tool_result_ack",
                    "tool_use_id": data.get('tool_use_id'),
                    "message": "工具调用结果已记录"
                })
                await asyncio.sleep(0.001)

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"未知的消息类型: {message_type}"
                })
                await asyncio.sleep(0.001)

    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: {conn_id}")
    except Exception as e:
        logger.error(f"WebSocket错误 {conn_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
            await asyncio.sleep(0.001)
        except Exception:
            pass
    finally:
        # 取消心跳
        await heartbeat_manager.unregister_connection(conn_id)
        logger.info(f"连接已清理: {conn_id}")

# CORS 预检请求处理
from fastapi import Response
from fastapi.responses import JSONResponse

@app.options("/api/sessions")
@app.options("/api/sessions/{session_id}/history")
async def options_handler():
    """处理 CORS 预检请求"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600",
        }
    )

@app.get("/api/sessions")
async def get_sessions():
    """获取所有历史会话列表 - 扫描history目录"""
    try:
        sessions = []
        if not os.path.exists(HISTORY_DIR):
             return JSONResponse(
                 content={"sessions": []},
                 headers={
                     "Access-Control-Allow-Origin": "*",
                     "Access-Control-Allow-Methods": "GET, OPTIONS",
                     "Access-Control-Allow-Headers": "*",
                 }
             )

        # 扫描目录下所有 _structured.json 文件
        files = [f for f in os.listdir(HISTORY_DIR) if f.endswith('_structured.json')]
        
        # 按修改时间倒序
        files.sort(key=lambda x: os.path.getmtime(os.path.join(HISTORY_DIR, x)), reverse=True)

        for filename in files:
            try:
                session_id = filename.replace('_structured.json', '')
                file_path = os.path.join(HISTORY_DIR, filename)
                
                # 读取第一行获取元数据
                session_info = {
                    "session_id": session_id,
                    "preview": "No content",
                    "timestamp": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                    "message_count": 0
                }

                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    if first_line:
                        try:
                            data = json.loads(first_line)
                            session_info["timestamp"] = data.get("timestamp", session_info["timestamp"])
                            
                            # 尝试提取预览
                            msg = data.get("parse_data", {}).get("message", {})
                            content = msg.get("content", [])
                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        text = item.get("text", "")
                                        session_info["preview"] = text[:50] + "..." if len(text) > 50 else text
                                        break
                        except:
                            pass
                    
                    # 统计行数
                    f.seek(0)
                    session_info["message_count"] = sum(1 for _ in f)

                sessions.append(session_info)
            except Exception as e:
                logger.error(f"Error parsing session file {filename}: {e}")
                continue

        return JSONResponse(
            content={"sessions": sessions},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        return JSONResponse(
            content={"sessions": [], "error": str(e)},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )


@app.get("/api/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """获取指定会话的历史记录"""
    try:
        structured_file = os.path.join(HISTORY_DIR, f"{session_id}_structured.json")
        if not os.path.exists(structured_file):
            return JSONResponse(
                content={"session_id": session_id, "messages": [], "error": "Session not found"},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                }
            )

        messages = []
        with open(structured_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    parse_data = entry.get("parse_data", {})
                    msg = parse_data.get("message", {})
                    content = msg.get("content", [])

                    # 提取文本内容
                    text_content = ""
                    thinking_content = ""
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict):
                                if item.get("type") == "text":
                                    text_content = item.get("text", "")
                                elif item.get("type") == "thinking":
                                    thinking_content = item.get("thinking", "")

                    messages.append({
                        "id": entry.get("timestamp", str(len(messages))),
                        "role": msg.get("role", "assistant"),
                        "content": text_content,
                        "thinkingContent": thinking_content,
                        "toolCalls": parse_data.get("tool_calls", []),
                        "todo_list": parse_data.get("todo_list", []), # Keep for state restoration
                        "message": msg,
                        "timestamp": entry.get("timestamp")
                    })
                except Exception as e:
                    logger.debug(f"解析历史行失败: {e}")

        return JSONResponse(
            content={
                "session_id": session_id,
                "messages": messages
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )
    except Exception as e:
        logger.error(f"获取会话历史失败 {session_id}: {e}")
        return JSONResponse(
            content={"session_id": session_id, "messages": [], "error": str(e)},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )


@app.get("/api/workspace/files")
async def list_workspace_files(path: str = ""):
    """获取workspace目录的文件树结构"""
    try:
        workspace_path = get_or_create_workspace()
        target_path = os.path.join(workspace_path, path) if path else workspace_path
        
        if not os.path.exists(target_path):
            return {"files": [], "error": "Path not found"}
        
        def build_tree(dir_path: str, relative_path: str = "") -> list:
            items = []
            try:
                for entry in sorted(os.listdir(dir_path)):
                    # Skip hidden files and common ignore patterns
                    if entry.startswith('.') or entry in ['node_modules', '__pycache__', 'dist', 'build']:
                        continue
                    
                    full_path = os.path.join(dir_path, entry)
                    rel_path = os.path.join(relative_path, entry) if relative_path else entry
                    
                    if os.path.isdir(full_path):
                        items.append({
                            "name": entry,
                            "path": rel_path,
                            "type": "directory",
                            "children": build_tree(full_path, rel_path)
                        })
                    else:
                        try:
                            size = os.path.getsize(full_path)
                            items.append({
                                "name": entry,
                                "path": rel_path,
                                "type": "file",
                                "size": size
                            })
                        except:
                            pass
            except Exception as e:
                logger.error(f"Error reading directory {dir_path}: {e}")
            
            return items
        
        files = build_tree(target_path, path)
        return {"files": files}
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return {"files": [], "error": str(e)}


@app.get("/api/workspace/file-content")
async def get_file_content(file_path: str):
    """读取workspace中的文件内容"""
    try:
        workspace_path = get_or_create_workspace()
        full_path = os.path.join(workspace_path, file_path)
        
        # Security check: ensure file is within workspace
        if not os.path.abspath(full_path).startswith(os.path.abspath(workspace_path)):
            return {"error": "Access denied"}, 403
        
        if not os.path.exists(full_path):
            return {"error": "File not found"}, 404
        
        if not os.path.isfile(full_path):
            return {"error": "Not a file"}, 400
        
        # Check file size (limit to 1MB)
        file_size = os.path.getsize(full_path)
        if file_size > 1024 * 1024:
            return {"error": "File too large (max 1MB)"}, 413
        
        # Try to read as text
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"content": content, "encoding": "utf-8"}
        except UnicodeDecodeError:
            # Try other encodings
            for encoding in ['gbk', 'latin-1']:
                try:
                    with open(full_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    return {"content": content, "encoding": encoding}
                except:
                    continue
            # If all fail, return as binary
            return {"error": "Binary file or unsupported encoding"}, 415
            
    except Exception as e:
        logger.error(f"读取文件失败 {file_path}: {e}")
        return {"error": str(e)}, 500


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "active_tasks": len(task_manager.tasks),
        "active_connections": len(heartbeat_manager.connections),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "WebSocket Stream Service with DataModel",
        "version": "2.2.0",
        "websocket_endpoint": "/ws",
        "datamodel": "ParseData-based unified message format",
        "features": [
            "heartbeat_mechanism",
            "optimized_history_storage",
            "parallel_task_support",
            "stream_parsing",
            "session_history_api"
        ]
    }


# 全局管理器
@app.post("/api/clean-lock")
async def clean_lock():
    """
    清理Claude Code的锁文件以防止EBADF错误
    """
    try:
        # 获取用户主目录
        home_dir = os.path.expanduser("~")
        lock_file = os.path.join(home_dir, ".claude", "history.jsonl.lock")
        
        if os.path.exists(lock_file):
            os.remove(lock_file)
            logger.info(f"已清理锁文件: {lock_file}")
            return {"success": True, "message": "锁文件已清理"}
        else:
            return {"success": True, "message": "无锁文件需要清理"}
            
    except Exception as e:
        logger.error(f"清理锁文件失败: {e}")
        return {"success": False, "message": str(e)}


def kill_port(port):
    """强制终止占用指定端口的进程"""
    import signal
    try:
        if IS_WINDOWS:
            cmd = f"netstat -ano | findstr :{port}"
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                pids = set()
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5 and "LISTENING" in line: # 只杀监听端口的进程
                        pids.add(parts[-1])
                
                for pid in pids:
                    if pid != str(os.getpid()): # 防止自杀
                        logger.info(f"正在终止占用端口 {port} 的进程 PID: {pid}")
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Linux/Mac
            cmd = f"lsof -t -i:{port}"
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.stdout:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid and pid != str(os.getpid()):
                        logger.info(f"正在终止占用端口 {port} 的进程 PID: {pid}")
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        except Exception as e:
                            logger.error(f"终止进程失败: {e}")
            
            # 双重保险：尝试 fuser
            try:
                subprocess.run(f"fuser -k -n tcp {port}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass

        time.sleep(1)  # 等待释放
    except Exception as e:
        logger.error(f"清理端口失败: {e}")

if __name__ == "__main__":

    import uvicorn
    # 从配置文件读取端口，环境变量可以覆盖配置文件
    port = config.PORT
    host = config.HOST
    
    # 启动前先清理端口

    ports = [port, "5690"]
    for p in ports:
        kill_port(p)
    
    print(f"启动WebSocket服务（v2.1 - 心跳机制 + 优化历史）: {host}:{port}")
    print(f"   - 心跳间隔: {HEARTBEAT_INTERVAL}秒")
    print(f"   - 心跳超时: {HEARTBEAT_TIMEOUT}秒")
    print(f"   - 历史保存: history/{{session_id}}_raw.json | _parsed.txt | _structured.json")
    uvicorn.run(app, host=host, port=port)
