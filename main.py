"""
抖音直播弹幕AI回复助手 - 程序入口

用法：
    python main.py                  # 默认启用自动重连
    python main.py --no-reconnect   # 不自动重连（断线即退出）
"""
import argparse
import logging
import time

from douyin_ai_assist.config import ROOM_ID, HOST_NAME,AI_MODEL, validate
from douyin_ai_assist.live_client import DouYinLive

def setup_logging():
    """配置全局日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[logging.StreamHandler()]
    )
    # 隐藏第三方库的冗余日志
    logging.getLogger('websocket').setLevel(logging.ERROR)
    logging.getLogger('requests').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)


def print_banner():
    """打印启动横幅"""
    print("=" * 60)
    print(f"  抖音直播AI回复助手 - {HOST_NAME}")
    print("=" * 60)
    print(f"  直播间: https://live.douyin.com/{ROOM_ID}")
    print(f"  AI引擎: {AI_MODEL}")
    print(f"  功能:   实时弹幕 → AI回复 → 语音播报")
    print("=" * 60)
    print()


def main():
    parser = argparse.ArgumentParser(description="抖音直播弹幕AI回复助手")
    parser.add_argument(
        "--no-reconnect",
        action="store_true",
        help="禁用自动重连（默认启用）"
    )
    args = parser.parse_args()

    setup_logging()
    validate()  # 校验必要配置
    print_banner()

    if args.no_reconnect:
        # 基础模式：不重连
        client = DouYinLive(ROOM_ID)
        client.start()
    else:
        # 自动重连模式（默认）
        max_reconnects = 100
        reconnect_delay = 5

        for attempt in range(1, max_reconnects + 1):
            try:
                client = DouYinLive(ROOM_ID)
                client.start()
            except KeyboardInterrupt:
                print("\n[系统] 用户手动停止程序")
                break
            except Exception as e:
                print(f"\n[系统] 连接异常: {e}")
                print(f"[系统] {reconnect_delay}秒后尝试第 {attempt} 次重连...")
                time.sleep(reconnect_delay)
                print("[系统] 正在重连...")
                print("=" * 60)
        else:
            print(f"\n[系统] 已达到最大重连次数({max_reconnects})，程序停止")


if __name__ == "__main__":
    main()
