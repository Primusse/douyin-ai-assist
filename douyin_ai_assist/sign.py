"""
抖音 X-Bogus 签名生成
通过 Node.js 子进程调用 sign.js，规避 Windows GBK 编码问题
"""
import os
import subprocess
import logging

from .crypto import md5_encrypt
from .config import JS_DIR

logger = logging.getLogger(__name__)


def get_s(room_id: str) -> str:
    """
    根据直播间 ID 生成 s 值（MD5 签名参数）

    Args:
        room_id: 直播间内部 ID

    Returns:
        MD5 哈希字符串
    """
    param = {
        "app_name": "douyin_web",
        "version_code": "180800",
        "webcast_sdk_version": "1.0.14-beta.0",
        "update_version_code": "1.0.14-beta.0",
        "compress": "gzip",
        "device_platform": "web",
        "cookie_enabled": 'true',
        "screen_width": 1920,
        "screen_height": 1080,
        "browser_language": "zh-CN",
        "browser_platform": "Win32",
        "browser_name": "Mozilla",
        "browser_version": "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "browser_online": 'true',
        "tz_name": "Asia/Shanghai",
        "cursor": "t-1748834041134_r-7511185012226569781_d-7511185012226523137_u-1_fh-7511184045972533541",
        "internal_ext": "internal_src:dim|wss_push_room_id:7511169016510040832|wss_push_did:7506916920386848296|first_req_ms:1748834041041|fetch_time:1748834041134|seq:1|wss_info:0-1748834041134-0-0|wrds_v:7511184999341623742",
        "host": "https://live.douyin.com",
        "aid": "6383",
        "live_id": 1,
        "did_rule": 3,
        "endpoint": "live_pc",
        "support_wrds": 1,
        "user_unique_id": "7506916920386848296",
        "im_path": "/webcast/im/fetch/",
        "identity": "audience",
        "need_persist_msg_count": "15",
        "insert_task_id": "",
        "live_reason": "",
        "room_id": room_id,
        "heartbeatDuration": "0"
    }

    # 参数拼接顺序
    order = [
        "live_id", "aid", "version_code", "webcast_sdk_version",
        "room_id", "sub_room_id", "sub_channel_id", "did_rule",
        "user_unique_id", "device_platform", "device_type", "ac", "identity",
    ]

    parts = []
    for name in order:
        value = param.get(name, '')
        parts.append(f"{name}={value}")

    return md5_encrypt(','.join(parts))


def get_sign(room_id: str) -> str:
    """
    获取 X-Bogus 签名值

    通过 Node.js 子进程执行 get_sign_wrapper.js，
    读取 sign.js 中的签名算法，通过 stdin/stdout 传参。

    Args:
        room_id: 直播间内部 ID

    Returns:
        签名字符串
    """
    s = get_s(room_id)

    wrapper_path = os.path.join(JS_DIR, 'get_sign_wrapper.js')
    if not os.path.exists(wrapper_path):
        raise FileNotFoundError(f"签名脚本不存在: {wrapper_path}")

    try:
        result = subprocess.run(
            ['node', wrapper_path],
            input=s,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10
        )
        if result.returncode != 0:
            raise RuntimeError(f"签名生成失败: {result.stderr}")

        return result.stdout.strip()

    except FileNotFoundError:
        raise RuntimeError(
            "未找到 Node.js，请先安装 Node.js: https://nodejs.org/"
        )
