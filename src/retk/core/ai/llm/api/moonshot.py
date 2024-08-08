import asyncio
from enum import Enum
from typing import List, Tuple, Callable, Union, Dict

from retk import config, const
from retk.core.utils import ratelimiter
from .base import ModelConfig, MessagesType
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
    name = "moonshot"

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

    @classmethod
    def set_api_auth(cls, auth: Dict[str, str]):
        config.get_settings().MOONSHOT_API_KEY = auth.get("API-KEY", "")

    @staticmethod
    def get_api_key():
        return config.get_settings().MOONSHOT_API_KEY

    @staticmethod
    async def _batch_complete_union(
            messages: List[MessagesType],
            func: Callable,
            model: str = None,
            req_id: str = None,
    ) -> List[Tuple[Union[str, Dict[str, str]], const.CodeEnum]]:
        settings = config.get_settings()
        rate_limiter = ratelimiter.RateLimiter(requests=settings.MOONSHOT_RPM, period=60)
        concurrent_limiter = ratelimiter.ConcurrentLimiter(n=settings.MOONSHOT_CONCURRENCY)

        tasks = [
            func(
                limiters=[concurrent_limiter, rate_limiter],
                messages=m,
                model=model,
                req_id=req_id,
            ) for m in messages
        ]
        return await asyncio.gather(*tasks)

    async def batch_complete(
            self,
            messages: List[MessagesType],
            model: str = None,
            req_id: str = None,
    ) -> List[Tuple[str, const.CodeEnum]]:
        return await self._batch_complete_union(
            messages=messages,
            func=self._batch_complete,
            model=model,
            req_id=req_id,
        )

    async def batch_complete_json_detect(
            self,
            messages: List[MessagesType],
            model: str = None,
            req_id: str = None,
    ) -> List[Tuple[Dict[str, str], const.CodeEnum]]:
        return await self._batch_complete_union(
            messages=messages,
            func=self._batch_stream_complete_json_detect,
            model=model,
            req_id=req_id,
        )
