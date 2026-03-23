"""
LLM提供商适配器 - 支持 DeepSeek, Kimi, OpenAI, Claude, 通义千问等
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx
from loguru import logger

from config import get_config


class BaseLLMProvider(ABC):
    """LLM提供商基类"""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成文本"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查是否可用"""
        pass


def _get_config_value(config, key: str, default=None):
    """安全获取配置值，支持 dict 和 Pydantic 模型"""
    if config is None:
        return default
    if isinstance(config, dict):
        return config.get(key, default)
    # Pydantic 模型
    return getattr(config, key, default)


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek 提供商"""
    
    def __init__(self):
        self.config = get_config().llm.providers.get("deepseek", {})
        self.api_key = _get_config_value(self.config, "api_key")
        self.base_url = _get_config_value(self.config, "base_url", "https://api.deepseek.com")
        self.model = _get_config_value(self.config, "model", "deepseek-chat")
        self.temperature = _get_config_value(self.config, "temperature", 0.3)
        self.max_tokens = _get_config_value(self.config, "max_tokens", 4000)
    
    def is_available(self) -> bool:
        return bool(self.api_key) and _get_config_value(self.config, "enabled", False)
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            raise Exception("DeepSeek API Key未配置")
        
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": kwargs.get("temperature", self.temperature),
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens)
                }
            )
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "text": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
                "model": data.get("model", self.model)
            }


class KimiProvider(BaseLLMProvider):
    """Kimi (Moonshot AI) 提供商"""
    
    def __init__(self):
        self.config = get_config().llm.providers.get("kimi", {})
        self.api_key = _get_config_value(self.config, "api_key")
        self.base_url = _get_config_value(self.config, "base_url", "https://api.moonshot.cn")
        self.model = _get_config_value(self.config, "model", "moonshot-v1-8k")
        self.temperature = _get_config_value(self.config, "temperature", 0.3)
        self.max_tokens = _get_config_value(self.config, "max_tokens", 4000)
    
    def is_available(self) -> bool:
        return bool(self.api_key) and _get_config_value(self.config, "enabled", False)
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            raise Exception("Kimi API Key未配置")
        
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": [
                        {"role": "system", "content": "你是Kimi，一个AI助手。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": kwargs.get("temperature", self.temperature),
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens)
                }
            )
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "text": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
                "model": data.get("model", self.model)
            }


class OpenAIProvider(BaseLLMProvider):
    """OpenAI提供商"""
    
    def __init__(self):
        self.config = get_config().llm.providers.get("openai", {})
        self.api_key = _get_config_value(self.config, "api_key")
        self.base_url = _get_config_value(self.config, "base_url", "https://api.openai.com/v1")
        self.model = _get_config_value(self.config, "model", "gpt-4-turbo-preview")
        self.temperature = _get_config_value(self.config, "temperature", 0.3)
        self.max_tokens = _get_config_value(self.config, "max_tokens", 4000)
    
    def is_available(self) -> bool:
        return bool(self.api_key) and _get_config_value(self.config, "enabled", False)
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            raise Exception("OpenAI API Key未配置")
        
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": kwargs.get("temperature", self.temperature),
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens)
                }
            )
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "text": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
                "model": data.get("model", self.model)
            }


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude提供商"""
    
    def __init__(self):
        self.config = get_config().llm.providers.get("claude", {})
        self.api_key = _get_config_value(self.config, "api_key")
        self.model = _get_config_value(self.config, "model", "claude-3-sonnet-20240229")
        self.temperature = _get_config_value(self.config, "temperature", 0.3)
        self.max_tokens = _get_config_value(self.config, "max_tokens", 4000)
    
    def is_available(self) -> bool:
        return bool(self.api_key) and _get_config_value(self.config, "enabled", False)
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            raise Exception("Claude API Key未配置")
        
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                    "temperature": kwargs.get("temperature", self.temperature)
                }
            )
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "text": data["content"][0]["text"],
                "usage": data.get("usage", {}),
                "model": data.get("model", self.model)
            }


