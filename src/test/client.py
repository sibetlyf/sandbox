import asyncio
import websockets
import json

SERVER_URL = "ws://127.0.0.1:8084/ws"

async def test_chat():
    print(f"📡 正在连接到服务器: {SERVER_URL} ...")
    try:
        async with websockets.connect(SERVER_URL) as websocket:
            print("✅ 连接成功！")

            # 1. 构造问题请求
            question = "你好，请简单介绍一下你自己。"
            message = {
                "type": "execute",
                "prompt": question,
                "session_id": "test_session_001"
            }

            print(f"📤 发送问题: {question}")
            await websocket.send(json.dumps(message))

            # 2. 接收响应流
            print("📥 等待回复...")
            print("-" * 50)
            
            full_response = ""
            
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                msg_type = data.get("type")

                # 处理不同类型的消息
                if msg_type == "task_start":
                    print(f"[系统] 任务已开始 (Task ID: {data.get('task_id')})")
                
                elif msg_type == "chunk":
                    # 获取新增文本并实时打印
                    new_text = data.get("new_text", "")
                    if new_text:
                        print(new_text, end="", flush=True)
                        full_response += new_text
                
                elif msg_type == "task_complete":
                    print("\n" + "-" * 50)
                    print("✅ 任务完成！")
                    break
                
                elif msg_type == "error":
                    print(f"\n❌ 发生错误: {data.get('message')}")
                    break

    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        print("请确保后端服务已运行 (./run.sh)")

if __name__ == "__main__":
    asyncio.run(test_chat())
