"""
AI 回复生成器
通过通用 AI 客户端接口生成弹幕回复，支持缓存和模板匹配

优先级：回复模板 > LRU 缓存 > AI API 调用
"""
import logging
from datetime import datetime
from typing import Dict

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
)
from .ai_client import create_client
from .reply_templates import ReplyTemplates
from . import reply_cache

logger = logging.getLogger(__name__)

# 回复风格描述映射
_STYLE_MAP = {
    "professional": "专业严谨",
    "friendly": "亲切友好",
    "humorous": "幽默风趣",
}

# 系统提示词（模块加载时构建一次）
_SYSTEM_PROMPT = f"""你是{HOST_NAME}的直播助手，正在帮助回复抖音直播间的观众弹幕。

【主播简介】
{HOST_INTRO}

【主播人设】
{HOST_PERSONA}

【回复风格】
{_STYLE_MAP.get(REPLY_STYLE, "亲切友好")}

【回复要求】
1. 用第一人称"我"来回复，让观众感觉是在和主播直接交流
2. 称呼观众为"朋友"、"家长"或直接用"@用户名"
3. 回复要有温度，体现主播的专业性和亲和力
4. 如果是书籍相关问题，可以自然推荐相关书籍
5. 如果是育儿问题，给出具体可行的建议
6. 回复控制在30字以内，简洁有力
7. 不要出现"AI"、"机器人"等字眼
8. 回复要自然，像真人说话一样
9. 不要出现任何表情emoji

请直接给出回复内容，不要加任何解释。"""

# 懒加载的 AI 客户端实例
_client = None
# 模板匹配器
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


def generate_reply(user_name: str, user_message: str) -> Dict:
    """
    生成回复

    优先级：回复模板 > LRU 缓存 > AI API 调用

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
            'error': None
        }

    # 2. 检查 LRU 缓存
    cached_reply = reply_cache.get_cached_reply(user_message)
    if cached_reply:
        return {
            'user_name': user_name,
            'user_message': user_message,
            'reply': cached_reply,
            'success': True,
            'from_cache': True,
            'from_template': False,
            'error': None
        }

    # 3. 缓存未命中，调用 AI API
    try:
        client = _get_client()
        user_prompt = f'观众"{user_name}"发了一条弹幕："{user_message}"\n\n请帮我回复这条弹幕：'
        reply = client.chat(_SYSTEM_PROMPT, user_prompt)

        # 缓存新回复
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        reply_cache.cache_reply(user_message, reply, timestamp)

        return {
            'user_name': user_name,
            'user_message': user_message,
            'reply': reply,
            'success': True,
            'from_cache': False,
            'from_template': False,
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
            'error': str(e)
        }
