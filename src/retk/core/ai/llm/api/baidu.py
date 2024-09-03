import asyncio
import json
from datetime import datetime
from enum import Enum
from typing import Tuple, AsyncIterable, List, Dict, Union, Callable

import httpx

from retk import config, const
from retk.core.utils import ratelimiter
from retk.logger import logger
from .base import BaseLLMService, MessagesType, NoAPIKeyError, ModelConfig


# https://cloud.baidu.com/doc/WENXINWORKSHOP/s/hlrk4akp7#tokens%E7%94%A8%E9%87%8F%E5%90%8E%E4%BB%98%E8%B4%B9
# https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Slkkydake#%E8%AF%A6%E6%83%85
class BaiduModelEnum(Enum):
    ERNIE4_8K = ModelConfig(
        key="completions_pro",
        max_tokens=8000,
        RPM=120,
        TPM=120_000,
    )  # 0.12 / 0.12
    ERNIE4_TURBO_8K = ModelConfig(
        key="ernie-4.0-turbo-8k",
        max_tokens=8000,
        RPM=300,
        TPM=300_000,
    )  # 0.003 / 0.06
    ERNIE35_8K = ModelConfig(
        key="completions",
        max_tokens=8000,
        RPM=300,
        TPM=300_000,
    )  # 0.012 / 0.012
    ERNIE35_128K = ModelConfig(
        key="ernie-3.5-128k",
        max_tokens=128000,
        RPM=100,
        TPM=100_000,
    )  # 0.048 / 0.096
    ERNIE_SPEED_128K = ModelConfig(
        key="ernie-speed-128k",
        max_tokens=128000,
        RPM=6,
        TPM=128_000,
    )  # free
    ERNIE_SPEED_8K = ModelConfig(
        key="ernie_speed",
        max_tokens=8000,
        RPM=300,
        TPM=300_000,
    )  # free
    ERNIE_LITE_8K = ModelConfig(
        key="ernie-lite-8k",
        max_tokens=8000,
        RPM=300,
        TPM=300_000,
    )  # free
    ERNIE_TINY_8K = ModelConfig(
        key="ernie-tiny-8k",
        max_tokens=8000,
        RPM=300,
        TPM=300_000,
    )  # free


class BaiduService(BaseLLMService):
    name = "baidu"

    def __init__(
            self,
            top_p: float = 0.9,
            temperature: float = 0.9,
            timeout: float = 60.,
    ):
        super().__init__(
            endpoint="https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/",
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
            model_enum=BaiduModelEnum,
            default_model=BaiduModelEnum.ERNIE_SPEED_8K.value,
        )

        self.headers = {
            "Content-Type": "application/json",
        }

        self.token_expires_at = datetime.now().timestamp()
        self.token = ""

    @classmethod
    def set_api_auth(cls, auth: Dict[str, str]):
        settings = config.get_settings()
        settings.BAIDU_QIANFAN_API_KEY = auth.get("API-KEY", "")
        settings.BAIDU_QIANFAN_SECRET_KEY = auth.get("Secret Key", "")

    async def set_token(self, req_id: str = None):
        _s = config.get_settings()
        if _s.BAIDU_QIANFAN_API_KEY == "" or _s.BAIDU_QIANFAN_SECRET_KEY == "":
            raise NoAPIKeyError("Baidu api key or skey is empty")

        if self.token_expires_at > datetime.now().timestamp():
            return

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url="https://aip.baidubce.com/oauth/2.0/token",
                headers={"Content-Type": "application/json", 'Accept': 'application/json'},
                content=b"",
                params={
                    "grant_type": "client_credentials",
                    "client_id": _s.BAIDU_QIANFAN_API_KEY,
                    "client_secret": _s.BAIDU_QIANFAN_SECRET_KEY,
                }
            )
        if resp.status_code != 200:
            logger.error(f"rid='{req_id}' | Baidu | error: {resp.text}")
            return ""
        rj = resp.json()
        if rj.get("error") is not None:
            logger.error(f"rid='{req_id}' | Baidu | token error: {rj['error_description']}")
            return ""

        self.token_expires_at = rj["expires_in"] + datetime.now().timestamp()
        self.token = rj["access_token"]

    def get_payload(self, model: str, messages: MessagesType, stream: bool) -> bytes:
        if messages[0]["role"] == "system":
            messages[0]["role"] = "user"
            if messages[1]["role"] == "user":
                messages.insert(1, {"role": "assistant", "content": "明白。"})

        messages = self._clip_messages(model, messages)

        return json.dumps(
            {
                "messages": messages,
                "stream": stream,
            },
            ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

    async def complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None,
    ) -> Tuple[str, const.CodeEnum]:
        if model is None:
            model = self.default_model.key
        payload = self.get_payload(model=model, messages=messages, stream=False)

        await self.set_token()

        resp, code = await self._complete(
            url=self.endpoint + model,
            headers=self.headers,
            payload=payload,
            params={"access_token": self.token},
            req_id=req_id,
        )
        if code != const.CodeEnum.OK:
            return "Model error, please try later", code

        if resp.get("error_code") is not None:
            logger.error(f"rid='{req_id}' | Baidu {model} | error: code={resp['error_code']} {resp['error_msg']}")
            return resp["error_msg"], const.CodeEnum.INVALID_AUTH
        logger.info(f"rid='{req_id}' | Baidu {model} | usage: {resp['usage']}")
        return resp["result"], const.CodeEnum.OK

    async def stream_complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None,
    ) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
        if model is None:
            model = self.default_model.key
        payload = self.get_payload(model=model, messages=messages, stream=True)

        await self.set_token()
        async for b, code in self._stream_complete(
                url=self.endpoint + model,
                headers=self.headers,
                payload=payload,
                params={"access_token": self.token},
                req_id=req_id,
        ):
            if code != const.CodeEnum.OK:
                yield b, code
                continue
            txt = ""
            lines = b.splitlines()
            for line in lines:
                s = line.decode("utf-8").strip()
                if s == "":
                    continue
                try:
                    json_str = s[6:]
                except IndexError:
                    logger.error(f"rid='{req_id}' | Baidu {model} | stream error: string={s}")
                    continue
                try:
                    json_data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"rid='{req_id}' | Baidu {model} | stream error: string={s}, error={e}")
                    continue

                if json_data["is_end"]:
                    logger.info(f"rid='{req_id}' | Baidu {model} | usage: {json_data['usage']}")
                    break
                txt += json_data["result"]
            yield txt.encode("utf-8"), code

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
            m = self.key2model[model].value
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
