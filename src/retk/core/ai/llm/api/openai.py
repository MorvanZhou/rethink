import asyncio
import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import Tuple, AsyncIterable, List, Dict, Callable, Union

from retk import config, const
from retk.core.utils import ratelimiter
from retk.logger import logger
from .base import BaseLLMService, MessagesType, NoAPIKeyError, ModelConfig


# https://openai.com/api/pricing/
class OpenaiModelEnum(Enum):
    GPT4 = ModelConfig(
        key="gpt-4",
        max_tokens=8_192,
        RPM=500,  # tier 1
    )
    GPT4_TURBO = ModelConfig(
        key="gpt-4-turbo",
        max_tokens=128_000,
        RPM=500,  # tier 1
    )
    GPT4_32K = ModelConfig(
        key="gpt-4-32k",
        max_tokens=32_000,
        RPM=500,  # tier 1
    )
    GPT35_TURBO = ModelConfig(
        key="gpt-3.5-turbo",
        max_tokens=16_385,
        RPM=3,  # free, other tiers are different
        # https://platform.openai.com/docs/guides/rate-limits/usage-tiers?context=tier-free
        RPD=200,  # free
    )


_key2model: Dict[str, OpenaiModelEnum] = {m.value.key: m for m in OpenaiModelEnum}


class OpenaiLLMStyle(BaseLLMService, ABC):
    def __init__(
            self,
            endpoint: str,
            default_model: ModelConfig,
            top_p: float = 0.9,
            temperature: float = 0.4,
            timeout: float = 60.,
    ):
        super().__init__(
            endpoint=endpoint,
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
            default_model=default_model,
        )

    @staticmethod
    @abstractmethod
    def get_api_key():
        pass

    def get_headers(self):
        k = self.get_api_key()
        if k == "":
            raise NoAPIKeyError(f"{self.__class__.__name__} api key is empty")

        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {k}",
        }

    def get_payload(self, model: str, messages: MessagesType, stream: bool) -> bytes:
        return json.dumps({
            "model": model,
            "messages": messages,
            # "max_tokens": 100,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "stream": stream,
        }, ensure_ascii=False).encode("utf-8")

    async def complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None,
    ) -> Tuple[str, const.CodeEnum]:
        if model is None:
            model = self.default_model.key
        payload = self.get_payload(model, messages, stream=False)
        rj, code = await self._complete(
            url=self.endpoint,
            headers=self.get_headers(),
            payload=payload,
            req_id=req_id,
        )
        if code != const.CodeEnum.OK:
            return "", code
        if rj.get("error") is not None:
            return rj["error"]["message"], const.CodeEnum.LLM_SERVICE_ERROR
        logger.info(f"rid='{req_id}' | {self.__class__.__name__} {model} | usage: {rj['usage']}")
        return rj["choices"][0]["message"]["content"], code

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
                choice = json_data["choices"][0]
                if choice["finish_reason"] is not None:
                    try:
                        usage = json_data["usage"]
                    except KeyError:
                        usage = choice["usage"]
                    logger.info(f"rid='{req_id}' | {self.__class__.__name__} {model} | usage: {usage}")
                    break
                txt += choice["delta"]["content"]
            yield txt.encode("utf-8"), code


class OpenaiService(OpenaiLLMStyle):
    name = "openai"

    def __init__(
            self,
            top_p: float = 0.9,
            temperature: float = 0.7,
            timeout: float = 60.,
    ):
        super().__init__(
            endpoint="https://api.openai.com/v1/chat/completions",
            default_model=OpenaiModelEnum.GPT35_TURBO.value,
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
        )

    @classmethod
    def set_api_auth(cls, auth: Dict[str, str]):
        config.get_settings().OPENAI_API_KEY = auth.get("API-KEY", "")

    @staticmethod
    def get_api_key():
        return config.get_settings().OPENAI_API_KEY

    async def _batch_complete_union(
            self,
            messages: List[MessagesType],
            func: Callable,
            model: str = None,
            req_id: str = None,
    ) -> List[Tuple[Union[str, Dict[str, str]], const.CodeEnum]]:
        if model is None:
            m = self.default_model
        else:
            m = _key2model[model].value
        limiter = ratelimiter.RateLimiter(requests=m.RPM, period=60)

        tasks = [
            func(
                limiters=[limiter],
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
