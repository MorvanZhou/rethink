from enum import Enum

from retk import config
from .openai import OpenaiLLMStyle


# https://platform.moonshot.cn/docs/pricing#%E4%BB%B7%E6%A0%BC%E8%AF%B4%E6%98%8E
class MoonshotModelEnum(str, Enum):
    V1_8K = "moonshot-v1-8k"
    V1_32K = "moonshot-v1-32k"
    V1_128K = "moonshot-v1-128k"


class MoonshotService(OpenaiLLMStyle):
    def __init__(
            self,
            top_p: float = 0.9,
            temperature: float = 0.7,
            timeout: float = 60.,
    ):
        super().__init__(
            api_key=config.get_settings().MOONSHOT_API_KEY,
            endpoint="https://api.moonshot.cn/v1/chat/completions",
            default_model=MoonshotModelEnum.V1_8K.value,
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
        )
