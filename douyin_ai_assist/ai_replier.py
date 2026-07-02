"""
AI 回复生成器
通过通用 AI 客户端接口生成弹幕回复，支持缓存、模板匹配和多轮对话历史

优先级：回复模板 > LRU 缓存（可关闭） > AI API 调用
"""
import collections
import logging
import threading
from datetime import datetime
from typing import Dict, Optional

from .config import (
    AI_API_FORMAT,
    AI_API_KEY,
    AI_API_URL,
    AI_MODEL,
    AI_TEMPERATURE,
    AI_MAX_TOKENS,
    HOST_NAME,
    HOST_INTRO,
    HOST_PERSONA,
    REPLY_STYLE,
    REPLY_TEMPLATES,
    REPLY_CACHE_ENABLED,
    CONVERSATION_HISTORY_SIZE,
    REPLY_MAX_LENGTH,
)
from .ai_client import create_client
from .reply_templates import ReplyTemplates
from . import reply_cache

logger = logging.getLogger(__name__)

# 回复风格描述映射
_STYLE_MAP = {
    "professional": "专业严谨，用词准确利落，像一个专家在解答",
    "friendly": "亲切友好，像朋友聊天一样自然温暖",
    "humorous": "幽默风趣，偶尔调侃但不过分，像游戏主播一样的互动感",
}

# ==================== 系统提示词 ====================

_SYSTEM_PROMPT = f"""你是{HOST_NAME}本人，正在抖音直播中和观众实时互动。

【你的身份】
{HOST_INTRO}

【你的性格】
{HOST_PERSONA}

【说话风格】
{_STYLE_MAP.get(REPLY_STYLE, "亲切友好")}

【核心规则 — 必须遵守】
1. 你就是{HOST_NAME}本人，用第一人称"我"，绝不能让观众察觉是 AI
2. 每条回复 {REPLY_MAX_LENGTH} 字以内，简洁有力，像直播聊天不是写文章
3. 语气词可以自然带出：哈哈、嗯、emmm、哎呀、卧槽（适度）、兄弟、老铁
4. 称呼要多样：朋友、兄弟、老铁、这位水友、@用户名，别每条都用一个词
5. 开头要有变化：有时直接回答，有时先叫名字，有时带个语气词，别总是"朋友你好"
6. 保持你的专业人设，遇到不懂的大方说"这个我也不太清楚"，别硬编
7. 偶尔可以反问观众增加互动，比如"你们觉得呢？""有人试过吗？"
8. 绝不能说"AI"、"机器人"、"助手"、"模型"等词
9. 不要用任何 emoji 表情符号
10. 回复要像真人直播随口说的，不要书面语，不要客套话

【直播间的感觉】
- 弹幕刷得快，回复要短平快，不要长篇大论
- 观众在直播间，你们在实时聊天，不是邮件往来
- 可以 cue 其他观众："刚才那位老铁问的xxx..."
- 连续有人问同类问题，可以带一句"好多人问这个，统一说下..."

请直接给出回复内容，不加解释、不加引号。"""

# ==================== 多轮对话历史 ====================

# 对话历史缓冲区: deque of {"user_name": str, "user_message": str, "ai_reply": str}
_history: collections.deque = collections.deque(maxlen=CONVERSATION_HISTORY_SIZE)
_history_lock = threading.Lock()


def _format_history_context() -> str:
    """将近期对话历史格式化为上下文文本，注入到 prompt 中"""
    with _history_lock:
        if not _history or CONVERSATION_HISTORY_SIZE == 0:
            return ""
        lines = ["【刚才的对话 — 你可以参考上下文让回复更连贯】"]
        for h in _history:
            lines.append(
                f'观众"{h["user_name"]}"问："{h["user_message"]}" → 我回："{h["ai_reply"]}"'
            )
        return "\n".join(lines)


def _add_to_history(user_name: str, user_message: str, ai_reply: str):
    """添加一轮对话到历史缓冲区"""
    if CONVERSATION_HISTORY_SIZE == 0:
        return
    with _history_lock:
        _history.append({
            "user_name": user_name,
            "user_message": user_message,
            "ai_reply": ai_reply,
        })


# ==================== AI 客户端 ====================

_client = None
_templates = ReplyTemplates(REPLY_TEMPLATES)


def _get_client():
    """获取 AI 客户端单例"""
    global _client
    if _client is None:
        _client = create_client(
            api_format=AI_API_FORMAT,
            api_key=AI_API_KEY,
            api_url=AI_API_URL,
            model=AI_MODEL,
            temperature=AI_TEMPERATURE,
            max_tokens=AI_MAX_TOKENS,
        )
        logger.info(f"AI 客户端已初始化: {AI_API_FORMAT} / {AI_MODEL}")
    return _client


# ==================== 回复生成主逻辑 ====================


def generate_reply(user_name: str, user_message: str) -> Dict:
    """
    生成回复

    优先级：回复模板 > LRU 缓存（可关闭） > AI API 调用

    Args:
        user_name: 用户名
        user_message: 用户消息内容

    Returns:
        {
            'user_name': str,
            'user_message': str,
            'reply': str,
            'success': bool,
            'from_cache': bool,
            'from_template': bool,
            'from_history': bool,
            'error': str (如果失败)
        }
    """
    # 1. 优先匹配回复模板
    template_reply = _templates.match(user_name, user_message)
    if template_reply:
        return {
            'user_name': user_name,
            'user_message': user_message,
            'reply': template_reply,
            'success': True,
            'from_cache': False,
            'from_template': True,
            'from_history': False,
            'error': None
        }

    # 2. 检查 LRU 缓存（可配置开关）
    if REPLY_CACHE_ENABLED:
        cached_reply = reply_cache.get_cached_reply(user_message)
        if cached_reply:
            return {
                'user_name': user_name,
                'user_message': user_message,
                'reply': cached_reply,
                'success': True,
                'from_cache': True,
                'from_template': False,
                'from_history': False,
                'error': None
            }

    # 3. 缓存未命中，调用 AI API（带对话历史上下文）
    try:
        client = _get_client()

        # 构建用户提示词（含对话历史）
        history_ctx = _format_history_context()
        has_history = bool(history_ctx)

        if has_history:
            user_prompt = (
                f"{history_ctx}\n\n"
                f"【当前弹幕】\n"
                f"观众\"{user_name}\"发了一条弹幕：\"{user_message}\"\n\n"
                f"参考刚才的对话，用{HOST_NAME}的口吻回复这条弹幕："
            )
        else:
            user_prompt = (
                f"观众\"{user_name}\"发了一条弹幕：\"{user_message}\"\n\n"
                f"用{HOST_NAME}的口吻回复这条弹幕："
            )

        reply = client.chat(_SYSTEM_PROMPT, user_prompt)

        # 写入对话历史
        _add_to_history(user_name, user_message, reply)

        # 写入缓存（如果启用）
        if REPLY_CACHE_ENABLED:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            reply_cache.cache_reply(user_message, reply, timestamp)

        return {
            'user_name': user_name,
            'user_message': user_message,
            'reply': reply,
            'success': True,
            'from_cache': False,
            'from_template': False,
            'from_history': has_history,
            'error': None
        }

    except Exception as e:
        logger.error(f"AI 回复生成失败: {e}")
        return {
            'user_name': user_name,
            'user_message': user_message,
            'reply': None,
            'success': False,
            'from_cache': False,
            'from_template': False,
            'from_history': False,
            'error': str(e)
        }
