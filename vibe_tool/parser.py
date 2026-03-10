#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 datamodel 的异步消息解析器
用于解析 Claude Code 返回的流式消息并转换为 ParseData 对象
"""

import json
import asyncio
from typing import Optional, Dict, Any, AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from .datamodel import ParseData


class StreamParser:
    """流式消息解析器"""

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
        异步解析单行 JSON 消息

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
            
            # 异步转换为 ParseData
            parse_data = await ParseData.from_dict_async(data, self.executor)

            # 缓存结果（限制缓存大小）
            if len(self._parse_cache) < 1000000:
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
            return ParseData.from_dict(data)
        except (json.JSONDecodeError, Exception):
            return None

    def clear_cache(self):
        """清空缓存"""
        self._parse_cache.clear()

    def shutdown(self):
        """关闭解析器并清理资源"""
        self.executor.shutdown(wait=False)
        self.clear_cache()


class MessageExtractor:
    """消息内容提取器"""

    @staticmethod
    async def extract_text_content(parse_data: ParseData) -> str:
        """
        提取文本内容

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
        提取思考内容

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
    async def extract_mermaid_diagrams(parse_data: ParseData) -> list:
        """
        从消息中提取 Mermaid 图表代码

        Args:
            parse_data: ParseData 对象

        Returns:
            Mermaid 代码列表
        """
        import re
        
        text = await MessageExtractor.extract_text_content(parse_data)
        if not text:
            return []
        
        # 匹配 ```mermaid ... ``` 代码块
        pattern = r'```mermaid\s+(.*?)```'
        diagrams = re.findall(pattern, text, re.DOTALL)
        
        # 清理每个图表代码（去除首尾空白）
        return [diagram.strip() for diagram in diagrams if diagram.strip()]
