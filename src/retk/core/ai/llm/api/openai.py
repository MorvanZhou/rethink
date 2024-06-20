import json
from enum import Enum
from typing import Tuple, AsyncIterable, Optional

from retk import config, const
from retk.logger import logger
from .base import BaseLLMService, MessagesType, NoAPIKeyError


class OpenaiModelEnum(str, Enum):
    GPT4 = "gpt-4"
    GPT4_TURBO_PREVIEW = "gpt-4-turbo-preview"
    GPT4_32K = "gpt-4-32k"
    GPT35_TURBO = "gpt-3.5-turbo"
    GPT35_TURBO_16K = "gpt-3.5-turbo-16k"


class OpenaiLLMStyle(BaseLLMService):
    def __init__(
            self,
            api_key: str,
            endpoint: str,
            default_model: str,
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
        self.api_key = api_key
        if self.api_key == "":
            raise NoAPIKeyError(f"{self.__class__.__name__} API key is empty")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def get_payload(self, model: Optional[str], messages: MessagesType, stream: bool) -> bytes:
        if model is None:
            model = self.default_model
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
            headers=self.headers,
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
                headers=self.headers,
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
            api_key=config.get_settings().OPENAI_API_KEY,
            endpoint="https://api.openai.com/v1/chat/completions",
            default_model=OpenaiModelEnum.GPT35_TURBO.value,
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
        )
