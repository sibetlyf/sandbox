#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 datamodel 的异步消息解析器 - Jiutian Vibecoding 版本
用于解析 Jiutian Vibecoding 返回的流式消息并转换为 ParseData 对象
"""

import json
import asyncio
from typing import Optional, Dict, Any, AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from datamodel import ParseData, Usage


class JiutianStreamParser:
    """Jiutian Vibecoding 流式消息解析器"""

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
        将 Jiutian 格式的消息转换为 ParseData 对象

        Args:
            data: Jiutian 消息字典

        Returns:
            ParseData 对象
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._convert_to_parse_data, data)

    def _convert_to_parse_data(self, data: Dict[str, Any]) -> ParseData:
        """
        同步版本：将 Jiutian 格式的消息转换为 ParseData 对象

        Jiutian 消息格式映射:
        - type="system": 系统初始化消息
        - type="user": 用户消息或工具结果
        - type="assistant": AI 助手回复（包含 thinking 和 text）
        - type="stream_event": 流式事件
        - type="result": 最终结果摘要

        Args:
            data: Jiutian 消息字典

        Returns:
            ParseData 对象
        """
        msg_type = data.get("type", "")
        
        # 提取通用字段
        session_id = data.get("session_id")
        uuid = data.get("uuid")
        parent_tool_use_id = data.get("parent_tool_use_id")
        
        # 处理不同类型的消息
        if msg_type == "system":
            # 系统消息：保留原始数据结构，并提取 subtype
            return ParseData(
                type="system",
                subtype=data.get("subtype"),
                message=data,
                session_id=session_id,
                uuid=uuid,
                model=data.get("model")
            )
        
        elif msg_type == "user":
            # 用户消息：保留 message 字段
            return ParseData(
                type="user",
                message=data.get("message"),
                session_id=session_id,
                uuid=uuid,
                parent_tool_use_id=parent_tool_use_id
            )
        
        elif msg_type == "assistant":
            # 助手消息：提取 thinking 和 text 内容
            message = data.get("message", {})
            usage_data = message.get("usage", {})
            
            usage = Usage(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
                cache_creation_input_tokens=usage_data.get("cache_creation_input_tokens", 0),
                cache_read_input_tokens=usage_data.get("cache_read_input_tokens", 0),
                service_tier=usage_data.get("service_tier"),
                cache_creation=usage_data.get("cache_creation")
            ) if usage_data else None
            
            return ParseData(
                type="assistant",
                message=message,
                model=message.get("model") or data.get("model"),
                usage=usage,
                session_id=session_id,
                uuid=uuid,
                parent_tool_use_id=parent_tool_use_id
            )
        
        elif msg_type == "stream_event":
            # 流式事件：保留 event 数据
            event = data.get("event", {})
            return ParseData(
                type="stream_event",
                message={"event": event},
                session_id=session_id,
                uuid=uuid,
                parent_tool_use_id=parent_tool_use_id
            )
        
        elif msg_type == "result":
            # 结果消息：提取 subtype 和其他结果数据
            usage_data = data.get("usage", {})
            
            usage = Usage(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
                cache_creation_input_tokens=usage_data.get("cache_creation_input_tokens", 0),
                cache_read_input_tokens=usage_data.get("cache_read_input_tokens", 0),
                service_tier=usage_data.get("service_tier"),
                cache_creation=usage_data.get("cache_creation")
            ) if usage_data else None
            
            return ParseData(
                type="result",
                subtype=data.get("subtype"),
                message={
                    "result": data.get("result"),
                    "duration_ms": data.get("duration_ms"),
                    "duration_api_ms": data.get("duration_api_ms"),
                    "num_turns": data.get("num_turns"),
                    "is_error": data.get("is_error"),
                    "permission_denials": data.get("permission_denials", [])
                },
                usage=usage,
                session_id=session_id,
                uuid=uuid
            )
        
        else:
            # 未知类型：保留原始数据
            return ParseData(
                type=msg_type or "unknown",
                message=data,
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


class JiutianMessageExtractor:
    """Jiutian 消息内容提取器"""

    @staticmethod
    async def extract_text_content(parse_data: ParseData) -> str:
        """
        提取文本内容（从 assistant 消息中提取 text 类型内容）

        Args:
            parse_data: ParseData 对象

        Returns:
            提取的文本内容
        """
        if not parse_data.message:
            return ""

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
        提取思考内容（从 assistant 消息中提取 thinking 类型内容）

        Args:
            parse_data: ParseData 对象

        Returns:
            提取的思考内容
        """
        if not parse_data.message:
            return ""

        content = parse_data.message.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "thinking":
                    return item.get("thinking", "")

        return ""

    @staticmethod
    async def extract_result_summary(parse_data: ParseData) -> str:
        """
        提取结果摘要（从 result 消息中提取）

        Args:
            parse_data: ParseData 对象

        Returns:
            提取的结果摘要
        """
        if parse_data.type != "result" or not parse_data.message:
            return ""

        return parse_data.message.get("result", "")

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
    async def get_event_type(parse_data: ParseData) -> Optional[str]:
        """
        获取流式事件类型

        Args:
            parse_data: ParseData 对象

        Returns:
            事件类型，如果不是 stream_event 则返回 None
        """
        if parse_data.type != "stream_event" or not parse_data.message:
            return None

        event = parse_data.message.get("event", {})
        return event.get("type")


# 测试代码
async def test_parser():
    """测试解析器"""
    import os
    
    log_file = r"H:\MOMA\temp\minimax\all_projects.tar\backend_new\logs\log.json"
    
    if not os.path.exists(log_file):
        print(f"日志文件不存在: {log_file}")
        return
    
    parser = JiutianStreamParser()
    extractor = JiutianMessageExtractor()
    
    print(f"开始解析: {log_file}\n")
    print("=" * 80)
    
    parsed_count = 0
    system_count = 0
    user_count = 0
    assistant_count = 0
    stream_event_count = 0
    result_count = 0
    
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
                    if parse_data.type == "system":
                        system_count += 1
                    elif parse_data.type == "user":
                        user_count += 1
                    elif parse_data.type == "assistant":
                        assistant_count += 1
                        # 提取并显示 thinking 和 text 内容
                        thinking = await extractor.extract_thinking_content(parse_data)
                        text = await extractor.extract_text_content(parse_data)
                        if thinking:
                            print(f"\n[Assistant #{assistant_count}] Thinking:")
                            print(f"  {thinking[:100]}..." if len(thinking) > 100 else f"  {thinking}")
                        if text:
                            print(f"\n[Assistant #{assistant_count}] Text:")
                            print(f"  {text[:100]}..." if len(text) > 100 else f"  {text}")
                    elif parse_data.type == "stream_event":
                        stream_event_count += 1
                    elif parse_data.type == "result":
                        result_count += 1
                        result_summary = await extractor.extract_result_summary(parse_data)
                        print(f"\n[Result] Summary:")
                        print(f"  {result_summary[:200]}..." if len(result_summary) > 200 else f"  {result_summary}")
    
    finally:
        parser.shutdown()
    
    print("\n" + "=" * 80)
    print(f"\n解析统计:")
    print(f"  总计: {parsed_count} 条消息")
    print(f"  - System: {system_count}")
    print(f"  - User: {user_count}")
    print(f"  - Assistant: {assistant_count}")
    print(f"  - Stream Event: {stream_event_count}")
    print(f"  - Result: {result_count}")


if __name__ == "__main__":
    asyncio.run(test_parser())
