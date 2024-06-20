import json
from enum import Enum
from typing import Tuple, AsyncIterable, Optional, Dict

from retk import config, const
from retk.logger import logger
from .base import BaseLLMService, MessagesType, NoAPIKeyError


# https://help.aliyun.com/zh/dashscope/developer-reference/tongyi-thousand-questions-metering-and-billing
class AliyunModelEnum(str, Enum):
    QWEN1_5_05B = "qwen1.5-0.5b-chat"  # free
    QWEN_2B = "qwen-1.8b-chat"  # free
    BAICHUAN7BV1 = "baichuan-7b-v1"  # free
    QWEN_LONG = "qwen-long"  # in 0.0005/1000, out 0.002/1000
    QWEN_TURBO = "qwen-turbo"  # in 0.002/1000, out 0.006/1000
    QWEN_PLUS = "qwen-plus"  # in 0.004/1000, out 0.012/1000
    QWEN_MAX = "qwen-max"  # in 0.04/1000, out 0.12/1000


class AliyunService(BaseLLMService):
    def __init__(
            self,
            top_p: float = 0.9,
            temperature: float = 0.7,
            timeout: float = 60.,
    ):
        super().__init__(
            endpoint="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
            default_model=AliyunModelEnum.QWEN1_5_05B.value,
        )
        self.api_key = config.get_settings().ALIYUN_DASHSCOPE_API_KEY
        if self.api_key == "":
            raise NoAPIKeyError("Aliyun API key is empty")

    def get_headers(self, stream: bool) -> Dict[str, str]:
        h = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }
        if stream:
            h["Accept"] = "text/event-stream"
        return h

    def get_payload(self, model: Optional[str], messages: MessagesType, stream: bool) -> bytes:
        if model is None:
            model = self.default_model
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
        if rj.get("code") is not None:
            logger.error(f"ReqId={req_id} Aliyun model error: code={rj['code']} {rj['message']}")
            return "Aliyun model error, please try later", const.CodeEnum.LLM_SERVICE_ERROR
        logger.info(f"ReqId={req_id} Aliyun model usage: {rj['usage']}")
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
                    logger.error(f"ReqId={req_id} Aliyun model stream error: string={s}")
                    continue
                try:
                    json_data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"ReqId={req_id} Aliyun model stream error: string={s}, error={e}")
                    continue
                choice = json_data["output"]["choices"][0]
                if choice["finish_reason"] != "null":
                    logger.info(f"ReqId={req_id} Aliyun model usage: {json_data['usage']}")
                    break
                txt += choice["message"]["content"]
            yield txt.encode("utf-8"), code
