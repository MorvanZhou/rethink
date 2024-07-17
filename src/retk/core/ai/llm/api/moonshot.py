from enum import Enum

from retk import config
from .base import ModelConfig
from .openai import OpenaiLLMStyle


# https://platform.moonshot.cn/docs/pricing#%E4%BB%B7%E6%A0%BC%E8%AF%B4%E6%98%8E
class MoonshotModelEnum(Enum):
    V1_8K = ModelConfig(
        key="moonshot-v1-8k",
        max_tokens=8000,
    )
    V1_32K = ModelConfig(
        key="moonshot-v1-32k",
        max_tokens=32000,
    )
    V1_128K = ModelConfig(
        key="moonshot-v1-128k",
        max_tokens=128000,
    )


class MoonshotService(OpenaiLLMStyle):
    def __init__(
            self,
            top_p: float = 0.9,
            temperature: float = 0.3,
            timeout: float = 60.,
    ):
        super().__init__(
            endpoint="https://api.moonshot.cn/v1/chat/completions",
            default_model=MoonshotModelEnum.V1_8K.value,
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
        )

    @staticmethod
    def get_api_key():
        return config.get_settings().MOONSHOT_API_KEY

    @staticmethod
    def get_concurrency():
        return config.get_settings().MOONSHOT_CONCURRENCY
