import asyncio
from enum import Enum
from typing import List, Tuple, Callable, Union, Dict

from retk import config, const
from retk.core.utils import ratelimiter
from .base import ModelConfig, MessagesType
from .openai import OpenaiLLMStyle


# https://open.bigmodel.cn/dev/howuse/rate-limits/tiers?tab=0
class GLMModelEnum(Enum):
    GLM4_PLUS = ModelConfig(
        key="GLM-4-Plus",
        max_tokens=128_000,
    )
    GLM4_LONG = ModelConfig(
        key="GLM-4-Long",
        max_tokens=1_000_000,
    )
    GLM4_FLASH = ModelConfig(
        key="GLM-4-Flash",
        max_tokens=128_000,
    )


class GLMService(OpenaiLLMStyle):
    name = "glm"

    def __init__(
            self,
            top_p: float = 0.9,
            temperature: float = 0.9,
            timeout: float = 60.,
    ):
        super().__init__(
            model_enum=GLMModelEnum,
            endpoint="https://open.bigmodel.cn/api/paas/v4/chat/completions",
            default_model=GLMModelEnum.GLM4_FLASH.value,
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
        )

    @classmethod
    def set_api_auth(cls, auth: Dict[str, str]):
        config.get_settings().BIGMODEL_API_KEY = auth.get("API-KEY", "")

    @staticmethod
    def get_api_key():
        return config.get_settings().BIGMODEL_API_KEY

    @staticmethod
    async def _batch_complete_union(
            messages: List[MessagesType],
            func: Callable,
            model: str = None,
            req_id: str = None,
    ) -> List[Tuple[Union[str, Dict[str, str]], const.CodeEnum]]:
        settings = config.get_settings()
        concurrent_limiter = ratelimiter.ConcurrentLimiter(n=settings.BIGMODEL_CONCURRENCY)

        tasks = [
            func(
                limiters=[concurrent_limiter],
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
