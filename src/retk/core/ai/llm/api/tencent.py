import asyncio
import hashlib
import hmac
import json
import time
from enum import Enum
from typing import TypedDict, Tuple, Dict, AsyncIterable, Optional, List, Callable, Union

from retk import config, const
from retk.core.utils import ratelimiter, tencent
from retk.logger import logger
from .base import BaseLLMService, MessagesType, NoAPIKeyError, ModelConfig

Headers = TypedDict("Headers", {
    "Authorization": str,
    "Content-Type": str,
    "Host": str,
    "X-TC-Action": str,
    "X-TC-Timestamp": str,
    "X-TC-Version": str,
    "X-TC-Language": str,
})


# https://cloud.tencent.com/document/product/1729/97731
class TencentModelEnum(Enum):
    HUNYUAN_PRO = ModelConfig(
        key="hunyuan-pro",
        max_tokens=32000,
    )  # in 0.03/1000, out 0.10/1000
    HUNYUAN_STANDARD = ModelConfig(
        key="hunyuan-standard",
        max_tokens=32000,
    )  # in 0.0045/1000, out 0.005/1000
    HUNYUAN_STANDARD_256K = ModelConfig(
        key="hunyuan-standard-256K",
        max_tokens=256000,
    )  # in 0.015/1000, out 0.06/1000
    HUNYUAN_LITE = ModelConfig(
        key="hunyuan-lite",
        max_tokens=256000,
    )  # free


# 计算签名摘要函数
def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


class TencentService(BaseLLMService):
    name = "tencent"
    service = "hunyuan"
    host = "hunyuan.tencentcloudapi.com"
    version = "2023-09-01"
    concurrency = 5

    def __init__(
            self,
            top_p: float = 0.9,
            temperature: float = 0.9,
            timeout: float = 60.,
    ):
        super().__init__(
            model_enum=TencentModelEnum,
            endpoint=f"https://{self.host}",
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
            default_model=TencentModelEnum.HUNYUAN_LITE.value,
        )

    @classmethod
    def set_api_auth(cls, auth: Dict[str, str]):
        settings = config.get_settings()
        settings.HUNYUAN_SECRET_ID = auth.get("Secret Id", "")
        settings.HUNYUAN_SECRET_KEY = auth.get("Secret Key", "")

    def get_headers(self, action: str, payload: bytes) -> Headers:
        ct = "application/json"
        timestamp = int(time.time())
        _s = config.get_settings()
        if _s.HUNYUAN_SECRET_KEY == "" or _s.HUNYUAN_SECRET_ID == "":
            raise NoAPIKeyError("Tencent secret id or key is empty")
        authorization = tencent.get_auth(
            host=self.host,
            service=self.service,
            secret_id=_s.HUNYUAN_SECRET_ID,
            secret_key=_s.HUNYUAN_SECRET_KEY,
            action=action,
            payload=payload,
            timestamp=timestamp,
            content_type=ct,
        )
        return {
            "Authorization": authorization,
            "Host": self.host,
            "X-TC-Action": action,
            "X-TC-Version": self.version,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Language": "zh-CN",
            "Content-Type": ct,
        }

    def get_payload(self, model: Optional[str], messages: MessagesType, stream: bool) -> bytes:
        if model is None:
            model = self.default_model.key

        messages = self._clip_messages(model, messages)
        return json.dumps(
            {
                "Model": model,
                "Messages": [{"Role": m["role"], "Content": m["content"]} for m in messages],
                "Stream": stream,
                "TopP": self.top_p,
                "Temperature": self.temperature,
                "EnableEnhancement": False,
            },
            ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

    @staticmethod
    def handle_err(req_id: str, error: Dict):
        msg = error.get("Message")
        code = error.get("Code")
        logger.error(f"rid='{req_id}' | Tencent | error code={code}, msg={msg}")
        if code == 4001:
            ccode = const.CodeEnum.LLM_TIMEOUT
        elif code == "LimitExceeded":
            ccode = const.CodeEnum.LLM_API_LIMIT_EXCEEDED
        elif code == 'AuthFailure.SecretIdNotFound':
            ccode = const.CodeEnum.INVALID_AUTH
        elif code == 'AuthFailure.SignatureFailure':
            ccode = const.CodeEnum.INVALID_AUTH
        else:
            ccode = const.CodeEnum.LLM_SERVICE_ERROR
        return msg, ccode

    @staticmethod
    def handle_normal_response(req_id: str, resp: Dict, stream: bool) -> Tuple[str, const.CodeEnum]:
        choices = resp["Choices"]
        if len(choices) == 0:
            return "No response", const.CodeEnum.LLM_NO_CHOICE
        choice = choices[0]
        m = choice["Delta"] if stream else choice["Message"]
        logger.info(f"rid='{req_id}' | Tencent | usage: {resp['Usage']}")
        return m["Content"], const.CodeEnum.OK

    async def complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None,
    ) -> Tuple[str, const.CodeEnum]:
        action = "ChatCompletions"
        payload = self.get_payload(model=model, messages=messages, stream=False)
        headers = self.get_headers(action=action, payload=payload)

        rj, code = await self._complete(
            url=self.endpoint,
            headers=headers,
            payload=payload,
            req_id=req_id,
        )
        if code != const.CodeEnum.OK:
            return "Model error, please try later", code

        resp = rj["Response"]
        error = resp.get("Error")
        if error is not None:
            return self.handle_err(req_id, error)

        return self.handle_normal_response(req_id=req_id, resp=resp, stream=False)

    async def stream_complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None
    ) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
        action = "ChatCompletions"
        payload = self.get_payload(model=model, messages=messages, stream=True)
        headers = self.get_headers(action=action, payload=payload)

        async for b, code in self._stream_complete(
                url=self.endpoint,
                headers=headers,
                payload=payload,
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
                    logger.error(f"rid='{req_id}' | Tencent {model} | stream error: string={s}")
                    continue
                try:
                    json_data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"rid='{req_id}' | Tencent {model} | stream error: string={s}, error={e}")
                    continue
                choice = json_data["Choices"][0]
                if choice["FinishReason"] != "":
                    logger.info(f"rid='{req_id}' | Tencent {model} | usage: {json_data['Usage']}")
                    break
                content = choice["Delta"]["Content"]
                txt += content
            yield txt.encode("utf-8"), code

    async def _batch_complete_union(
            self,
            messages: List[MessagesType],
            func: Callable,
            model: str = None,
            req_id: str = None,
    ) -> List[Tuple[Union[str, Dict[str, str]], const.CodeEnum]]:
        limiter = ratelimiter.ConcurrentLimiter(n=self.concurrency)

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
