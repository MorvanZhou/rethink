import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import Tuple, AsyncIterable, Optional

from retk import config, const
from retk.logger import logger
from .base import BaseLLMService, MessagesType, NoAPIKeyError, ModelConfig


# https://openai.com/api/pricing/
class OpenaiModelEnum(Enum):
    GPT4 = ModelConfig(
        key="gpt-4",
        max_tokens=8192,
    )
    GPT4_TURBO = ModelConfig(
        key="gpt-4-turbo",
        max_tokens=128000,
    )
    GPT4_32K = ModelConfig(
        key="gpt-4-32k",
        max_tokens=32000,
    )
    GPT35_TURBO = ModelConfig(
        key="gpt-3.5-turbo",
        max_tokens=16385,
    )


class OpenaiLLMStyle(BaseLLMService, ABC):
    def __init__(
            self,
            endpoint: str,
            default_model: ModelConfig,
            top_p: float = 0.9,
            temperature: float = 0.7,
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

    def get_payload(self, model: Optional[str], messages: MessagesType, stream: bool) -> bytes:
        if model is None:
            model = self.default_model.key
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
        logger.info(f"ReqId={req_id} {self.__class__.__name__} model usage: {rj['usage']}")
        return rj["choices"][0]["message"]["content"], code

    async def stream_complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None
    ) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
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
                    logger.error(f"ReqId={req_id} {self.__class__.__name__} model stream error: json={json_str}")
                    continue
                choice = json_data["choices"][0]
                if choice["finish_reason"] is not None:
                    try:
                        usage = json_data["usage"]
                    except KeyError:
                        usage = choice["usage"]
                    logger.info(f"ReqId={req_id} {self.__class__.__name__} model usage: {usage}")
                    break
                txt += choice["delta"]["content"]
            yield txt.encode("utf-8"), code


class OpenaiService(OpenaiLLMStyle):
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

    @staticmethod
    def get_api_key():
        return config.get_settings().OPENAI_API_KEY

    @staticmethod
    def get_concurrency():
        return 1
