"""
通用 AI 客户端接口
支持两种 API 格式：
- openai: 兼容 OpenAI Chat Completions 格式（DeepSeek、GPT、智谱、通义、Moonshot 等）
- claude: Anthropic Messages 格式（Claude 系列）
"""
import logging
from abc import ABC, abstractmethod

import requests

logger = logging.getLogger(__name__)


class AIClient(ABC):
    """AI 客户端抽象基类"""

    @abstractmethod
    def chat(self, system_prompt: str, user_message: str) -> str:
        """
        发送对话请求，返回 AI 回复文本

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息

        Returns:
            AI 回复文本

        Raises:
            Exception: API 调用失败时抛出异常
        """
        ...


class OpenAICompatibleClient(AIClient):
    """
    OpenAI 兼容格式客户端

    适用于所有兼容 OpenAI Chat Completions API 的服务商：
    DeepSeek、OpenAI、智谱、通义千问、Moonshot、零一万物、硅基流动等
    """

    def __init__(self, api_key: str, api_url: str, model: str,
                 temperature: float = 0.7, max_tokens: int = 500,
                 timeout: int = 30):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def chat(self, system_prompt: str, user_message: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False
        }

        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=self.timeout
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"API 错误 [{response.status_code}]: {response.text}"
            )

        result = response.json()
        return result['choices'][0]['message']['content'].strip()


class ClaudeClient(AIClient):
    """
    Anthropic Claude 客户端

    适用于 Claude 系列模型（claude-sonnet、claude-haiku 等）
    """

    def __init__(self, api_key: str, api_url: str, model: str,
                 temperature: float = 0.7, max_tokens: int = 500,
                 timeout: int = 30):
        self.api_key = api_key
        self.api_url = api_url or "https://api.anthropic.com/v1/messages"
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def chat(self, system_prompt: str, user_message: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }

        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=self.timeout
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Claude API 错误 [{response.status_code}]: {response.text}"
            )

        result = response.json()
        return result['content'][0]['text'].strip()


def create_client(api_format: str, api_key: str, api_url: str,
                  model: str, temperature: float = 0.7,
                  max_tokens: int = 500) -> AIClient:
    """
    根据配置创建 AI 客户端实例

    Args:
        api_format: API 格式，"openai" 或 "claude"
        api_key: API Key
        api_url: API 请求地址
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大 token 数

    Returns:
        AIClient 实例
    """
    clients = {
        "openai": OpenAICompatibleClient,
        "claude": ClaudeClient,
    }

    client_class = clients.get(api_format)
    if not client_class:
        raise ValueError(
            f"不支持的 API 格式: '{api_format}'，可选: openai, claude"
        )

    return client_class(
        api_key=api_key,
        api_url=api_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
