"""
回复缓存管理器
- 缓存最近 100 条已回复的内容
- 相同或相似的消息直接复用缓存回复，节省 API 费用
"""
import json
import os
import hashlib
import logging
from collections import OrderedDict
from typing import Optional, Dict

from .config import REPLY_FILE, REPLY_CACHE_ENABLED

logger = logging.getLogger(__name__)


class ReplyCache:
    """LRU 回复缓存，基于 OrderedDict 实现"""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache = OrderedDict()
        # 缓存文件路径（与回复记录同目录）
        self._cache_file = os.path.join(
            os.path.dirname(REPLY_FILE),
            "ai_replies_cache.json"
        )
        self._load_from_file()

    def _generate_key(self, user_message: str) -> str:
        """生成消息的唯一 key（MD5 哈希）"""
        cleaned = user_message.strip().lower().replace(" ", "").replace("　", "")
        return hashlib.md5(cleaned.encode('utf-8')).hexdigest()

    def get(self, user_message: str) -> Optional[Dict]:
        """从缓存获取回复，命中时自动更新 LRU 顺序"""
        key = self._generate_key(user_message)

        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]

        return None

    def set(self, user_message: str, reply_data: Dict):
        """设置缓存，超出容量时淘汰最旧条目"""
        key = self._generate_key(user_message)

        if key in self.cache:
            del self.cache[key]

        self.cache[key] = {
            'user_message': user_message,
            'ai_reply': reply_data.get('reply'),
            'timestamp': reply_data.get('timestamp'),
            'use_count': 1
        }

        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

        self._save_to_file()

    def increment_use(self, user_message: str):
        """增加缓存使用次数"""
        key = self._generate_key(user_message)
        if key in self.cache:
            self.cache[key]['use_count'] = self.cache[key].get('use_count', 1) + 1
            self.cache.move_to_end(key)
            self._save_to_file()

    def _load_from_file(self):
        """从文件加载缓存"""
        if os.path.exists(self._cache_file):
            try:
                with open(self._cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        self.cache[key] = value
            except Exception as e:
                logger.warning(f"加载缓存失败: {e}")

    def _save_to_file(self):
        """保存缓存到文件"""
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(dict(self.cache), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")

    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        return {
            'total_cached': len(self.cache),
            'max_size': self.max_size,
            'total_uses': sum(item.get('use_count', 1) for item in self.cache.values())
        }

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        if os.path.exists(self._cache_file):
            os.remove(self._cache_file)


# ========== 模块级单例与便捷函数 ==========

_reply_cache: Optional[ReplyCache] = None


def get_cache() -> ReplyCache:
    """获取全局缓存实例（懒加载单例）"""
    global _reply_cache
    if _reply_cache is None:
        _reply_cache = ReplyCache(max_size=100)
    return _reply_cache


def get_cached_reply(user_message: str) -> Optional[str]:
    """获取缓存的回复内容，未命中返回 None（受 REPLY_CACHE_ENABLED 控制）"""
    if not REPLY_CACHE_ENABLED:
        return None

    cache = get_cache()
    cached = cache.get(user_message)

    if cached:
        cache.increment_use(user_message)
        return cached['ai_reply']

    return None


def cache_reply(user_message: str, reply: str, timestamp: str = None):
    """缓存一条回复（受 REPLY_CACHE_ENABLED 控制）"""
    if not REPLY_CACHE_ENABLED:
        return

    if timestamp is None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cache = get_cache()
    cache.set(user_message, {
        'reply': reply,
        'timestamp': timestamp
    })


# 延迟导入 datetime（仅在 cache_reply 未传 timestamp 时使用）
from datetime import datetime  # noqa: E402
