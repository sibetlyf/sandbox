"""
Session ID管理模块
用于保存和读取session_id
"""
import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SESSION_STORAGE_FILE = "session_storage.json"


def save_session_id(session_id: str):
    """保存session_id到文件"""
    try:
        data = {}
        if os.path.exists(SESSION_STORAGE_FILE):
            with open(SESSION_STORAGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

        # 保存最新的session_id
        data['latest_session_id'] = session_id

        # 保存到历史记录
        if 'session_history' not in data:
            data['session_history'] = []
        if session_id not in data['session_history']:
            data['session_history'].append(session_id)

        with open(SESSION_STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Session ID已保存: {session_id}")
        return True
    except Exception as e:
        logger.error(f"保存session_id失败: {e}")
        return False


def get_latest_session_id() -> Optional[str]:
    """获取最新的session_id"""
    try:
        if os.path.exists(SESSION_STORAGE_FILE):
            with open(SESSION_STORAGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('latest_session_id')
    except Exception as e:
        logger.error(f"读取session_id失败: {e}")
    return None


def parse_session_id_from_json(json_str: str) -> Optional[str]:
    """从JSON字符串中解析session_id"""
    try:
        data = json.loads(json_str)
        # 尝试从不同的字段获取session_id
        if 'session_id' in data:
            session_id = data['session_id']
            if isinstance(session_id, str) and len(session_id) > 10:
                return session_id
        elif 'sessionId' in data:
            session_id = data['sessionId']
            if isinstance(session_id, str) and len(session_id) > 10:
                return session_id
        elif 'id' in data:
            session_id = data['id']
            if isinstance(session_id, str) and len(session_id) > 10:
                return session_id
        # 尝试从metadata或其他字段获取
        if 'metadata' in data and isinstance(data['metadata'], dict):
            if 'session_id' in data['metadata']:
                return data['metadata']['session_id']
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        pass
    return None


def parse_session_id_from_text(text: str) -> Optional[str]:
    """从文本中尝试提取session_id（可能包含JSON行）"""
    # 尝试按行解析JSON
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # 尝试解析JSON
        session_id = parse_session_id_from_json(line)
        if session_id:
            return session_id
    return None
