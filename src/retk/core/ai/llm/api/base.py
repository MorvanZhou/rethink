from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    List, Dict, Literal, AsyncIterable, Tuple, Optional, Union, Any
)

import httpx

from retk import const
from retk.core.utils import ratelimiter
from retk.logger import logger
from ..utils import parse_json_pattern

MessagesType = List[Dict[Literal["role", "content"], str]]


@dataclass(frozen=True)
class ModelConfig:
    key: str
    max_tokens: int
    RPM: int = field(default=999999)
    RPD: int = field(default=9999999999)
    TPM: int = field(default=9999999999)


class NoAPIKeyError(Exception):
    pass


class BaseLLMService(ABC):
    name: str
    default_timeout = 60.

    def __init__(
            self,
            model_enum: Any,
            endpoint: str,
            top_p: float = 1.,
            temperature: float = 0.4,
            timeout: float = None,
            default_model: Optional[ModelConfig] = None,
    ):
        if self.name is None:
            raise ValueError("name should be set")

        self.top_p = top_p
        self.temperature = temperature
        self.timeout = self.default_timeout if timeout is not None else timeout
        self.default_model: Optional[ModelConfig] = default_model
        self.endpoint = endpoint
        self.key2model = {m.value.key: m for m in model_enum}

    @classmethod
    @abstractmethod
    def set_api_auth(cls, auth: Dict[str, str]):
        ...

    def _clip_messages(self, model: str, messages: MessagesType) -> MessagesType:
        # clip the last message if it's too long
        max_tokens = self.key2model[model].value.max_tokens
        max_char = max(0, int(1.5 * max_tokens - 2000))
        if len(messages[-1]["content"]) > max_char:
            logger.warning(f"Message too long, clipping to {max_char} characters")
            messages[-1]["content"] = messages[-1]["content"][:max_char]
        return messages

    async def _complete(
            self,
            url: str,
            headers: Dict[str, str],
            payload: bytes,
            params: Dict[str, str] = None,
            req_id: str = None,
    ) -> Tuple[Dict, const.CodeEnum]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url=url,
                    headers=headers,
                    content=payload,
                    params=params,
                    follow_redirects=False,
                    timeout=self.timeout,
                )
        except (
                httpx.ConnectTimeout,
                httpx.ConnectError,
                httpx.ReadTimeout,
        ) as e:
            logger.error(f"rid='{req_id}' Model error: {e}")
            return {}, const.CodeEnum.LLM_TIMEOUT
        except httpx.HTTPError as e:
            logger.error(f"rid='{req_id}' Model error: {e}")
            return {}, const.CodeEnum.LLM_SERVICE_ERROR
        if resp.status_code != 200:
            txt = resp.text.replace('\n', '')
            logger.error(f"rid='{req_id}' Model error: {txt}")
            if resp.status_code in [401, 403]:
                code = const.CodeEnum.INVALID_AUTH
            else:
                code = const.CodeEnum.LLM_SERVICE_ERROR
            return {}, code

        rj = resp.json()
        return rj, const.CodeEnum.OK

    @abstractmethod
    async def complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None,
    ) -> Tuple[str, const.CodeEnum]:
        ...

    async def _stream_complete(
            self,
            url: str,
            headers: Dict[str, str],
            payload: bytes,
            method: str = "POST",
            params: Dict[str, str] = None,
            req_id: str = None,
    ) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
        client = httpx.AsyncClient()
        try:
            async with client.stream(
                    method=method,
                    url=url,
                    headers=headers,
                    content=payload,
                    params=params,
                    follow_redirects=False,
                    timeout=self.timeout,
            ) as resp:
                if resp.status_code != 200:
                    await resp.aread()
                    logger.error(f"rid='{req_id}' Model error: {resp.text}")
                    yield resp.content, const.CodeEnum.LLM_SERVICE_ERROR
                    await client.aclose()
                    return

                async for chunk in resp.aiter_bytes():
                    yield chunk, const.CodeEnum.OK
        except (
                httpx.ConnectTimeout,
                httpx.ConnectError,
                httpx.ReadTimeout,
        ) as e:
            logger.error(f"rid='{req_id}' Model error: {e}")
            yield b"", const.CodeEnum.LLM_TIMEOUT
        await client.aclose()

    async def _batch_complete(
            self,
            limiters: List[Union[ratelimiter.RateLimiter, ratelimiter.ConcurrentLimiter]],
            messages: MessagesType,
            model: str = None,
            req_id: str = None,
    ) -> Tuple[str, const.CodeEnum]:
        if len(limiters) == 4:
            async with limiters[0], limiters[1], limiters[2], limiters[3]:
                return await self.complete(messages=messages, model=model, req_id=req_id)
        elif len(limiters) == 3:
            async with limiters[0], limiters[1], limiters[2]:
                return await self.complete(messages=messages, model=model, req_id=req_id)
        elif len(limiters) == 2:
            async with limiters[0], limiters[1]:
                return await self.complete(messages=messages, model=model, req_id=req_id)
        elif len(limiters) == 1:
            async with limiters[0]:
                return await self.complete(messages=messages, model=model, req_id=req_id)
        else:
            raise ValueError("Invalid number of limiters, should less than 4")

    async def _batch_stream_complete_json_detect(
            self,
            limiters: List[Union[ratelimiter.RateLimiter, ratelimiter.ConcurrentLimiter]],
            messages: MessagesType,
            model: str = None,
            req_id: str = None,
    ) -> Tuple[Optional[Dict[str, str]], const.CodeEnum]:
        if len(limiters) == 4:
            async with limiters[0], limiters[1], limiters[2], limiters[3]:
                return await self.stream_complete_json_detect(messages=messages, model=model, req_id=req_id)
        elif len(limiters) == 3:
            async with limiters[0], limiters[1], limiters[2]:
                return await self.stream_complete_json_detect(messages=messages, model=model, req_id=req_id)
        elif len(limiters) == 2:
            async with limiters[0], limiters[1]:
                return await self.stream_complete_json_detect(messages=messages, model=model, req_id=req_id)
        elif len(limiters) == 1:
            async with limiters[0]:
                return await self.stream_complete_json_detect(messages=messages, model=model, req_id=req_id)
        else:
            raise ValueError("Invalid number of limiters, should less than 4")

    async def stream_complete_json_detect(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None,
    ) -> Tuple[Dict[str, str], const.CodeEnum]:
        chunks: List[bytes] = []
        chunks_append = chunks.append

        async for b, code in self.stream_complete(
                messages=messages,
                model=model,
                req_id=req_id,
        ):
            if code != const.CodeEnum.OK:
                logger.error(f"rid='{req_id}' | Model error: {code}")
                return {}, code

            chunks_append(b)
            if b"}" in b:
                text_bytes = b"".join(chunks)
                text = text_bytes.decode("utf-8")
                try:
                    d = parse_json_pattern(text)
                    return d, const.CodeEnum.OK
                except ValueError:
                    continue
        oneline = (b"".join(chunks).decode("utf-8")).replace("\n", "\\n")
        logger.error(f"rid='{req_id}' | {self.__class__.__name__} {model} | error: No JSON pattern found | {oneline}")
        return {}, const.CodeEnum.LLM_INVALID_RESPONSE_FORMAT

    @abstractmethod
    async def stream_complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None
    ) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
        ...

    @abstractmethod
    async def batch_complete(
            self,
            messages: List[MessagesType],
            model: str = None,
            req_id: str = None,
    ) -> List[Tuple[str, const.CodeEnum]]:
        ...

    @abstractmethod
    async def batch_complete_json_detect(
            self,
            messages: List[MessagesType],
            model: str = None,
            req_id: str = None,
    ) -> List[Tuple[Dict[str, str], const.CodeEnum]]:
        ...
