"""
弹幕过滤模块
根据配置规则过滤无意义、不相关的弹幕内容
"""
import logging

from .config import (
    IGNORED_USERS,
    IGNORED_KEYWORDS,
    MIN_MESSAGE_LENGTH,
    FILTER_MODE,
    PRODUCT_KEYWORDS,
)

logger = logging.getLogger(__name__)


def should_reply(user_name: str, content: str) -> bool:
    """
    判断是否应该回复该弹幕

    过滤规则：
    1. 消息长度过短
    2. 纯数字内容
    3. 忽略列表中的用户
    4. 包含忽略关键词
    5. 电商模式下未命中产品关键词

    Args:
        user_name: 发送者昵称
        content: 弹幕内容

    Returns:
        True 表示应该回复，False 表示跳过
    """
    content = content.strip()

    # 长度过滤
    if len(content) < MIN_MESSAGE_LENGTH:
        return False

    # 纯数字过滤
    if content.isdigit():
        return False

    # 忽略用户
    if user_name in IGNORED_USERS:
        return False

    # 忽略关键词
    for keyword in IGNORED_KEYWORDS:
        if keyword in content:
            return False

    # 电商模式：仅回复产品相关问题
    if FILTER_MODE == "ecommerce":
        if not any(kw in content for kw in PRODUCT_KEYWORDS):
            return False

    return True
