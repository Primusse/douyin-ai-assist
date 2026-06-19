"""
抖音直播 WebSocket 客户端
负责与抖音直播服务器建立 WebSocket 连接、维持心跳、接收消息。
"""
import logging
import re
import ssl
import threading

import requests
import websocket

from .config import ROOM_ID
from .sign import get_sign
from .message_parser import MessageParser
from .douyin.douyin_pb2 import PushFrame

logger = logging.getLogger(__name__)

# WebSocket 回调中的 OPCODE_BINARY
OPCODE_BINARY = websocket.ABNF.OPCODE_BINARY


class DouYinLive:
    """抖音直播 WebSocket 客户端"""

    def __init__(self, room_uid: str = ROOM_ID):
        self.room_uid = room_uid
        self.headers = {
            "user-agent": (
                "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
            )
        }
        self.cookies = {
            "__ac_nonce": "0683ab03200786e902e82"
        }
        self.url = f"https://live.douyin.com/{room_uid}"

        self._ws = None
        self._heartbeat_stop = threading.Event()
        self._parser = MessageParser(on_stream_end=self._stop)

    def start(self):
        """启动连接：获取房间信息 → 生成签名 → 建立 WebSocket"""
        room_id, ttwid = self._get_room_id()
        logger.info(f"房间ID: {room_id}")

        sign = get_sign(room_id)
        logger.info(f"签名: {sign[:20]}...")

        self._connect_websocket(room_id, sign, ttwid)

    def _stop(self):
        """停止连接"""
        self._heartbeat_stop.set()
        if self._ws:
            self._ws.close()

    def _get_room_id(self):
        """
        获取直播间内部 room_id 和 ttwid cookie

        Returns:
            (room_id, ttwid)
        """
        response = requests.get(
            self.url, headers=self.headers, cookies=self.cookies
        )

        match = re.search(r'\\"roomId\\":\\"(\d+)\\"', response.text)
        if not match:
            raise RuntimeError(
                f"无法获取直播间ID，请确认直播间地址正确且正在直播: {self.url}"
            )

        room_id = match.group(1)
        ttwid = response.cookies.get('ttwid')

        if not ttwid:
            raise RuntimeError("无法获取 ttwid cookie，请检查网络连接")

        return room_id, ttwid

    def _connect_websocket(self, room_id: str, sign: str, ttwid: str):
        """建立 WebSocket 连接"""
        cookie = f"ttwid={ttwid}"

        ws_url = (
            f"wss://webcast100-ws-web-lq.douyin.com/webcast/im/push/v2/"
            f"?app_name=douyin_web&version_code=180800"
            f"&webcast_sdk_version=1.0.14-beta.0"
            f"&update_version_code=1.0.14-beta.0"
            f"&compress=gzip&device_platform=web&cookie_enabled=true"
            f"&screen_width=1920&screen_height=1080"
            f"&browser_language=zh-CN&browser_platform=Win32"
            f"&browser_name=Mozilla"
            f"&browser_version=5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)"
            f"%20AppleWebKit/537.36%20(KHTML,%20like%20Gecko)"
            f"%20Chrome/137.0.0.0%20Safari/537.36"
            f"&browser_online=true&tz_name=Asia/Shanghai"
            f"&cursor=u-1_fh-7511183563078362663_t-1748833761054"
            f"_r-7511183809635723460_d-7511183805340712963"
            f"&internal_ext=internal_src:dim"
            f"|wss_push_room_id:7511169016510040832"
            f"|wss_push_did:7506916920386848296"
            f"|first_req_ms:1748833760959"
            f"|fetch_time:1748833761054|seq:1"
            f"|wss_info:0-1748833761054-0-0"
            f"|wrds_v:7511183805340715817"
            f"&host=https://live.douyin.com&aid=6383&live_id=1"
            f"&did_rule=3&endpoint=live_pc&support_wrds=1"
            f"&user_unique_id=7506916920386848296"
            f"&im_path=/webcast/im/fetch/&identity=audience"
            f"&need_persist_msg_count=15&insert_task_id=&live_reason="
            f"&room_id={room_id}&heartbeatDuration=0"
            f"&signature={sign}"
        )

        self._ws = websocket.WebSocketApp(
            ws_url,
            header=self.headers,
            cookie=cookie,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        self._ws.run_forever(sslopt={'cert_reqs': ssl.CERT_NONE})

    def _on_open(self, ws):
        """连接建立成功"""
        logger.info("[系统] 连接成功，开始接收弹幕...")
        self._heartbeat_stop.clear()
        threading.Thread(target=self._heartbeat, daemon=True).start()

    def _on_message(self, ws, message):
        """接收到消息"""
        self._parser.parse(
            raw_message=message,
            send_ack=lambda data: ws.send(data, OPCODE_BINARY)
        )

    def _on_error(self, ws, error):
        """WebSocket 错误"""
        logger.error(f"[系统] WebSocket 错误: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket 关闭"""
        self._heartbeat_stop.set()
        logger.info("[系统] 连接已关闭")

    def _heartbeat(self):
        """
        心跳保活
        每 10 秒发送一次应用层心跳包（抖音不响应协议层 ping）
        """
        while not self._heartbeat_stop.is_set():
            try:
                heartbeat = PushFrame(payload_type='hb').SerializeToString()
                self._ws.send(heartbeat, OPCODE_BINARY)
            except Exception:
                break
            self._heartbeat_stop.wait(10)
