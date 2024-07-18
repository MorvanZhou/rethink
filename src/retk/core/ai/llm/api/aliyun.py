import asyncio
import json
from enum import Enum
from typing import Tuple, AsyncIterable, Optional, Dict, List

from retk import config, const
from retk.core.utils import ratelimiter
from retk.logger import logger
from .base import BaseLLMService, MessagesType, NoAPIKeyError, ModelConfig


# https://help.aliyun.com/zh/dashscope/developer-reference/tongyi-thousand-questions-metering-and-billing
class AliyunModelEnum(Enum):
    QWEN1_5_05B = ModelConfig(
        key="qwen1.5-0.5b-chat",
        max_tokens=32000,
    )  # free
    QWEN_2B = ModelConfig(
        key="qwen-1.8b-chat",
        max_tokens=32000,
    )  # free
    QWEN_LONG = ModelConfig(
        key="qwen-long",
        max_tokens=32000,
        RPM=100,
        TPM=1000_000,
    )  # in 0.0005/1000, out 0.002/1000
    QWEN_TURBO = ModelConfig(
        key="qwen-turbo",
        max_tokens=8000,
        RPM=500,
        TPM=500_000,
    )  # in 0.002/1000, out 0.006/1000
    QWEN_PLUS = ModelConfig(
        key="qwen-plus",
        max_tokens=32000,
        RPM=200,
        TPM=200_000,
    )  # in 0.004/1000, out 0.012/1000
    QWEN_MAX = ModelConfig(
        key="qwen-max",
        max_tokens=8000,
        RPM=60,
        TPM=100_000,
    )  # in 0.04/1000, out 0.12/1000
    QWEN_MAX_LONG_CONTEXT = ModelConfig(
        key="qwen-max-longcontext",
        max_tokens=32000,
        RPM=5,
        TPM=1500_000,
    )


_key2model: Dict[str, AliyunModelEnum] = {m.value.key: m for m in AliyunModelEnum}


class AliyunService(BaseLLMService):
    name = "ali"

    def __init__(
            self,
            top_p: float = 0.9,
            temperature: float = 0.4,
            timeout: float = 60.,
    ):
        super().__init__(
            endpoint="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
            default_model=AliyunModelEnum.QWEN1_5_05B.value,
        )
        self.concurrency = 5

    @staticmethod
    def get_headers(stream: bool) -> Dict[str, str]:
        k = config.get_settings().ALIYUN_DASHSCOPE_API_KEY
        if k == "":
            raise NoAPIKeyError("Aliyun API key is empty")
        h = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {k}',
        }
        if stream:
            h["Accept"] = "text/event-stream"
        return h

    def get_payload(self, model: Optional[str], messages: MessagesType, stream: bool) -> bytes:
        if model is None:
            model = self.default_model.key
        return json.dumps({
            'model': model,
            "input": {
                "messages": messages,
            },
            "top_p": self.top_p,
            "temperature": self.temperature,
            "stream": stream,
            "parameters": {
                "incremental_output": stream,
                "result_format": "message",
            },
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
            headers=self.get_headers(stream=False),
            payload=payload,
            req_id=req_id,
        )
        if code != const.CodeEnum.OK:
            return "Aliyun model error, please try later", code
        rcode = rj.get("code")
        if rcode is not None:
            logger.error(f"ReqId={req_id} | Aliyun {model} | error: code={rj['code']} {rj['message']}")
            if rcode == "Throttling.RateQuota":
                return "Aliyun model rate limit exceeded", const.CodeEnum.LLM_API_LIMIT_EXCEEDED
            return "Aliyun model error, please try later", const.CodeEnum.LLM_SERVICE_ERROR

        logger.info(f"ReqId={req_id} | Aliyun {model} | usage: {rj['usage']}")
        return rj["output"]["choices"][0]["message"]["content"], const.CodeEnum.OK

    async def stream_complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None
    ) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
        payload = self.get_payload(model, messages, stream=True)
        async for b, code in self._stream_complete(
                url=self.endpoint,
                headers=self.get_headers(stream=True),
                payload=payload,
                req_id=req_id
        ):
            if code != const.CodeEnum.OK:
                yield b, code
                continue
            txt = ""
            lines = b.splitlines()
            for line in lines:
                s = line.decode("utf-8").strip()
                if s == "" or not s.startswith("data:"):
                    continue
                try:
                    json_str = s[5:]
                except IndexError:
                    logger.error(f"ReqId={req_id} | Aliyun {model} | stream error: string={s}")
                    continue
                try:
                    json_data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"ReqId={req_id} | Aliyun {model} | stream error: string={s}, error={e}")
                    continue
                choice = json_data["output"]["choices"][0]
                if choice["finish_reason"] != "null":
                    logger.info(f"ReqId={req_id} | Aliyun {model} | usage: {json_data['usage']}")
                    break
                txt += choice["message"]["content"]
            yield txt.encode("utf-8"), code

    async def batch_complete(
            self,
            messages: List[MessagesType],
            model: str = None,
            req_id: str = None,
    ) -> List[Tuple[str, const.CodeEnum]]:
        if model is None:
            m = self.default_model
        else:
            m = _key2model[model].value
        concurrent_limiter = ratelimiter.ConcurrentLimiter(n=self.concurrency)
        rate_limiter = ratelimiter.RateLimiter(requests=m.RPM, period=60)

        tasks = [
            self._batch_complete(
                limiters=[concurrent_limiter, rate_limiter],
                messages=m,
                model=model,
                req_id=req_id,
            ) for m in messages
        ]
        return await asyncio.gather(*tasks)
