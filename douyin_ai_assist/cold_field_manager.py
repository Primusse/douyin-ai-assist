"""
冷场管理器
后台线程定时检查弹幕间隔，空闲时自动播报预设话术防止冷场。

触发条件（同时满足）：
1. 距上次弹幕时间 > COLD_FIELD_INTERVAL 秒
2. TTS 空闲（不在播报或回答问题）
"""
import random
import threading
import time
import logging

from .config import COLD_FIELD_ENABLED, COLD_FIELD_INTERVAL, COLD_FIELD_PHRASES

logger = logging.getLogger(__name__)


class ColdFieldManager:
    """防止冷场管理器"""

    def __init__(self):
        self._last_danmaku_time = time.time()
        self._stop_event = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        """是否启用（由配置控制，且必须有话术）"""
        return COLD_FIELD_ENABLED and len(COLD_FIELD_PHRASES) > 0

    def notify_danmaku(self):
        """收到弹幕时调用，更新时间戳"""
        with self._lock:
            self._last_danmaku_time = time.time()

    def start(self):
        """启动后台定时检查线程"""
        if not self.enabled:
            logger.info("[冷场管理] 未启用或话术列表为空，跳过")
            return
        if self._thread is not None:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="cold_field")
        self._thread.start()
        logger.info(f"[冷场管理] 已启动，间隔={COLD_FIELD_INTERVAL}秒，话术数={len(COLD_FIELD_PHRASES)}")

    def stop(self):
        """停止后台线程"""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        logger.info("[冷场管理] 已停止")

    def _run(self):
        """后台线程主循环"""
        while not self._stop_event.is_set():
            self._stop_event.wait(COLD_FIELD_INTERVAL)

            if self._stop_event.is_set():
                break

            try:
                self._check_and_speak()
            except Exception as e:
                logger.warning(f"[冷场管理] 检查异常: {e}")

    def _check_and_speak(self):
        """检查条件并播报冷场话术"""
        # 条件1: 距上次弹幕时间超过间隔
        with self._lock:
            elapsed = time.time() - self._last_danmaku_time
        if elapsed < COLD_FIELD_INTERVAL:
            return

        # 条件2: TTS 空闲（不在回答问题/播报）
        from .tts_engine import is_busy
        if is_busy():
            return

        # 随机选择一条话术播报
        phrase = random.choice(COLD_FIELD_PHRASES)
        logger.info(f"[冷场管理] 播报: {phrase}")

        from .tts_engine import speak
        speak(phrase)
