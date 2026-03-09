#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse JSON 数据模型 - 异步并行版本"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import json
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor


@dataclass
class TodoItem:
    """Todo 项"""
    content: str
    status: str
    activeForm: Optional[str] = None


@dataclass
class ToolCall:
    """工具调用"""
    name: str
    input: Dict[str, Any]
    id: Optional[str] = None
    
    def get_todo_list(self) -> Optional[List[TodoItem]]:
        """提取 Todo 列表"""
        # 支持原始名称或可能的映射名称（不区分大小写）
        tool_name_lower = self.name.lower()
        if (tool_name_lower == "todowrite" or self.name.startswith("tool_")) and "todos" in self.input:
            todos = self.input.get("todos", [])
            if isinstance(todos, list):
                return [TodoItem(item.get("content", ""), item.get("status", "pending"), item.get("activeForm"))
                        for item in todos if isinstance(item, dict)]
        return None
    
    def get_write_file_info(self) -> Optional[Dict[str, str]]:
        """提取 Write 文件信息"""
        # 支持原始名称或可能的映射名称（不区分大小写）
        tool_name_lower = self.name.lower()
        if (tool_name_lower == "write" or self.name.startswith("tool_")) and "file_path" in self.input and "content" in self.input:
            return {"file_path": self.input["file_path"], "content": self.input["content"]}
        return None


@dataclass
class Usage:
    """Token 使用情况"""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    service_tier: Optional[str] = None
    cache_creation: Optional[Dict[str, Any]] = None


