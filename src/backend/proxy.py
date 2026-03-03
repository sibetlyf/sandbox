import json
import os
import time
import logging
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn
from openai import AsyncOpenAI

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CONFIG_FILE = 'proxy-config.json'
LOGS_DIR = 'logs'
DEFAULT_PORT = 30056

os.makedirs(LOGS_DIR, exist_ok=True)

app = FastAPI()


def load_config() -> Dict[str, Any]:
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Config load error: {e}")
    return {"customParams": {}}


@app.post("/chat/completions")
async def chat_completions(request: Request):
    config = load_config()
    stream_log_file = os.path.join(LOGS_DIR, 'stream-debug.jsonl')
    
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    # 合并自定义参数
    request_params = {**body, **config.get("customParams", {}), "stream": True}
    model = request_params.get("model", "unknown")
    
    print(f"[Proxy] New Request: {model}")
    
    # 记录请求
    try:
        with open(stream_log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n--- Request Start {time.strftime('%Y-%m-%dT%H:%M:%S%z')} ---\n")
            f.write(json.dumps({"type": "request", "model": model}) + "\n")
    except Exception:
        pass

    target_base_url = config.get("targetBaseUrl", "https://jiutian.10086.cn/largemodel/moma/api/v3")
    auth_header = request.headers.get("authorization", "")
    api_key = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else "dummy-key"
    
    client = AsyncOpenAI(base_url=target_base_url, api_key=api_key, timeout=60000)
    
    async def response_generator():
        chunk_count = 0
        skipped_count = 0
        
        # 跟踪流状态
        has_finish_reason = False
        has_tool_calls = False
        has_content = False
        has_reasoning = False
        last_chunk_info = {"id": "chatcmpl-proxy", "model": model, "created": int(time.time())}
        
        # 提取tools定义，用于补充tool_calls元数据
        tools_map = {}
        if "tools" in request_params and request_params["tools"]:
            for tool in request_params["tools"]:
                if "function" in tool and "name" in tool["function"]:
                    tool_name = tool["function"]["name"]
                    tools_map[tool_name] = tool["function"]
        
        logger.info(f"Available tools: {list(tools_map.keys())}")
        
        try:
            # 分离标准参数和额外参数
            STANDARD_PARAMS = {
                "messages", "model", "frequency_penalty", "logit_bias", "logprobs", 
                "top_logprobs", "max_tokens", "n", "presence_penalty", "response_format", 
                "seed", "stop", "stream", "stream_options", "temperature", "top_p", 
                "tools", "tool_choice", "parallel_tool_calls", "user", "service_tier"
            }
            
            create_kwargs = {}
            extra_body = {}
            for k, v in request_params.items():
                if k == "stream":
                    continue
                if k in STANDARD_PARAMS:
                    create_kwargs[k] = v
                else:
                    extra_body[k] = v
            
            stream = await client.chat.completions.create(
                stream=True,
                extra_body=extra_body if extra_body else None,
                **create_kwargs
            )
            
            async for chunk in stream:
                chunk_count += 1
                chunk_dict = chunk.model_dump(exclude_unset=True)
                
                # 更新最后chunk信息
                last_chunk_info = {
                    "id": chunk_dict.get("id", last_chunk_info["id"]),
                    "model": chunk_dict.get("model", last_chunk_info["model"]),
                    "created": chunk_dict.get("created", last_chunk_info["created"])
                }
                
                # 检查是否应该跳过这个chunk
                should_skip = False
                
                # 九天API在最后返回的usage chunk中choices是空数组
                # 这会导致客户端在非流式模式聚合时失败
                # 策略：跳过这个chunk，usage信息的丢失是可接受的，因为：
                # 1. finish_reason已经在前一个chunk中
                # 2. 客户端对usage缺失有容错处理  
                # 3. token计数可以从其他chunk中获取
                if "choices" in chunk_dict and len(chunk_dict["choices"]) == 0:
                    if "usage" in chunk_dict:
                        logger.info(f"跳过空choices的usage chunk: {chunk_dict.get('usage')}")
                    should_skip = True
                elif "choices" in chunk_dict and len(chunk_dict["choices"]) > 0:
                    choice = chunk_dict["choices"][0]
                    delta = choice.get("delta", {})
                    
                    # 跟踪流状态
                    if choice.get("finish_reason"):
                        has_finish_reason = True
                    
                    # 修复不完整的tool_calls
                    if delta.get("tool_calls"):
                        has_tool_calls = True
                        
                        # 九天API可能返回不完整的tool_calls（缺少id、name、type）
                        # 需要补充这些字段
                        for tool_call in delta["tool_calls"]:
                            # 补充id（如果缺失）
                            if "id" not in tool_call or not tool_call["id"]:
                                tool_call["id"] = f"chatcmpl-tool-{int(time.time() * 1000)}-{tool_call.get('index', 0)}"
                            
                            # 补充type（如果缺失）
                            if "type" not in tool_call:
                                tool_call["type"] = "function"
                            
                            # 补充function.name（如果缺失）
                            if "function" in tool_call:
                                func = tool_call["function"]
                                if "name" not in func or not func["name"]:
                                    # 尝试从arguments推断工具名称
                                    inferred_name = None
                                    if "arguments" in func and func["arguments"]:
                                        try:
                                            args = json.loads(func["arguments"]) if isinstance(func["arguments"], str) else func["arguments"]
                                            arg_keys = set(args.keys())
                                            
                                            # 根据参数结构精确匹配工具
                                            # 检查每个工具的参数签名
                                            for tool_name, tool_def in tools_map.items():
                                                if "parameters" in tool_def:
                                                    required_params = set(tool_def["parameters"].get("required", []))
                                                    all_params = set(tool_def["parameters"].get("properties", {}).keys())
                                                    
                                                    # 如果参数的所有key都在工具的参数定义中，且包含所有必需参数
                                                    if arg_keys.issubset(all_params) and required_params.issubset(arg_keys):
                                                        inferred_name = tool_name
                                                        break
                                            
                                            # 如果精确匹配失败，使用启发式规则
                                            if not inferred_name:
                                                if "DirectoryPath" in args or ("path" in args and "pattern" in args):
                                                    inferred_name = "glob"
                                                elif "path" in args and "pattern" not in args:
                                                    inferred_name = "list_directory"
                                                elif "paths" in args:
                                                    inferred_name = "read_many_files"
                                                elif "todos" in args:
                                                    inferred_name = "todo"
                                        except Exception as e:
                                            logger.error(f"Error inferring tool name: {e}")
                                    
                                    # 如果仍然推断失败，记录警告但不设置name
                                    # 让客户端报错，这样更容易发现问题
                                    if inferred_name:
                                        func["name"] = inferred_name
                                        logger.warning(f"Inferred tool name: {inferred_name} for tool_call index {tool_call.get('index')}")
                                    else:
                                        logger.error(f"Failed to infer tool name for tool_call with args: {func.get('arguments', '')[:100]}")
                    
                    if delta.get("content") and delta["content"].strip():
                        has_content = True
                    
                    if delta.get("reasoning_content"):
                        has_reasoning = True
                    
                    # 跳过空的content chunks（关键优化！）
                    # 但不能跳过包含其他重要数据的chunk（tool_calls、reasoning_content、role等）
                    # 修复：之前会跳过包含tool_calls元数据的chunk，导致id和name丢失
                    # 临时禁用以便DEBUG
                    # if (
                    #     "content" in delta 
                    #     and not delta.get("content")
                    #     and not delta.get("tool_calls")  # 有tool_calls不能跳过
                    #     and not delta.get("reasoning_content")  # 有reasoning不能跳过
                    #     and not delta.get("role")  # 有role不能跳过
                    # ):
                    #     should_skip = True
                    #     skipped_count += 1
                
                # 如果不跳过，记录并转发chunk
                if not should_skip:
                    chunk_json = json.dumps(chunk_dict, ensure_ascii=False)
                    try:
                        with open(stream_log_file, 'a', encoding='utf-8') as f:
                            f.write(chunk_json + "\n")
                    except Exception:
                        pass
                    
                    yield f"data: {chunk_json}\n\n"
            
            # 根据qwen code的验证逻辑决定是否需要注入finish_reason
            # 客户端逻辑: if (!hasToolCall && (!hasFinishReason || !hasValidContent))
            # 只有在 没有tool_call 且 没有finish_reason 且 有内容 时才需要注入
            has_valid_content = has_content or has_reasoning
            
            if not has_tool_calls and not has_finish_reason and has_valid_content:
                logger.warning(f"Stream ended without finish_reason (has_content={has_content}, has_reasoning={has_reasoning}), injecting 'stop'")
                stop_chunk = {
                    "id": last_chunk_info["id"],
                    "object": "chat.completion.chunk",
                    "created": last_chunk_info["created"],
                    "model": last_chunk_info["model"],
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                chunk_json = json.dumps(stop_chunk, ensure_ascii=False)
                try:
                    with open(stream_log_file, 'a', encoding='utf-8') as f:
                        f.write(chunk_json + "\n")
                except Exception:
                    pass
                yield f"data: {chunk_json}\n\n"
            
            logger.info(f"Stream completed: {chunk_count} chunks, {skipped_count} skipped, finish={has_finish_reason}, tools={has_tool_calls}, content={has_content}, reasoning={has_reasoning}")

        except Exception as e:
            logger.error(f"Stream Error: {e}", exc_info=True)
            error_chunk = {
                "id": "error",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": f"\n\n[API Error: {str(e)}]"},
                    "finish_reason": "error"
                }]
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
        
        yield "data: [DONE]\n\n"

    return StreamingResponse(response_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    init_config = load_config()
    port = init_config.get("proxyPort") or int(os.environ.get("PORT", DEFAULT_PORT))
    print(f"[Proxy] Server running on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
