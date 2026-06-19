"""
Protobuf 消息解析与分发
负责将抖音 WebSocket 推送的 Protobuf 二进制数据解析为结构化消息，
并根据消息类型分发给对应的处理函数。
"""
import gzip
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from .douyin.douyin_pb2 import (
    PushFrame, Message, Response, ChatMessage, GiftMessage,
    LikeMessage, MemberMessage, SocialMessage, RoomUserSeqMessage,
    FansclubMessage, EmojiChatMessage, RoomMessage, RoomStatsMessage,
    RoomRankMessage, ControlMessage, RoomStreamAdaptationMessage,
)
from . import danmaku_filter
from . import ai_replier
from .config import REPLY_FILE, TTS_ENABLED

logger = logging.getLogger(__name__)


class MessageParser:
    """
    Protobuf 消息解析器

    负责：
    - 解析 Protobuf 消息
    - 分发给对应类型的 handler
    - 在后台线程中生成 AI 回复
    """

    def __init__(self, on_stream_end=None):
        """
        Args:
            on_stream_end: 直播结束时的回调函数
        """
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='ai_reply')
        self._on_stream_end = on_stream_end

        # 消息类型 -> 处理函数的映射表
        self._handlers = {
            'WebcastChatMessage': self._handle_chat,
            'WebcastGiftMessage': self._handle_gift,
            'WebcastLikeMessage': self._handle_like,
            'WebcastMemberMessage': self._handle_member,
            'WebcastSocialMessage': self._handle_social,
            'WebcastRoomUserSeqMessage': self._handle_room_user_seq,
            'WebcastFansclubMessage': self._handle_fansclub,
            'WebcastControlMessage': self._handle_control,
            'WebcastEmojiChatMessage': self._handle_emoji_chat,
            'WebcastRoomStatsMessage': self._handle_room_stats,
            'WebcastRoomMessage': self._handle_room,
            'WebcastRoomRankMessage': self._handle_rank,
            'WebcastRoomStreamAdaptationMessage': self._handle_room_stream_adaptation,
        }

    def parse(self, raw_message: bytes, send_ack=None):
        """
        解析一条 WebSocket 二进制消息

        Args:
            raw_message: 原始二进制数据
            send_ack: 发送 ACK 的回调函数（ws.send）
        """
        # 解析 PushFrame
        frame = PushFrame()
        frame.ParseFromString(raw_message)

        # 解压 payload
        payload_bytes = gzip.decompress(frame.payload)
        response = Response()
        response.ParseFromString(payload_bytes)

        # 发送 ACK
        if response.need_ack and send_ack:
            ack = PushFrame(
                LogID=frame.LogID,
                payload=response.internal_ext.encode('utf-8'),
                payload_type='ack'
            ).SerializeToString()
            send_ack(ack)

        # 分发消息
        for msg in response.messages:
            handler = self._handlers.get(msg.method)
            if handler:
                handler(msg.payload)

    def _handle_chat(self, payload):
        """处理文字聊天弹幕"""
        message = ChatMessage()
        message.ParseFromString(payload)

        user_name = message.user.nickname
        content = message.content

        # 过滤
        if not danmaku_filter.should_reply(user_name, content):
            return

        # TTS 忙碌时直接丢弃，防止堆积
        if TTS_ENABLED:
            from .tts_engine import is_busy
            if is_busy():
                return

        # 后台线程执行 AI 回复
        self._executor.submit(self._generate_and_output, user_name, content)

    def _generate_and_output(self, user_name: str, content: str):
        """后台线程：生成回复 + 写日志 + TTS"""

        # TTS 启用时，等待上一条播放完成再调用 AI（避免浪费 API）
        if TTS_ENABLED:
            from .tts_engine import wait_until_ready
            wait_until_ready()

        result = ai_replier.generate_reply(user_name, content)

        if not result['success']:
            logger.warning(f"AI 回复失败: {result['error']}")
            return

        reply_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_name': result['user_name'],
            'user_message': result['user_message'],
            'ai_reply': result['reply']
        }

        # 写入回复日志
        try:
            with open(REPLY_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(reply_data, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.warning(f"写入回复日志失败: {e}")

        # 控制台输出
        if result.get('from_template'):
            cache_status = "[模板]"
        elif result.get('from_cache'):
            cache_status = "[缓存]"
        else:
            cache_status = "[API]"
        print(f"\n{'='*60}")
        print(f"[{reply_data['timestamp']}] {cache_status} {user_name}: {content}")
        print(f"-"*60)
        print(f"DeepSeek AI回复: {result['reply']}")
        print(f"{'='*60}")

        # TTS 语音播报
        if TTS_ENABLED:
            from .tts_engine import speak
            speak(result['reply'])

    def _handle_control(self, payload):
        """处理控制消息（直播结束等）"""
        message = ControlMessage()
        message.ParseFromString(payload)

        if message.action == 3:
            logger.info("[系统] 直播间已结束")
            if self._on_stream_end:
                self._on_stream_end()

    # 以下 handler 当前不做处理，保留扩展点

    def _handle_gift(self, payload):
        """礼物消息"""
        pass

    def _handle_like(self, payload):
        """点赞消息"""
        pass

    def _handle_member(self, payload):
        """进入直播间消息"""
        pass

    def _handle_social(self, payload):
        """关注消息"""
        pass

    def _handle_room_user_seq(self, payload):
        """直播间用户排序"""
        pass

    def _handle_fansclub(self, payload):
        """粉丝团消息"""
        pass

    def _handle_emoji_chat(self, payload):
        """表情聊天消息"""
        pass

    def _handle_room_stats(self, payload):
        """直播间统计"""
        pass

    def _handle_room(self, payload):
        """房间基本信息"""
        pass

    def _handle_rank(self, payload):
        """排行榜信息"""
        pass

    def _handle_room_stream_adaptation(self, payload):
        """直播间流配置"""
        pass
