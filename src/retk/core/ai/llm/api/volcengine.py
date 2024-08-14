import asyncio
import json
from enum import Enum
from typing import List, Tuple, Callable, Union, Dict, AsyncIterable

from retk import config, const
from retk.core.utils import ratelimiter
from retk.logger import logger
from .base import ModelConfig, MessagesType
from .openai import OpenaiLLMStyle


# API https://www.volcengine.com/docs/82379/1263482
# model fee https://www.volcengine.com/docs/82379/1099320


class VolcEngineModelEnum(Enum):
    DOUBAO_LITE_4K = ModelConfig(
        key="Doubao-lite-4k",
        max_tokens=4000,
        TPM=800000,
        RPM=10000,
    )
    DOUBAO_LITE_32K = ModelConfig(
        key="Doubao-lite-32k",
        max_tokens=32000,
        TPM=800000,
        RPM=10000,
    )
    DOUBAO_LITE_128K = ModelConfig(
        key="Doubao-lite-128k",
        max_tokens=128000,
        TPM=400000,
        RPM=1000,
    )
    DOUBAO_PRO_4K = ModelConfig(
        key="Doubao-pro-4k",
        max_tokens=4000,
        TPM=800000,
        RPM=10000,
    )
    DOUBAO_PRO_32K = ModelConfig(
        key="Doubao-pro-32k",
        max_tokens=32000,
        TPM=800000,
        RPM=10000,
    )
    DOUBAO_PRO_128K = ModelConfig(
        key="Doubao-pro-128k",
        max_tokens=128000,
        TPM=400000,
        RPM=1000,
    )


class VolcEngineService(OpenaiLLMStyle):
    name = "volcengine"

    def __init__(
            self,
            top_p: float = 0.9,
            temperature: float = 0.3,
            timeout: float = 60.,
    ):
        super().__init__(
            model_enum=VolcEngineModelEnum,
            endpoint="https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            default_model=VolcEngineModelEnum.DOUBAO_LITE_32K.value,
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
        )

    @classmethod
    def set_api_auth(cls, auth: Dict[str, str]):
        s = config.get_settings()
        s.VOLCENGINE_API_KEY = auth.get("API-KEY", "")
        s.VOLCENGINE_ENDPOINT_ID = auth.get("ENDPOINT-ID", "")

    @staticmethod
    def get_api_key():
        return config.get_settings().VOLCENGINE_API_KEY

    def get_payload(self, model: str, messages: MessagesType, stream: bool) -> bytes:
        messages = self._clip_messages(model, messages)
        return json.dumps({
            "model": config.get_settings().VOLCENGINE_ENDPOINT_ID,
            "messages": messages,
            # "max_tokens": 100,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "stream": stream,
            "stream_options": {"include_usage": True}
        }, ensure_ascii=False).encode("utf-8")

    async def stream_complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None
    ) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
        if model is None:
            model = self.default_model.key
        payload = self.get_payload(model, messages, stream=True)
        async for b, code in self._stream_complete(
                url=self.endpoint,
                headers=self.get_headers(),
                payload=payload,
                req_id=req_id
        ):
            if code != const.CodeEnum.OK:
                yield b, code
                continue
            txt = ""
            lines = filter(lambda s: s != b"", b.split("\n\n".encode("utf-8")))
            for line in lines:
                json_str = line.decode("utf-8")[5:].strip()
                try:
                    json_data = json.loads(json_str)
                except json.JSONDecodeError:
                    logger.error(f"rid='{req_id}' | {self.__class__.__name__} {model} | stream error: json={json_str}")
                    continue
                choices = json_data["choices"]
                if len(choices) > 0:
                    choice = json_data["choices"][0]
                    txt += choice["delta"]["content"]
                else:
                    usage = json_data.get("usage", {})
                    logger.info(f"rid='{req_id}' | {self.__class__.__name__} {model} | usage: {usage}")
                    break
            yield txt.encode("utf-8"), code

    async def _batch_complete_union(
            self,
            messages: List[MessagesType],
            func: Callable,
            model: str = None,
            req_id: str = None,
    ) -> List[Tuple[Union[str, Dict[str, str]], const.CodeEnum]]:
        if model is None:
            model = self.default_model.key
        m = self.key2model[model].value
        rate_limiter = ratelimiter.RateLimiter(requests=m.RPM, period=60)

        tasks = [
            func(
                limiters=[rate_limiter],
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
