#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
from agno.agent import Agent
from agno.models.litellm import LiteLLM

# 添加上级目录到 module path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vibe_tool.vibe_toolkit import VibeCodingToolkit

async def main():
    # 测试主函数
    model = LiteLLM(
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="sk-d9e5f3b88a174d9dad0ae94fb571f4ec",
        id="openai/qwen3.5-plus",
    )
    toolkit = VibeCodingToolkit(agent_type="ccr")
    agent = Agent(model=model, tools=[toolkit], debug_mode=True)
    # await agent.aprint_response("你好")
    while True:
        query = str(input())
        if query == "exit":
            break
        else:
            resp = agent.arun(query, stream=True)
            async for chunk in resp:
                if hasattr(chunk, 'content') and chunk.content:
                    print(chunk.content, flush=True)
                else:
                    print(chunk, flush=True)
            print()

if __name__ == "__main__":
    asyncio.run(main())