class QwenProvider(BaseLLMProvider):
    """通义千问提供商"""
    
    def __init__(self):
        self.config = get_config().llm.providers.get("qwen", {})
        self.api_key = _get_config_value(self.config, "api_key")
        self.base_url = _get_config_value(self.config, "base_url", "https://dashscope.aliyuncs.com/api/v1")
        self.model = _get_config_value(self.config, "model", "qwen-max")
        self.temperature = _get_config_value(self.config, "temperature", 0.3)
        self.max_tokens = _get_config_value(self.config, "max_tokens", 4000)
    
    def is_available(self) -> bool:
        return bool(self.api_key) and _get_config_value(self.config, "enabled", False)
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            raise Exception("通义千问 API Key未配置")
        
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": kwargs.get("model", self.model),
                    "input": {
                        "messages": [
                            {"role": "user", "content": prompt}
                        ]
                    },
                    "parameters": {
                        "temperature": kwargs.get("temperature", self.temperature),
                        "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                        "result_format": "message"
                    }
                }
            )
            resp.raise_for_status()
            data = resp.json()
            
            output = data.get("output", {})
            usage = data.get("usage", {})
            
            return {
                "text": output.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "usage": {
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                },
                "model": self.model
            }


class OllamaProvider(BaseLLMProvider):
    """Ollama本地提供商"""
    
    def __init__(self):
        self.config = get_config().llm.providers.get("ollama", {})
        self.base_url = _get_config_value(self.config, "base_url", "http://localhost:11434")
        self.model = _get_config_value(self.config, "model", "llama2-chinese")
    
    def is_available(self) -> bool:
        if not _get_config_value(self.config, "enabled", False):
            return False
        try:
            import httpx
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except:
            return False
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": kwargs.get("model", self.model),
                    "prompt": prompt,
                    "stream": False
                }
            )
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "text": data.get("response", ""),
                "usage": {},
                "model": self.model
            }


class MockProvider(BaseLLMProvider):
    """模拟提供商（用于测试）"""
    
    def is_available(self) -> bool:
        return True
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        logger.warning("使用模拟LLM提供商（测试模式）")
        
        if "清洗" in prompt or "clean" in prompt.lower():
            return {
                "text": "# 清洗后的内容\n\n这是模拟的清洗后内容。\n\n实际使用时请配置真实的LLM API。",
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                "model": "mock"
            }
        elif "摘要" in prompt or "summarize" in prompt.lower():
            return {
                "text": "摘要: 这是一份模拟的文档摘要。\n关键词: 测试, 模拟, 示例\n主题: 测试主题",
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                "model": "mock"
            }
        elif "分类" in prompt or "classify" in prompt.lower():
            return {
                "text": "推荐路径: 01-产品知识库/CMP（多云管理平台）/01-交付实施\n置信度: 85\n理由: 这是一份部署相关的文档",
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                "model": "mock"
            }
        elif "质量" in prompt or "quality" in prompt.lower():
            return {
                "text": """总评分: 85
各维度得分:
- 格式规范性: 25/30
- 内容完整性: 28/30
- 逻辑清晰度: 18/20
- 可读性: 14/20

问题列表:
1. 部分段落过长 - 建议拆分为短段落

是否通过: 是""",
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                "model": "mock"
            }
        else:
            return {
                "text": "这是模拟的LLM响应。请配置真实的LLM API以获得更好的效果。",
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                "model": "mock"
            }


class LLMProviderFactory:
    """LLM提供商工厂"""
    
    _providers = {
        "deepseek": DeepSeekProvider,
        "kimi": KimiProvider,
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "qwen": QwenProvider,
        "ollama": OllamaProvider,
        "mock": MockProvider
    }
    
    @classmethod
    def get_provider(cls, name: Optional[str] = None) -> BaseLLMProvider:
        """获取提供商实例"""
        config = get_config().llm
        
        # 如果指定了名称
        if name and name in cls._providers:
            provider = cls._providers[name]()
            if provider.is_available():
                return provider
        
        # 按优先级查找可用提供商
        priority = ["deepseek", "kimi", "openai", "claude", "qwen", "ollama"]
        
        for p in priority:
            if p in cls._providers:
                provider = cls._providers[p]()
                if provider.is_available():
                    logger.info(f"使用LLM提供商: {p}")
                    return provider
        
        # 默认使用模拟提供商
        logger.warning("未配置可用的LLM提供商，使用模拟模式")
        return MockProvider()
    
    @classmethod
    def register(cls, name: str, provider_class):
        """注册新提供商"""
        cls._providers[name] = provider_class
