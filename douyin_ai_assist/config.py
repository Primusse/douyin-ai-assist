"""
抖音直播弹幕AI回复助手 - 配置文件
请在此处填写你的直播间信息和 API Key
"""
import os
import sys

# ==================== 路径配置 ====================
# 项目根目录（douyin-live-ai/）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据目录（运行时生成的文件存放于此）
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
TTS_CACHE_DIR = os.path.join(DATA_DIR, "tts_cache")

# JS 资源目录
JS_DIR = os.path.join(PROJECT_ROOT, "js")

# ==================== 直播间配置 ====================
# 抖音直播间ID（URL最后的数字，如 https://live.douyin.com/349873582969）
ROOM_ID = "your_room_id"

# 直播类型: "ecommerce"(电商), "education"(教育), "entertainment"(娱乐)
LIVE_TYPE = "entertainment"

# ==================== 主播简介配置 ====================
# 主播名称
HOST_NAME = "小玉"

# 主播简介 - 用于让AI了解主播背景和风格，填写越详细回复越准确
HOST_INTRO = """
主播是英雄联盟游戏主播，专注于LOL游戏直播。
擅长各种英雄操作，经常分享游戏技巧、出装思路、对线细节。
直播风格幽默风趣，与观众互动频繁，乐于解答游戏相关问题。
"""

# 主播人设风格
HOST_PERSONA = "幽默风趣，技术过硬但平易近人，喜欢和观众互动"

# 回复风格: "professional"(专业), "friendly"(亲切), "humorous"(humorous)
REPLY_STYLE = "humorous"

# ==================== AI 服务配置 ====================
# API 格式: "openai"（兼容 OpenAI 格式）或 "claude"（Anthropic 格式）
# 绝大多数国产/海外模型（DeepSeek、智谱、通义、Moonshot、GPT 等）都兼容 OpenAI 格式
AI_API_FORMAT = "openai"

# API 请求地址（必填）
AI_API_URL = "https://api.deepseek.com/v1/chat/completions"

# API Key（推荐通过环境变量设置：set AI_API_KEY=sk-xxxx）
# 如果想直接填入可以填到后面的引号里。如os.environ.get("AI_API_KEY", "sk-xxxxx")
AI_API_KEY = os.environ.get("AI_API_KEY", "")

# 模型名称（必填）
AI_MODEL = "deepseek-v4-flash"

# 温度参数 (0-2, 越高越 creative，建议 0.7)
AI_TEMPERATURE = 0.7

# 最大 token 数
AI_MAX_TOKENS = 1000

# ==================== 缓存配置 ====================
# 回复记录文件路径
REPLY_FILE = os.path.join(DATA_DIR, "ai_replies.jsonl")

# ==================== TTS 语音合成配置 ====================
# 是否启用 TTS（True=AI回复自动朗读，False=仅文字输出）
TTS_ENABLED = True

# 语音角色（微软 Edge TTS 中文语音）
# 可选:
#   zh-CN-XiaoxiaoNeural  — 女声，自然亲切（推荐）
#   zh-CN-YunxiNeural     — 男声，年轻活力
#   zh-CN-XiaoyiNeural    — 女声，温柔甜美
#   zh-CN-YunjianNeural   — 男声，成熟稳重
TTS_VOICE = "zh-CN-XiaoyiNeural"

# 语速调节 ("+0%" 正常, "+20%" 加速, "-20%" 减速)
TTS_RATE = "+0%"

# ==================== 意图过滤配置 ====================
# 过滤模式: "all"=回复所有弹幕, "ecommerce"=仅回复产品相关问题
FILTER_MODE = "all"

# 产品相关关键词（仅 FILTER_MODE="ecommerce" 时生效）
# 命中任一关键词的弹幕才会调用 AI 回复，其余直接跳过
# 按需修改，适配你的商品品类
PRODUCT_KEYWORDS = [
    # 购买意图
    "多少钱", "价格", "怎么买", "链接", "下单", "拍", "购买", "有货", "库存",
    "优惠", "券", "便宜", "打折", "活动", "秒杀", "包邮", "满减",
    # 产品咨询
    "质量", "材质", "尺寸", "颜色", "型号", "款式", "尺码", "大小",
    "保质期", "有效期", "成分", "配方", "产地",
    # 物流售后
    "发货", "快递", "几天到", "退换", "售后", "保修",
    # 通用疑问（结合上下文通常指产品）
    "这个", "那个", "还有吗", "有推荐", "哪个好", "怎么样", "好不好",
]

# ==================== 过滤配置 ====================
# 忽略的用户名列表 (如机器人、管理员)
IGNORED_USERS = ["管理员", "系统消息"]

# 忽略的关键词 (如纯表情、无意义内容)
IGNORED_KEYWORDS = ["666", "哈哈哈", "...", "???"]

# 最小消息长度 (小于此长度将忽略)
MIN_MESSAGE_LENGTH = 2

# ==================== 回复模板配置 ====================
# 高频问题的固定回复模板，命中关键词直接回复，不消耗 API 额外调用
# 模板匹配优先级高于缓存和 AI API
#
# 格式：
#   {
#       "keywords": ["关键词1", "关键词2"],  # 命中任一即匹配（默认）
#       "reply": "回复内容",                  # 固定回复文本
#       "match": "any"                        # 可选: "any"=命中任一(默认), "all"=全部命中
#   }
#
# 回复中可用 {user} 代替当前用户名
# 设为空列表 [] 则禁用模板匹配
REPLY_TEMPLATES = [
    {
        "keywords": ["怎么买", "哪里买", "购买链接", "链接", "下单"],
        "reply": "@{user} 点击直播间下方小黄车即可下单哦，今天有优惠活动！"
    },
    {
        "keywords": ["多少钱", "价格", "什么价"],
        "reply": "@{user} 价格在小黄车里看哦，今天活动价很划算！"
    },
    {
        "keywords": ["发货", "快递", "几天到"],
        "reply": "@{user} 拍下后48小时内发货，一般3-5天到~"
    },
    {
        "keywords": ["质量", "好不好", "怎么样"],
        "reply": "@{user} 放心品质的，我自己都在用！有问题随时找售后~"
    },
]


def validate():
    """启动时校验必要配置"""
    errors = []
    if not AI_API_KEY:
        errors.append(
            "未配置 AI_API_KEY，请设置环境变量或在 config.py 中填写\n"
            "  环境变量: set AI_API_KEY=sk-xxxx"
        )
    if not ROOM_ID:
        errors.append("未配置 ROOM_ID，请在 config.py 中填写直播间ID")
    if errors:
        for e in errors:
            print(f"[配置错误] {e}", file=sys.stderr)
        sys.exit(1)
