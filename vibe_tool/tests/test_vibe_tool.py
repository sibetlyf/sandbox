import pytest
import os
import sys
import json
import shutil
import subprocess
from unittest.mock import patch

# Ensure the src/backend directory is in sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from vibe_tool.vibe_toolkit import VibeCodingToolkit
from vibe_tool.parser import StreamParser, MessageExtractor
from vibe_tool.datamodel import ParseData, ToolCall, TodoItem

@pytest.fixture(scope="session", autouse=True)
def ensure_environment():
    """Ensure ccr and claude are installed; if not, configure them based on 1.sh logic."""
    has_claude = shutil.which("claude") is not None
    has_ccr = shutil.which("ccr") is not None or shutil.which("claude-code-router") is not None

    if not (has_claude and has_ccr):
        print("环境不存在，尝试自动配置...")
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "1.sh")
        
        if os.path.exists(script_path) and shutil.which("bash"):
            try:
                subprocess.run(["bash", script_path], check=True)
                print("1.sh 脚本执行完毕。")
            except subprocess.CalledProcessError as e:
                print(f"尝试执行 1.sh 失败: {e}")
        else:
            # Fallback for Windows without bash
            import pathlib
            home = str(pathlib.Path.home())
            npm_global = os.path.join(home, ".npm-global")
            os.makedirs(npm_global, exist_ok=True)
            
            try:
                subprocess.run(f"npm config set prefix \"{npm_global}\"", shell=True, check=True)
                os.environ["PATH"] = os.path.join(npm_global, "bin") + os.pathsep + os.environ.get("PATH", "")
                subprocess.run("npm install -g @anthropic-ai/claude-code", shell=True, check=True)
                subprocess.run("npm install -g @musistudio/claude-code-router", shell=True, check=True)
                print("通过 npm 成功安装了环境。")
            except Exception as e:
                print(f"直接配置环境失败: {e}")


@pytest.mark.parametrize("agent_type, session_id, use_resume, expected_substring", [
    ("ccr", "test-session", True, "ccr code -p -r test-session"),
    ("ccr", None, False, "ccr code -p"),
    ("opencode", "test-session", True, "opencode --session test-session"),
    ("opencode", None, False, "opencode --format json"),
])
def test_build_cmd_posix(agent_type, session_id, use_resume, expected_substring):
    with patch("platform.system", return_value="Linux"):
        with patch("vibe_tool.vibe_toolkit.IS_WINDOWS", False):
            toolkit = VibeCodingToolkit(agent_type=agent_type, workspace_path="/tmp")
            cmd = toolkit._build_cmd("hello", session_id=session_id, use_resume=use_resume)
            
            assert cmd[0] == "/bin/bash"
            assert cmd[1] == "-c"
            assert expected_substring in cmd[2]

def test_build_cmd_windows():
    with patch("platform.system", return_value="Windows"):
        with patch("vibe_tool.vibe_toolkit.IS_WINDOWS", True):
            # We need to mock NamedTemporaryFile since it interacts with the FS
            with patch("tempfile.NamedTemporaryFile") as mock_tmp:
                mock_tmp.return_value.name = "C:\\temp\\prompt.txt"
                
                toolkit = VibeCodingToolkit(agent_type="ccr", workspace_path="C:\\project")
                cmd = toolkit._build_cmd("hello world", session_id="sid", use_resume=True)
                
                assert cmd[0] == "powershell.exe"
                assert "$p = Get-Content -Path \"C:\\temp\\prompt.txt\" -Raw" in cmd[3]
                assert "ccr code -p -r sid" in cmd[3]

@pytest.mark.asyncio
async def test_stream_parser_success():
    parser = StreamParser()
    valid_json = json.dumps({
        "type": "content",
        "message": {
            "content": [{"type": "text", "text": "Hello, world!"}]
        },
        "uuid": "test-uuid"
    })
    
    results = []
    async for data in parser.parse_line_async(valid_json):
        if data:
            results.append(data)
    
    assert len(results) == 1
    assert results[0].type == "content"
    assert results[0].uuid == "test-uuid"
    
    # Test cache
    async for data in parser.parse_line_async(valid_json):
        if data:
            results.append(data)
    assert len(results) == 2
    
    parser.shutdown()

@pytest.mark.asyncio
async def test_stream_parser_invalid_json():
    parser = StreamParser()
    invalid_json = "{ invalid json }"
    
    results = []
    async for data in parser.parse_line_async(invalid_json):
        if data:
            results.append(data)
    
    assert len(results) == 0
    parser.shutdown()

@pytest.mark.asyncio
async def test_message_extractor():
    data_dict = {
        "type": "content",
        "message": {
            "content": [
                {"type": "thinking", "thinking": "Let me think..."},
                {"type": "text", "text": "Execution result: "},
                {"type": "text", "text": "Success!"},
                {"type": "tool_use", "name": "write", "id": "t1", "input": {"file_path": "a.txt", "content": "hello"}}
            ]
        }
    }
    parse_data = ParseData.from_dict(data_dict)
    
    text = await MessageExtractor.extract_text_content(parse_data)
    assert text == "Execution result: Success!"
    
    thinking = await MessageExtractor.extract_thinking_content(parse_data)
    assert thinking == "Let me think..."
    
    has_tools = await MessageExtractor.has_tool_calls(parse_data)
    assert has_tools is True
    assert len(parse_data.tool_calls) == 1
    assert parse_data.tool_calls[0].name == "write"

@pytest.mark.asyncio
async def test_todo_extraction():
    data_dict = {
        "type": "content",
        "message": {
            "content": [
                {
                    "type": "tool_use", 
                    "name": "todowrite", 
                    "id": "t2", 
                    "input": {
                        "todos": [
                            {"content": "First task", "status": "done"},
                            {"content": "Second task", "status": "pending"}
                        ]
                    }
                }
            ]
        }
    }
    parse_data = ParseData.from_dict(data_dict)
    assert parse_data.todo_list is not None
    assert len(parse_data.todo_list) == 2
    assert parse_data.todo_list[0].content == "First task"
    assert parse_data.todo_list[0].status == "done"
