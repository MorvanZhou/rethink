from abc import ABC, abstractmethod
from typing import List, Dict, Literal, AsyncIterable, Tuple

import httpx

from retk import const, httpx_helper
from retk.logger import logger

MessagesType = List[Dict[Literal["role", "content"], str]]


class NoAPIKeyError(Exception):
    pass


class BaseLLMService(ABC):
    default_timeout = 60.

    def __init__(
            self,
            endpoint: str,
            top_p: float = 1.,
            temperature: float = 1.,
            timeout: float = None,
            default_model: str = None
    ):
        self.top_p = top_p
        self.temperature = temperature
        self.timeout = self.default_timeout if timeout is not None else timeout
        self.default_model = default_model
        self.endpoint = endpoint

    async def _complete(
            self,
            url: str,
            headers: Dict[str, str],
            payload: bytes,
            params: Dict[str, str] = None,
            req_id: str = None,
    ) -> Tuple[Dict, const.CodeEnum]:
        try:
            resp = await httpx_helper.get_async_client().post(
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
            logger.error(f"ReqId={req_id} Model error: {e}")
            return {}, const.CodeEnum.LLM_TIMEOUT
        except httpx.HTTPError as e:
            logger.error(f"ReqId={req_id} Model error: {e}")
            return {}, const.CodeEnum.LLM_SERVICE_ERROR
        if resp.status_code != 200:
            txt = resp.text.replace('\n', '')
            logger.error(f"ReqId={req_id} Model error: {txt}")
            return {}, const.CodeEnum.LLM_SERVICE_ERROR

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
            params: Dict[str, str] = None,
            req_id: str = None,
    ) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
        async with httpx_helper.get_async_client().stream(
                method="POST",
                url=url,
                headers=headers,
                content=payload,
                params=params,
                follow_redirects=False,
                timeout=self.timeout,
        ) as resp:
            if resp.status_code != 200:
                await resp.aread()
                logger.error(f"ReqId={req_id} Model error: {resp.text}")
                yield resp.content, const.CodeEnum.LLM_SERVICE_ERROR
                return

            async for chunk in resp.aiter_bytes():
                yield chunk, const.CodeEnum.OK

    @abstractmethod
    async def stream_complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None
    ) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
        ...
