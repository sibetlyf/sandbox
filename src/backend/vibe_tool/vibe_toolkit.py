#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agno Toolkit - 封装 ccr/opencode CLI 工具"""

from typing import List
import asyncio
import os
import platform
import shlex
import signal
import subprocess
import sys
import uuid

import json
from dataclasses import asdict
from agno.tools import Toolkit
from agno.run.agent import ToolCallStartedEvent, ToolExecution, RunContentEvent
from agno.run.base import RunContext

# 确保 backend 目录在 path 中
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from .datamodel import ParseData
from .external_agent_run_response_event import ExternalAgentRunResponseContentEvent

IS_WINDOWS = platform.system() == "Windows"


class VibeCodingToolkit(Toolkit):
    """调用 ccr/opencode CLI 的 Agno 工具"""

    def __init__(self, agent_type: str = "ccr", workspace_path: str = None):
        super().__init__(
            name="vibe_coding",
            instructions="用于调用vibecoding的工具，负责处理一切项目级的复杂编程任务"
        )
        self.agent_type = agent_type
        self.workspace_path = workspace_path or os.getcwd()
        self.register(self.arun_prompt)

    def _build_cmd(self, prompt: str, session_id: str = None, use_resume: bool = False) -> list:
        """构建 CLI 命令列表"""
        # Windows 下写临时文件传 prompt，彻底绕开 cmd.exe 引号/转义问题
        if IS_WINDOWS:
            import tempfile
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            tmp.write(prompt)
            tmp.close()
            self._prompt_tmp = tmp.name     # 记录路径便于 finally 中删除
            prompt_arg = f'$(type "{tmp.name}")'
            # ccr 支持 -p @file 或 -p "$(cat file)"，这里直接把提示词从文件读给 shell
            # Windows 下用 PowerShell 来支持 $() 语法更稳妥
            session = f"-r {session_id}" if session_id and use_resume else ""
            if self.agent_type == "opencode":
                session = f"--session {session_id}" if session_id and use_resume else ""
                cmd_base = f'opencode {session} --format json'.strip()
            else:
                cmd_base = f'ccr code -p {session} --output-format stream-json --verbose --dangerously-skip-permissions'.strip()
            # 用 PowerShell 读取临时文件并传给 CLI
            ps_script = (
                f'cd "{self.workspace_path}"; '
                f'[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; '
                f'$p = Get-Content -Path "{tmp.name}" -Raw; '
                f'{cmd_base} $p'
            )
            return ["powershell.exe", "-NoProfile", "-Command", ps_script]

        # POSIX：shlex 引号安全
        self._prompt_tmp = None
        escaped = shlex.quote(prompt)
        session = f"-r {session_id}" if session_id and use_resume else ""
        if self.agent_type == "opencode":
            session = f"--session {session_id}" if session_id and use_resume else ""
            cmd = f"opencode {session} --format json {escaped}".strip()
        else:
            cmd = f"ccr code -p {session} --output-format stream-json --verbose --dangerously-skip-permissions {escaped}".strip()
        return ["/bin/bash", "-c", f"cd {shlex.quote(self.workspace_path)} && {cmd}"]


    async def arun_prompt(self, run_context: RunContext, prompt: str, session_id: str = None, use_resume: bool = False):
        """异步执行编程任务，将 CLI 的流式 JSON 解析后推给 Agno"""
        if self.agent_type == "opencode":
            from .opencode_parser import OpenCodeStreamParser as _Parser, OpenCodeMessageExtractor as _Extractor
        else:
            from .parser import StreamParser as _Parser, MessageExtractor as _Extractor

        parser = _Parser(max_workers=4)
        extractor = _Extractor()
        last_text_by_id = {}

        cmd = self._build_cmd(prompt, session_id, use_resume)
        env = {**os.environ, "PYTHONUNBUFFERED": "1"}
        kwargs = dict(stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, env=env)
        if IS_WINDOWS:
            kwargs["cwd"] = self.workspace_path
        else:
            kwargs["start_new_session"] = True

        process = await asyncio.create_subprocess_exec(*cmd, **kwargs)

        def _make_event(content: str|List, meta=None) -> ExternalAgentRunResponseContentEvent:
            return ExternalAgentRunResponseContentEvent(
                type="document",
                agent_id=run_context.session_id,
                agent_name=run_context.session_id,
                run_id=run_context.run_id,
                session_id=run_context.session_id,
                content=content,
                metadata=meta,
            )

        try:
            while True:
                raw = await process.stdout.readline()
                if not raw:
                    break

                line = raw.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("{"):
                    continue

                # 解析 JSON -> ParseData
                parse_data: ParseData = None
                async for pd in parser.parse_line_async(line):
                    parse_data = pd
                    break

                if parse_data is None:
                    continue

                # type=result → 任务完成
                if parse_data.type == "result":
                    metadata = RunContentEvent(
                        agent_id=run_context.session_id,
                        agent_name=run_context.run_id,
                        run_id=run_context.run_id,
                        session_id=run_context.session_id,
                        content_type="html",
                        content=parse_data.message,
                    )

                    yield ExternalAgentRunResponseContentEvent(
                        type="content",
                        agent_id=run_context.session_id,
                        agent_name=run_context.session_id,
                        run_id=run_context.run_id,
                        session_id=run_context.session_id,
                        content=parse_data.message,
                        metadata=metadata
                    )
                    await asyncio.sleep(0.0001)

                    print(f"result: {parse_data.message}")
                    break

                # 提取文本增量（只算 delta，避免重复）
                text_content = await extractor.extract_text_content(parse_data)
                msg_id = parse_data.uuid or "default"
                last_text = last_text_by_id.get(msg_id, "")
                new_text = text_content[len(last_text):] if len(text_content) > len(last_text) else ""
                if new_text:
                    last_text_by_id[msg_id] = text_content

                # TodoItem → 推带 ToolCallStartedEvent metadata 的事件
                for todo in (parse_data.todo_list or []):

                    content = json.dumps([asdict(t) for t in parse_data.todo_list], ensure_ascii=False)
                    yield _make_event(
                        content=content,
                        meta=ToolCallStartedEvent(
                            agent_id=run_context.session_id,
                            agent_name=run_context.run_id,
                            run_id=run_context.run_id,
                            session_id=run_context.session_id,
                            tool=ToolExecution(
                                tool_call_id=msg_id,
                                tool_name="TodoItem",
                                tool_args={"content": todo.content, "status": todo.status, "activeForm": todo.activeForm}
                            )
                        )
                    )
                    new_text = ""
                    await asyncio.sleep(0.0001)

                # ToolCall → 推带 ToolCallStartedEvent metadata 的事件
                for tc in (parse_data.tool_calls or []):

                    content = json.dumps([asdict(t) for t in parse_data.tool_calls], ensure_ascii=False)
                    yield _make_event(
                        content=content or '',
                        meta=ToolCallStartedEvent(
                            tool=ToolExecution(
                                tool_call_id=tc.id or f"call_{msg_id}",
                                tool_name=tc.name,
                                tool_args=tc.input
                            )
                        )
                    )
                    new_text = ""
                    await asyncio.sleep(0.0001)
                
                # ToolCallResult → 推带 ToolCallCompletedEvent metadata 的事件
                if parse_data.tool_use_result:
                    content = json.dumps(parse_data.tool_use_result, ensure_ascii=False)
                    yield _make_event(
                        content=content or '',
                        meta=ToolCallStartedEvent(
                            tool=ToolExecution(
                                tool_call_id=f"result_{msg_id}",
                                tool_name="ToolResult",
                                tool_args=parse_data.tool_use_result
                            )
                        )
                    )
                    new_text = ""
                    await asyncio.sleep(0.0001)
                    

                # 剩余文本直接推出
                if new_text and new_text.strip():
                    yield _make_event(
                        content=new_text,
                        meta=RunContentEvent(
                            agent_id=run_context.session_id,
                            agent_name=run_context.run_id,
                            run_id=run_context.run_id,
                            session_id=run_context.session_id,
                            content_type="html",
                            content=parse_data.message,
                        )
                    )

                await asyncio.sleep(0.0001)

        finally:
            parser.shutdown()
            if 'process' in locals() and process.returncode is None:
                try:
                    if IS_WINDOWS:
                        # Windows: 强制终止进程树 (/T)
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=False
                        )
                    else:
                        # POSIX: 终止整个进程组 (启动时使用了 start_new_session=True)
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass

            # 清理 Windows 临时 prompt 文件
            tmp = getattr(self, '_prompt_tmp', None)
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except Exception:
                    pass
