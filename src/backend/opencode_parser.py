#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 datamodel 的异步消息解析器 - OpenCode SDK 版本
用于解析 OpenCode SDK 返回的流式消息并转换为 ParseData 对象
"""

import json
import asyncio
from typing import Optional, Dict, Any, AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from datamodel import ParseData, Usage, ToolCall


class OpenCodeStreamParser:
    """OpenCode SDK 流式消息解析器"""

    def __init__(self, max_workers: Optional[int] = None):
        """
        初始化解析器

        Args:
            max_workers: 线程池最大工作线程数
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers or 4)
        self._parse_cache = {}  # 缓存解析结果

    async def parse_line_async(self, line: str) -> AsyncIterator[Optional[ParseData]]:
        """
        异步解析单行 JSON 消息 (JSONL 格式)

        Args:
            line: JSON 字符串

        Yields:
            ParseData 对象，如果解析失败则返回 None
        """
        if not line or not line.strip():
            await asyncio.sleep(0)
            yield None
            return

        line = line.strip()

        # 检查缓存
        if line in self._parse_cache:
            await asyncio.sleep(0)
            yield self._parse_cache[line]
            return

        try:
            # 在线程池中解析 JSON
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(self.executor, json.loads, line)
            
            # 转换为 ParseData
            parse_data = await self._convert_to_parse_data_async(data)

            # 缓存结果（限制缓存大小）
            if len(self._parse_cache) < 1000:
                self._parse_cache[line] = parse_data

            await asyncio.sleep(0)
            yield parse_data

        except json.JSONDecodeError:
            await asyncio.sleep(0)
            yield None
        except Exception as e:
            # 记录错误但不抛出异常
            await asyncio.sleep(0)
            yield None

    async def _convert_to_parse_data_async(self, data: Dict[str, Any]) -> ParseData:
        """
        将 OpenCode 格式的消息转换为 ParseData 对象

        Args:
            data: OpenCode 消息字典

        Returns:
            ParseData 对象
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._convert_to_parse_data, data)

    def _convert_to_parse_data(self, data: Dict[str, Any]) -> ParseData:
        """
        同步版本：将 OpenCode 格式的消息转换为 ParseData 对象

        OpenCode 消息格式映射:
        - type="error": 错误消息
        - type="step_start": 步骤开始
        - type="step_finish": 步骤完成（包含 tokens 和 cost）
        - type="text": 文本内容
        - type="tool_use": 工具调用

        字段映射:
        - sessionID -> session_id
        - part.id -> uuid
        - part.messageID -> parent_tool_use_id (如果是工具结果)
        - part -> message (重构后的内容)

        Args:
            data: OpenCode 消息字典

        Returns:
            ParseData 对象
        """
        msg_type = data.get("type", "")
        
        # 提取通用字段
        session_id = data.get("sessionID")
        timestamp = data.get("timestamp")
        part = data.get("part", {})
        
        # 从 part 中提取字段
        uuid = part.get("id")
        message_id = part.get("messageID")
        part_type = part.get("type")
        
        # 处理不同类型的消息
        if msg_type == "error":
            # 错误消息
            error_data = data.get("error", {})
            return ParseData(
                type="error",
                subtype=error_data.get("name"),
                message={
                    "error": error_data,
                    "timestamp": timestamp,
                    "sessionID": session_id
                },
                session_id=session_id,
                uuid=uuid
            )
        
        elif msg_type == "step_start":
            # 步骤开始
            return ParseData(
                type="step_start",
                message={
                    "part": part,
                    "timestamp": timestamp
                },
                session_id=session_id,
                uuid=uuid
            )
        
        elif msg_type == "step_finish":
            # 步骤完成 - 提取 tokens 和 cost
            reason = part.get("reason")
            cost = part.get("cost", 0)
            tokens = part.get("tokens", {})
            
            usage = Usage(
                input_tokens=tokens.get("input", 0),
                output_tokens=tokens.get("output", 0),
                cache_creation_input_tokens=0,
                cache_read_input_tokens=tokens.get("cache", {}).get("read", 0)
            ) if tokens else None
            
            return ParseData(
                type="step_finish",
                subtype=reason,
                message={
                    "part": part,
                    "timestamp": timestamp,
                    "reason": reason,
                    "cost": cost
                },
                usage=usage,
                session_id=session_id,
                uuid=uuid
            )
        
        elif msg_type == "text":
            # 文本消息 - 提取文本内容
            text_content = part.get("text", "")
            time_info = part.get("time", {})
            
            # 构建类似 Claude 格式的 message 结构
            message = {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": text_content
                    }
                ],
                "part": part,
                "timestamp": timestamp
            }
            
            return ParseData(
                type="text",
                subtype=part_type,
                message=message,
                session_id=session_id,
                uuid=uuid
            )
        
        elif msg_type == "tool_use":
            # 工具调用 - 提取工具信息
            tool_name = part.get("tool", "")
            call_id = part.get("callID", "")
            state = part.get("state", {})
            tool_input = state.get("input", {})
            tool_output = state.get("output")
            tool_status = state.get("status")
            tool_title = state.get("title")
            tool_metadata = state.get("metadata", {})
            time_info = state.get("time", {})
            
            # 创建 ToolCall 对象
            tool_call = ToolCall(
                name=tool_name,
                input=tool_input,
                id=call_id
            )
            
            # 构建 message 结构（包含工具调用和结果）
            message = {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": call_id,
                        "name": tool_name,
                        "input": tool_input
                    }
                ],
                "part": part,
                "timestamp": timestamp
            }
            
            # 如果有工具结果，添加到 tool_use_result
            tool_use_result = None
            if tool_output is not None:
                tool_use_result = {
                    "type": "tool_result",
                    "tool_use_id": call_id,
                    "content": tool_output,
                    "status": tool_status,
                    "title": tool_title,
                    "metadata": tool_metadata,
                    "time": time_info
                }
            
            parse_data = ParseData(
                type="tool_use",
                subtype=tool_name,
                message=message,
                session_id=session_id,
                uuid=uuid,
                parent_tool_use_id=message_id,
                tool_use_result=tool_use_result
            )
            
            # 添加工具调用到列表
            parse_data.tool_calls.append(tool_call)
            
            # 不区分大小写检查工具名称
            tool_name_lower = tool_name.lower()
            
            # 如果是 todowrite，提取 todo 列表
            if tool_name_lower == "todowrite":
                parse_data.todo_list = tool_call.get_todo_list()
            
            # 如果是 write，提取文件信息
            elif tool_name_lower == "write":
                file_info = tool_call.get_write_file_info()
                if file_info:
                    parse_data.write_files.append(file_info)
            
            return parse_data
        
        else:
            # 未知类型：保留原始数据
            return ParseData(
                type=msg_type or "unknown",
                message={
                    "data": data,
                    "part": part,
                    "timestamp": timestamp
                },
                session_id=session_id,
                uuid=uuid
            )

    def parse_line_sync(self, line: str) -> Optional[ParseData]:
        """
        同步解析单行 JSON 消息（用于非异步环境）

        Args:
            line: JSON 字符串

        Returns:
            ParseData 对象，如果解析失败则返回 None
        """
        if not line or not line.strip():
            return None

        line = line.strip()

        try:
            data = json.loads(line)
            return self._convert_to_parse_data(data)
        except (json.JSONDecodeError, Exception):
            return None

    def clear_cache(self):
        """清空缓存"""
        self._parse_cache.clear()

    def shutdown(self):
        """关闭解析器并清理资源"""
        self.executor.shutdown(wait=False)
        self.clear_cache()


class OpenCodeMessageExtractor:
    """OpenCode 消息内容提取器"""

    @staticmethod
    async def extract_text_content(parse_data: ParseData) -> str:
        """
        提取文本内容（从 text 消息中提取）

        Args:
            parse_data: ParseData 对象

        Returns:
            提取的文本内容
        """
        if not parse_data.message:
            return ""

        # 从 part 中提取
        part = parse_data.message.get("part", {})
        if part.get("type") == "text":
            return part.get("text", "")

        # 从 content 中提取（已转换格式）
        content = parse_data.message.get("content", [])
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
            return "".join(text_parts)

        return ""

    @staticmethod
    async def extract_thinking_content(parse_data: ParseData) -> str:
        """
        提取思考内容（OpenCode 不支持 thinking，返回空字符串）

        Args:
            parse_data: ParseData 对象

        Returns:
            空字符串（OpenCode 格式不包含 thinking）
        """
        return ""

    @staticmethod
    async def extract_tool_info(parse_data: ParseData) -> Optional[Dict[str, Any]]:
        """
        提取工具调用信息

        Args:
            parse_data: ParseData 对象

        Returns:
            工具调用信息字典
        """
        if parse_data.type != "tool_use" or not parse_data.message:
            return None

        part = parse_data.message.get("part", {})
        state = part.get("state", {})
        
        return {
            "tool": part.get("tool"),
            "callID": part.get("callID"),
            "status": state.get("status"),
            "input": state.get("input"),
            "output": state.get("output"),
            "title": state.get("title"),
            "metadata": state.get("metadata"),
            "time": state.get("time")
        }

    @staticmethod
    async def extract_error_message(parse_data: ParseData) -> str:
        """
        提取错误消息

        Args:
            parse_data: ParseData 对象

        Returns:
            错误消息文本
        """
        if parse_data.type != "error" or not parse_data.message:
            return ""

        error = parse_data.message.get("error", {})
        error_data = error.get("data", {})
        return error_data.get("message", "")

    @staticmethod
    async def has_tool_calls(parse_data: ParseData) -> bool:
        """
        检查是否包含工具调用

        Args:
            parse_data: ParseData 对象

        Returns:
            是否包含工具调用
        """
        return len(parse_data.tool_calls) > 0

    @staticmethod
    async def has_todo_list(parse_data: ParseData) -> bool:
        """
        检查是否包含 TODO 列表

        Args:
            parse_data: ParseData 对象

        Returns:
            是否包含 TODO 列表
        """
        return parse_data.todo_list is not None and len(parse_data.todo_list) > 0

    @staticmethod
    async def has_write_files(parse_data: ParseData) -> bool:
        """
        检查是否包含文件写入操作

        Args:
            parse_data: ParseData 对象

        Returns:
            是否包含文件写入操作
        """
        return len(parse_data.write_files) > 0

    @staticmethod
    async def get_step_metadata(parse_data: ParseData) -> Optional[Dict[str, Any]]:
        """
        获取步骤元数据（从 step_finish 消息中提取）

        Args:
            parse_data: ParseData 对象

        Returns:
            步骤元数据字典
        """
        if parse_data.type != "step_finish" or not parse_data.message:
            return None

        return {
            "reason": parse_data.message.get("reason"),
            "cost": parse_data.message.get("cost"),
            "usage": {
                "input_tokens": parse_data.usage.input_tokens,
                "output_tokens": parse_data.usage.output_tokens,
                "cache_read_input_tokens": parse_data.usage.cache_read_input_tokens
            } if parse_data.usage else None
        }

    @staticmethod
    async def extract_mermaid_diagrams(parse_data: ParseData) -> list:
        """
        从消息中提取 Mermaid 图表代码

        Args:
            parse_data: ParseData 对象

        Returns:
            Mermaid 代码列表
        """
        import re
        
        text = await OpenCodeMessageExtractor.extract_text_content(parse_data)
        if not text:
            return []
        
        # 匹配 ```mermaid ... ``` 代码块
        pattern = r'```mermaid\s+(.*?)```'
        diagrams = re.findall(pattern, text, re.DOTALL)
        
        # 清理每个图表代码（去除首尾空白）
        return [diagram.strip() for diagram in diagrams if diagram.strip()]


# 测试代码
async def test_parser():
    """测试解析器"""
    import os
    
    log_file = r"H:\MOMA\all_projects.tar\backend_new\logs\opencode.json"
    
    if not os.path.exists(log_file):
        print(f"日志文件不存在: {log_file}")
        return
    
    parser = OpenCodeStreamParser()
    extractor = OpenCodeMessageExtractor()
    
    print(f"开始解析: {log_file}\n")
    print("=" * 80)
    
    parsed_count = 0
    error_count = 0
    step_start_count = 0
    step_finish_count = 0
    text_count = 0
    tool_use_count = 0
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                
                async for parse_data in parser.parse_line_async(line):
                    if parse_data is None:
                        continue
                    
                    parsed_count += 1
                    
                    # 统计消息类型
                    if parse_data.type == "error":
                        error_count += 1
                        error_msg = await extractor.extract_error_message(parse_data)
                        print(f"\n[Error #{error_count}] {error_msg[:100]}")
                    elif parse_data.type == "step_start":
                        step_start_count += 1
                    elif parse_data.type == "step_finish":
                        step_finish_count += 1
                        metadata = await extractor.get_step_metadata(parse_data)
                        if metadata:
                            print(f"\n[Step Finish #{step_finish_count}] Reason: {metadata['reason']}, Cost: {metadata['cost']}")
                    elif parse_data.type == "text":
                        text_count += 1
                        text = await extractor.extract_text_content(parse_data)
                        if text:
                            print(f"\n[Text #{text_count}] {text[:100]}...")
                    elif parse_data.type == "tool_use":
                        tool_use_count += 1
                        tool_info = await extractor.extract_tool_info(parse_data)
                        if tool_info:
                            print(f"\n[Tool Use #{tool_use_count}] Tool: {tool_info['tool']}, Status: {tool_info['status']}")
                            if tool_info['title']:
                                print(f"  Title: {tool_info['title']}")
    
    finally:
        parser.shutdown()
    
    print("\n" + "=" * 80)
    print(f"\n解析统计:")
    print(f"  总计: {parsed_count} 条消息")
    print(f"  - Error: {error_count}")
    print(f"  - Step Start: {step_start_count}")
    print(f"  - Step Finish: {step_finish_count}")
    print(f"  - Text: {text_count}")
    print(f"  - Tool Use: {tool_use_count}")


if __name__ == "__main__":
    asyncio.run(test_parser())
