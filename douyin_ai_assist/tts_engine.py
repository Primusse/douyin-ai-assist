"""
TTS 语音合成模块
使用 edge-tts (微软 Edge TTS) 将文字转为语音并自动播放

策略：队列中只保留最新一条未播放的消息，新消息覆盖旧消息
"""
import asyncio
import os
import threading
import queue
import logging
from datetime import datetime

import edge_tts

from .config import TTS_VOICE, TTS_RATE, TTS_CACHE_DIR

logger = logging.getLogger(__name__)

# 延迟初始化 pygame（避免模块导入时的副作用）
_mixer_initialized = False
_mixer_lock = threading.Lock()

# TTS 消息队列，maxsize=1，只保留最新一条
_tts_queue: queue.Queue = queue.Queue(maxsize=1)
_worker_started = False
_worker_lock = threading.Lock()

# 用 Event 替代 bool 标志（线程安全）
_busy = threading.Event()
# TTS 就绪信号：set=可以接受新任务，clear=正在播放需等待
_tts_ready = threading.Event()
_tts_ready.set()  # 初始就绪


def _ensure_mixer():
    """延迟初始化 pygame mixer（首次使用时才初始化）"""
    global _mixer_initialized
    if not _mixer_initialized:
        with _mixer_lock:
            if not _mixer_initialized:
                import pygame
                pygame.mixer.init()
                _mixer_initialized = True


def _ensure_cache_dir():
    """确保缓存目录存在"""
    os.makedirs(TTS_CACHE_DIR, exist_ok=True)


async def _text_to_speech(text: str, output_path: str) -> str:
    """异步调用 edge-tts 将文字转为 mp3 音频文件"""
    communicate = edge_tts.Communicate(text, TTS_VOICE, rate=TTS_RATE)
    await communicate.save(output_path)
    return output_path


def _play_audio(file_path: str):
    """播放音频文件，等待播放完成"""
    import pygame
    try:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
    except Exception as e:
        logger.error(f"[TTS] 播放失败: {e}")


def _tts_worker():
    """后台工作线程，从队列取消息并播放（只播最新一条）"""
    while True:
        text = _tts_queue.get()
        _busy.set()
        _tts_ready.clear()  # 标记为忙碌，外部需等待
        try:
            _ensure_mixer()
            _ensure_cache_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_path = os.path.join(TTS_CACHE_DIR, f"reply_{timestamp}.mp3")

            asyncio.run(_text_to_speech(text, output_path))
            _play_audio(output_path)
        except Exception as e:
            logger.error(f"[TTS] 语音合成失败: {e}")
        finally:
            _busy.clear()
            _tts_ready.set()  # 播放完成，通知等待方
            _tts_queue.task_done()


def _ensure_worker():
    """确保后台工作线程已启动（只启动一次）"""
    global _worker_started
    if not _worker_started:
        with _worker_lock:
            if not _worker_started:
                t = threading.Thread(target=_tts_worker, daemon=True)
                t.start()
                _worker_started = True


def is_busy() -> bool:
    """TTS 是否正在生成或播放音频"""
    return _busy.is_set()


def is_queue_full() -> bool:
    """TTS 队列是否已满"""
    return _tts_queue.full()


def wait_until_ready():
    """阻塞等待 TTS 播放完成，可以接受新任务时返回"""
    _tts_ready.wait()


def speak(text: str):
    """
    将文字加入 TTS 队列（不阻塞调用线程）
    策略：队列满时丢弃旧消息，只保留最新一条
    """
    _ensure_worker()

    # 队列满时丢弃旧消息，只保留最新
    while not _tts_queue.empty():
        try:
            _tts_queue.get_nowait()
            _tts_queue.task_done()
        except queue.Empty:
            break

    try:
        _tts_queue.put_nowait(text)
    except queue.Full:
        pass
