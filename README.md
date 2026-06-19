# 抖音直播弹幕 AI 智能回复助手

> **⚠️ 本项目仅供学习交流和技术研究使用，请勿用于任何商业或违法用途。**
>
> 项目基于抖音直播 WebSocket 协议和 Protobuf 消息格式的学习与实践，旨在帮助开发者了解：
> - WebSocket 实时通信的实现方式
> - Protobuf 协议的解析与应用
> - AI API 的接入与调用方式
> - TTS 语音合成技术的集成
>
> 使用本项目产生的一切后果由使用者自行承担。

---

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Node.js](https://img.shields.io/badge/Node.js-Required-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 项目简介

通过 WebSocket 连接抖音直播间，实时采集弹幕消息，调用 AI 接口生成智能回复，并支持 TTS 语音播报。

**核心流程：**

```
弹幕采集 → 消息过滤 → 回复模板 / LRU 缓存 → AI API 生成 → 控制台输出 + TTS 播报
```

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 实时弹幕采集 | WebSocket 直连抖音直播服务器，Protobuf 解码 |
| AI 智能回复 | 支持 DeepSeek、OpenAI、智谱、通义、Claude 等多种 AI 服务 |
| 回复模板 | 高频问题配置固定回复模板，命中关键词直接回复，零 API 消耗 |
| 智能缓存 | LRU 缓存最近 100 条回复，相同问题直接命中 |
| 意图过滤 | 自动过滤无效弹幕、指定用户/关键词，支持电商模式 |
| TTS 语音播报 | AI 回复通过微软 Edge TTS 自动朗读 |
| 自动重连 | 网络断开自动恢复，支持无人值守运行 |

---

## 效果预览

```
============================================================
[2026-06-19 20:30:15] [模板] 暴躁的嘉文四世: 这个怎么买
------------------------------------------------------------
AI回复: @暴躁的嘉文四世 点击直播间下方小黄车即可下单哦，今天有优惠活动！
============================================================

============================================================
[2026-06-19 20:31:02] [API] 嘦姕: 龙女改版了？
------------------------------------------------------------
AI回复: @嘦姕 朋友好眼力！龙女确实改版了，新W加了额外移速，清野效率更高！
============================================================

============================================================
[2026-06-19 20:32:18] [缓存] 路人甲: W什么技能
------------------------------------------------------------
AI回复: @路人甲 朋友，W是黄金圣盾！开盾减速还能加护甲~
============================================================
```

- `[模板]` — 命中预设回复模板，不消耗 API
- `[缓存]` — 命中 LRU 缓存，不消耗 API
- `[API]` — 实时调用 AI 接口生成

---

## 快速开始

### 环境要求

- Python 3.7+
- Node.js（用于签名生成脚本）

### 安装

```bash
git clone https://github.com/Primusse/douyin-ai-assist.git
cd douyin-live-ai
pip install -r requirements.txt
```

### 配置

编辑 `douyin_ai_assist/config.py`，填写以下必填项：

```python
# 直播间 ID（浏览器打开直播间，URL 末尾的数字）
ROOM_ID = "3498735829xx"

# AI 服务配置
AI_API_URL = "https://api.deepseek.com/v1/chat/completions"
AI_MODEL   = "deepseek-v4-flash"
AI_API_KEY = "your_api_key_here"   # 或通过环境变量: set AI_API_KEY=sk-xxxx
```

### 启动

```bash
# Windows 一键启动（自动设置 UTF-8 编码）
start.bat

# 或手动启动（默认自动重连）
python main.py

# 不自动重连（断线即退出）
python main.py --no-reconnect
```

---

## 配置说明

所有配置项在 `douyin_ai_assist/config.py` 中，以下是完整说明：

### 直播间配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `ROOM_ID` | `""` | 直播间 ID，取自 URL 末尾数字 |
| `LIVE_TYPE` | `"entertainment"` | 直播类型：`ecommerce` / `education` / `entertainment` |

### 主播人设配置

| 配置项 | 说明 |
|--------|------|
| `HOST_NAME` | 主播名称 |
| `HOST_INTRO` | 主播简介，越详细 AI 回复越准确 |
| `HOST_PERSONA` | 主播人设风格描述 |
| `REPLY_STYLE` | 回复风格：`professional`（专业）/ `friendly`（亲切）/ `humorous`（幽默） |

### AI 服务配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `AI_API_FORMAT` | `"openai"` | API 格式，`"openai"` 或 `"claude"` |
| `AI_API_URL` | DeepSeek 地址 | API 请求地址 |
| `AI_MODEL` | `"deepseek-chat"` | 模型名称 |
| `AI_API_KEY` | `""` | API Key，推荐通过环境变量设置 |
| `AI_TEMPERATURE` | `0.7` | 温度参数，0=严谨，2=创意 |
| `AI_MAX_TOKENS` | `500` | 最大 token 数 |

**切换 AI 服务商只需改 `AI_API_URL` 和 `AI_MODEL`：**

| 服务商 | `AI_API_FORMAT` | `AI_API_URL` | `AI_MODEL` |
|--------|-----------------|-------------|-----------|
| DeepSeek | `openai` | `https://api.deepseek.com/v1/chat/completions` | `deepseek-chat` |
| OpenAI | `openai` | `https://api.openai.com/v1/chat/completions` | `gpt-4o-mini` |
| 智谱 AI | `openai` | `https://open.bigmodel.cn/api/paas/v4/chat/completions` | `glm-4-flash` |
| 通义千问 | `openai` | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | `qwen-turbo` |
| Moonshot | `openai` | `https://api.moonshot.cn/v1/chat/completions` | `moonshot-v1-8k` |
| Claude | `claude` | `https://api.anthropic.com/v1/messages` | `claude-haiku-4-5-20251001` |

> 绝大多数模型兼容 OpenAI 格式，`AI_API_FORMAT` 设为 `"openai"` 即可。

### 回复模板配置

高频问题可配置固定回复模板，命中关键词直接回复，不消耗 API 调用：

```python
REPLY_TEMPLATES = [
    {
        "keywords": ["怎么买", "链接", "下单"],
        "reply": "@{user} 点击小黄车即可下单~"
    },
    {
        "keywords": ["多少钱", "价格"],
        "reply": "@{user} 价格在小黄车里看哦~"
    },
    {
        "keywords": ["发货", "快递"],
        "reply": "@{user} 拍下后48小时内发货，一般3-5天到~"
    },
]
```

- `keywords` — 关键词列表，命中任一即触发
- `reply` — 回复内容，`{user}` 自动替换为当前用户名
- `match` — 可选，`"any"`（默认）命中任一即匹配，`"all"` 全部命中才匹配
- 设为 `[]` 禁用模板

### 过滤配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `FILTER_MODE` | `"all"` | `all`=回复全部弹幕，`ecommerce`=仅回复产品相关 |
| `PRODUCT_KEYWORDS` | `[...]` | 电商模式下的产品关键词列表 |
| `IGNORED_USERS` | `["管理员", "系统消息"]` | 忽略的用户名 |
| `IGNORED_KEYWORDS` | `["666", "哈哈哈", ...]` | 忽略的关键词 |
| `MIN_MESSAGE_LENGTH` | `2` | 最小消息长度 |

### TTS 语音合成配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `TTS_ENABLED` | `True` | 是否启用语音播报 |
| `TTS_VOICE` | `"zh-CN-XiaoyiNeural"` | 语音角色 |
| `TTS_RATE` | `"+0%"` | 语速，`+20%` 加速，`-20%` 减速 |

**可选语音角色：**

| 语音 ID | 描述 |
|---------|------|
| `zh-CN-XiaoxiaoNeural` | 女声，自然亲切 |
| `zh-CN-YunxiNeural` | 男声，年轻活力 |
| `zh-CN-XiaoyiNeural` | 女声，温柔甜美 |
| `zh-CN-YunjianNeural` | 男声，成熟稳重 |

---

## 项目结构

```
douyin-live-ai/
├── main.py                      # 程序入口
├── start.bat                    # Windows 一键启动脚本
├── requirements.txt             # Python 依赖
├── README.md
│
├── douyin_ai_assist/              # 核心代码包
│   ├── config.py                # 全局配置（直播间、AI、TTS、过滤、模板）
│   ├── live_client.py           # WebSocket 连接与生命周期管理
│   ├── message_parser.py        # Protobuf 消息解析与分发
│   ├── danmaku_filter.py        # 弹幕过滤规则
│   ├── ai_client.py             # 通用 AI 客户端（OpenAI 兼容 / Claude）
│   ├── ai_replier.py            # AI 回复生成（模板 → 缓存 → API）
│   ├── reply_templates.py       # 回复模板匹配引擎
│   ├── reply_cache.py           # LRU 缓存管理
│   ├── tts_engine.py            # TTS 语音合成（延迟初始化）
│   ├── sign.py                  # 抖音签名生成（封装 Node.js 调用）
│   ├── crypto.py                # MD5 加密工具
│   └── douyin/                  # Protobuf 协议定义
│       ├── douyin.proto         # 协议源文件
│       └── douyin_pb2.py        # protoc 自动生成的 Python 代码
│
├── js/                          # Node.js 签名脚本
│   ├── sign.js                  # X-Bogus 签名算法
│   └── get_sign_wrapper.js      # stdin/stdout 包装器
│
└── data/                        # 运行时数据（自动生成，已加入 .gitignore）
    ├── ai_replies.jsonl         # AI 回复日志
    ├── ai_replies_cache.json    # LRU 缓存持久化
    └── tts_cache/               # TTS 音频文件
```

### 模块职责

| 模块 | 职责 |
|------|------|
| `config.py` | 所有可配置项集中管理，启动时校验必填项 |
| `live_client.py` | 建立 WebSocket 连接、发送心跳包、管理连接生命周期 |
| `message_parser.py` | 解析 Protobuf 二进制消息，按类型分发给对应 handler |
| `danmaku_filter.py` | 弹幕过滤：长度、用户、关键词、电商模式 |
| `ai_client.py` | AI 客户端抽象层，支持 OpenAI 兼容格式和 Claude 格式 |
| `ai_replier.py` | 回复生成主逻辑：模板匹配 → 缓存查找 → API 调用 |
| `reply_templates.py` | 关键词匹配引擎，支持变量替换 |
| `reply_cache.py` | LRU 缓存，避免重复调用 API |
| `tts_engine.py` | TTS 合成与播放，单队列策略只播最新一条 |
| `sign.py` | 调用 Node.js 子进程生成抖音 X-Bogus 签名 |
| `crypto.py` | MD5 哈希工具 |

---

## 回复优先级

```
弹幕进入
  │
  ├─ 1. 回复模板匹配 ──→ 命中 ──→ 直接返回模板回复
  │
  ├─ 2. LRU 缓存查找 ──→ 命中 ──→ 返回缓存回复
  │
  └─ 3. 调用 AI API ──→ 生成回复 ──→ 写入缓存 ──→ 返回
```

---

## 常见问题

**Q: 提示 `'gbk' codec can't encode character`**

A: Windows 终端默认 GBK 编码，请使用 `start.bat` 启动（已内置 `chcp 65001` 切换 UTF-8）。

**Q: 程序运行一段时间后自动断开**

A: 正常现象，抖音服务器会主动关闭空闲连接。默认已启用自动重连，最多重试 100 次。

**Q: 没有弹幕输出**

A: 请确认：① 直播间 ID 正确 ② 目标直播间正在直播 ③ 网络连接正常。

**Q: AI 回复很慢或超时**

A: 检查网络是否能访问对应 API 地址。可降低 `AI_MAX_TOKENS` 加快响应。

**Q: 提示未配置 AI_API_KEY**

A: 在 `config.py` 中填写，或设置环境变量：`set AI_API_KEY=sk-xxxx`

**Q: 如何获取直播间 ID？**

A: 打开抖音直播间，浏览器地址栏 URL 末尾的数字即为 ID：
```
https://live.douyin.com/349873582969
                        ^^^^^^^^^^^^
                        这串数字就是 ROOM_ID
```

**Q: 如何切换 AI 服务商？**

A: 修改 `config.py` 中的 `AI_API_URL` 和 `AI_MODEL` 即可，详见上方配置说明。

---

## 依赖列表

| 依赖 | 版本要求 | 用途 |
|------|---------|------|
| Python | 3.7+ | 运行环境 |
| Node.js | 任意版本 | 执行签名生成脚本 |
| websocket-client | >=1.6.0 | WebSocket 连接 |
| requests | >=2.28.0 | HTTP 请求 |
| protobuf | >=4.21.0 | 解析 Protobuf 消息 |
| edge-tts | >=6.1.0 | TTS 语音合成 |
| pygame | >=2.5.0 | 音频播放 |

```bash
pip install -r requirements.txt
```

---

## 免责声明

1. 本项目仅供学习交流和技术研究，不得用于任何商业用途。
2. 本项目通过逆向分析抖音直播协议实现功能，可能违反抖音的服务条款，使用者需自行承担风险。
3. 项目作者不对使用本项目造成的任何损失承担责任。
4. 如本项目侵犯了任何第三方权益，请联系删除。
5. 使用本项目即表示您已阅读并同意以上声明。

---

## 许可证

MIT License

---

## 致谢
- [douyin-live-ai by go522000](https://github.com/go522000/douyin-live-ai) — 本项目基于此仓库开发，感谢原作者提供的抖音直播协议解析与 WebSocket 连接方案
- [edge-tts](https://github.com/rany2/edge-tts) — 微软 Edge TTS 语音合成