@dataclass
class ParseData:
    """Parse JSON 数据模型"""
    type: str
    subtype: Optional[str] = None
    message: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    usage: Optional[Usage] = None
    session_id: Optional[str] = None
    uuid: Optional[str] = None
    parent_tool_use_id: Optional[str] = None
    tool_use_result: Optional[Dict[str, Any]] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    todo_list: Optional[List[TodoItem]] = None
    write_files: List[Dict[str, str]] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParseData':
        """从字典创建 ParseData 对象"""
        if not data:
            return cls(type="empty")

        # 处理嵌套的 parse_data (从历史记录文件加载时可能存在)
        if "parse_data" in data and isinstance(data["parse_data"], dict):
            inner_data = data["parse_data"]
            # 合并顶层的 session_id/uuid 等字段（如果内部没有）
            for key in ["session_id", "uuid", "model"]:
                if key in data and key not in inner_data:
                    inner_data[key] = data[key]
            data = inner_data

        usage_data = data.get("usage", {})
        usage = Usage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
            cache_creation_input_tokens=usage_data.get("cache_creation_input_tokens", 0),
            cache_read_input_tokens=usage_data.get("cache_read_input_tokens", 0),
            service_tier=usage_data.get("service_tier"),
            cache_creation=usage_data.get("cache_creation")
        ) if usage_data else None
        
        parse_data = cls(
            type=data.get("type", ""),
            subtype=data.get("subtype"),
            message=data.get("message"),
            model=data.get("model"),
            usage=usage,
            session_id=data.get("session_id"),
            uuid=data.get("uuid"),
            parent_tool_use_id=data.get("parent_tool_use_id"),
            tool_use_result=data.get("tool_use_result")
        )
        
        # 解析工具调用
        content = parse_data.message.get("content", []) if parse_data.message else []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                tool_call = ToolCall(
                    name=item.get("name", ""),
                    input=item.get("input", {}),
                    id=item.get("id")
                )
                parse_data.tool_calls.append(tool_call)
                
                # 不区分大小写检查工具名称
                tool_name_lower = tool_call.name.lower()
                if tool_name_lower == "todowrite":
                    parse_data.todo_list = tool_call.get_todo_list()
                elif tool_name_lower == "write":
                    file_info = tool_call.get_write_file_info()
                    if file_info:
                        parse_data.write_files.append(file_info)
        
        return parse_data
    
    @classmethod
    async def from_dict_async(cls, data: Dict[str, Any], executor: ThreadPoolExecutor) -> 'ParseData':
        """异步版本"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, cls.from_dict, data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "type": self.type,
            "model": self.model,
            "session_id": self.session_id,
            "uuid": self.uuid,
            "parent_tool_use_id": self.parent_tool_use_id,
        }
        if self.subtype:
            result["subtype"] = self.subtype
        if self.message:
            result["message"] = self.message
        if self.usage:
            result["usage"] = {
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
                "cache_creation_input_tokens": self.usage.cache_creation_input_tokens,
                "cache_read_input_tokens": self.usage.cache_read_input_tokens,
                "service_tier": self.usage.service_tier,
                "cache_creation": self.usage.cache_creation
            }
        if self.tool_calls:
            result["tool_calls"] = [{"name": tc.name, "input": tc.input, "id": tc.id} for tc in self.tool_calls]
        if self.todo_list:
            result["todo_list"] = [{"content": t.content, "status": t.status, "activeForm": t.activeForm} for t in self.todo_list]
        if self.write_files:
            result["write_files"] = self.write_files
        if self.tool_use_result:
            result["tool_use_result"] = self.tool_use_result
        return result


def _get_file_path(file_path: str) -> str:
    """获取绝对路径"""
    return file_path if os.path.isabs(file_path) else os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)


async def load_parse_json_async(file_path: str, max_workers: Optional[int] = None) -> List[ParseData]:
    """异步并行加载 JSON 文件"""
    file_path = _get_file_path(file_path)
    loop = asyncio.get_event_loop()
    
    def read_file():
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            
            # 如果是标准的 JSON 数组，直接加载
            if content.startswith('['):
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass
            
            # 如果是 JSONL 或 连续的 JSON 对象 (由 append 产生)
            results = []
            decoder = json.JSONDecoder()
            pos = 0
            content_len = len(content)
            while pos < content_len:
                # 跳过空白字符
                while pos < content_len and content[pos].isspace():
                    pos += 1
                if pos >= content_len:
                    break
                
                try:
                    obj, pos = decoder.raw_decode(content, pos)
                    results.append(obj)
                except json.JSONDecodeError:
                    # 尝试寻找下一个 '{' or '[' 开始
                    next_obj_start = content.find('{', pos)
                    if next_obj_start == -1:
                        next_obj_start = content.find('[', pos)
                    
                    if next_obj_start == -1:
                        break
                    pos = next_obj_start
            return results
    
    data = await loop.run_in_executor(None, read_file)
    
    # 并行解析
    max_workers = max_workers or min(len(data), os.cpu_count() or 4)
    executor = ThreadPoolExecutor(max_workers=max_workers)
    parse_data_list = await asyncio.gather(*[ParseData.from_dict_async(item, executor) for item in data])
    executor.shutdown(wait=False)
    
    return list(parse_data_list)


async def save_parse_data_list_async(parse_data_list: List[ParseData], file_path: str, max_workers: Optional[int] = None):
    """异步并行保存"""
    file_path = _get_file_path(file_path)
    loop = asyncio.get_event_loop()
    
    # 并行转换为字典
    max_workers = max_workers or min(len(parse_data_list), os.cpu_count() or 4)
    executor = ThreadPoolExecutor(max_workers=max_workers)
    data = await asyncio.gather(*[loop.run_in_executor(executor, item.to_dict) for item in parse_data_list])
    executor.shutdown(wait=False)
    
    # 写入文件
    def write_file():
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    await loop.run_in_executor(None, write_file)




async def main_async():
    """主函数"""
    import time
    
    start_time = time.time()
    parse_data_list = await load_parse_json_async(r"H:\MOMA\sandbox\src\backend\vibe_tool\logs\output.json")
    load_time = time.time() - start_time
    
    print(f"成功加载 {len(parse_data_list)} 条记录（耗时: {load_time:.2f}秒）\n")
    
    # 打印所有解析后的 JSON 块并保存到文件
    output_file = _get_file_path("parsed_output.txt")
    print("=" * 80)
    print("所有解析后的 JSON 块:\n")
    print(f"同时保存到: {output_file}\n")
    
    # 并行转换为字典
    max_workers = min(len(parse_data_list), os.cpu_count() or 4)
    executor = ThreadPoolExecutor(max_workers=max_workers)
    loop = asyncio.get_event_loop()
    dict_list = await asyncio.gather(*[loop.run_in_executor(executor, item.to_dict) for item in parse_data_list])
    executor.shutdown(wait=False)
    
    # 打印所有 JSON 块并保存到文件
    def write_and_print(text: str, file_handle):
        print(text, end='')
        file_handle.write(text)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, data_dict in enumerate(dict_list, 1):
            header = f"[{idx}] " + "=" * 76 + "\n"
            json_str = json.dumps(data_dict, ensure_ascii=False, indent=2) + "\n\n"
            write_and_print(header, f)
            write_and_print(json_str, f)
    
    print(f"\n已保存到: {output_file}")


if __name__ == "__main__":
    asyncio.run(main_async())
