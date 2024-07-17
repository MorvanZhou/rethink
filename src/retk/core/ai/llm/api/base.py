import asyncio
import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import wraps
from typing import List, Dict, Literal, AsyncIterable, Tuple, Optional, Union

import httpx

from retk import const
from retk.logger import logger

MessagesType = List[Dict[Literal["role", "content"], str]]


@dataclass(frozen=True)
class ModelConfig:
    key: str
    max_tokens: int
    RPM: Optional[int] = None
    TPM: Optional[int] = None


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
            default_model: Optional[ModelConfig] = None,
            concurrency: int = -1,
    ):
        self.top_p = top_p
        self.temperature = temperature
        self.timeout = self.default_timeout if timeout is not None else timeout
        self.default_model: Optional[ModelConfig] = default_model
        self.endpoint = endpoint
        self.concurrency = concurrency

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
        client = httpx.AsyncClient()
        async with client.stream(
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
                await client.aclose()
                return

            async for chunk in resp.aiter_bytes():
                yield chunk, const.CodeEnum.OK
        await client.aclose()

    @abstractmethod
    async def stream_complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None
    ) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
        ...

    @staticmethod
    @abstractmethod
    def get_concurrency() -> int:
        ...


# unless you keep a strong reference to a running task, it can be dropped during execution
# https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
_background_tasks = set()


class RateLimitedClient(httpx.AsyncClient):
    """httpx.AsyncClient with a rate limit."""

    def __init__(
            self,
            interval: Union[dt.timedelta, float],
            count=1,
            **kwargs
    ):
        """
        Parameters
        ----------
        interval : Union[dt.timedelta, float]
            Length of interval.
            If a float is given, seconds are assumed.
        numerator : int, optional
            Number of requests which can be sent in any given interval (default 1).
        """
        if isinstance(interval, dt.timedelta):
            interval = interval.total_seconds()

        self.interval = interval
        self.semaphore = asyncio.Semaphore(count)
        super().__init__(**kwargs)

    def _schedule_semaphore_release(self):
        wait = asyncio.create_task(asyncio.sleep(self.interval))
        _background_tasks.add(wait)

        def wait_cb(task):
            self.semaphore.release()
            _background_tasks.discard(task)

        wait.add_done_callback(wait_cb)

    @wraps(httpx.AsyncClient.send)
    async def send(self, *args, **kwargs):
        await self.semaphore.acquire()
        send = asyncio.create_task(super().send(*args, **kwargs))
        self._schedule_semaphore_release()
        return await send
