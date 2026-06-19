"""
回复模板匹配
当弹幕命中模板关键词时，直接返回预设回复，不调用 AI API。
模板匹配优先级高于缓存和 API 调用。
"""
import re
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class ReplyTemplates:
    """回复模板管理器"""

    def __init__(self, templates: List[Dict]):
        """
        Args:
            templates: 模板列表，每个模板格式：
                {
                    "keywords": ["关键词1", "关键词2"],  # 命中任一关键词即匹配
                    "reply": "回复内容",                  # 固定回复文本
                    "match": "any"                       # 可选，"any"=命中任一(默认) "all"=全部命中
                }
                也支持变量替换，回复中可用 {user} 代替用户名：
                {
                    "keywords": ["你好", "hi"],
                    "reply": "@{user} 你好呀！欢迎来到直播间~"
                }
        """
        self._templates = templates or []

    def match(self, user_name: str, content: str) -> Optional[str]:
        """
        尝试匹配模板

        Args:
            user_name: 用户名
            content: 弹幕内容

        Returns:
            匹配到的回复内容（已替换变量），未匹配返回 None
        """
        content_lower = content.strip().lower()

        for tpl in self._templates:
            keywords = tpl.get("keywords", [])
            if not keywords:
                continue

            match_mode = tpl.get("match", "any")
            reply = tpl.get("reply", "")
            if not reply:
                continue

            keywords_lower = [kw.lower() for kw in keywords]

            matched = False
            if match_mode == "all":
                matched = all(kw in content_lower for kw in keywords_lower)
            else:  # "any"
                matched = any(kw in content_lower for kw in keywords_lower)

            if matched:
                # 替换变量
                result = reply.replace("{user}", user_name)
                logger.debug(f"模板命中: {keywords} -> {result[:30]}...")
                return result

        return None
