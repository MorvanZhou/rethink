import json
from enum import Enum
from typing import Optional, Tuple, Dict, AsyncIterable

from retk import config, const
from retk.logger import logger
from .base import BaseLLMService, MessagesType, NoAPIKeyError, ModelConfig


# https://xinghuo.xfyun.cn/sparkapi
# https://www.xfyun.cn/doc/spark/HTTP%E8%B0%83%E7%94%A8%E6%96%87%E6%A1%A3.html#_3-%E8%AF%B7%E6%B1%82%E8%AF%B4%E6%98%8E
class XfYunModelEnum(Enum):
    SPARK40_ULTRA = ModelConfig(
        key="v4.0",
        max_tokens=8192,
    )
    SPARK35_MAX = ModelConfig(
        key="v3.5",
        max_tokens=8192,
    )
    SPARK_PRO = ModelConfig(
        key="v3.1",
        max_tokens=8192,
    )
    SPARK_LITE = ModelConfig(
        key="v1.1",
        max_tokens=8192,
    )


_domain_map = {
    XfYunModelEnum.SPARK40_ULTRA.value.key: "4.0Ultra",
    XfYunModelEnum.SPARK35_MAX.value.key: "generalv3.5",
    XfYunModelEnum.SPARK_PRO.value.key: "generalv3",
    XfYunModelEnum.SPARK_LITE.value.key: "general",
}


class XfYunService(BaseLLMService):
    def __init__(
            self,
            top_p: float = 0.9,
            temperature: float = 0.7,
            timeout: float = 60.,
    ):
        super().__init__(
            endpoint="https://spark-api-open.xf-yun.com/v1/chat/completions",
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
            default_model=XfYunModelEnum.SPARK_LITE.value,
        )

    @staticmethod
    def get_concurrency() -> int:
        return 1

    @staticmethod
    def get_headers() -> Dict:
        _s = config.get_settings()
        if _s.XFYUN_API_KEY == "" or _s.XFYUN_API_SECRET == "":
            raise NoAPIKeyError("XfYun api secret or skey or appID is empty")
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_s.XFYUN_API_KEY}:{_s.XFYUN_API_SECRET}",
        }

    def get_payload(self, model: Optional[str], messages: MessagesType, stream: bool) -> bytes:
        if model is None:
            model = self.default_model.key
        data = {
            "model": _domain_map[model],
            "stream": stream,
            "messages": messages,
            "temperature": self.temperature,
            "top_k": 4,
        }
        return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

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
        if rj["code"] != 0:
            return rj["message"], const.CodeEnum.LLM_SERVICE_ERROR
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
                if json_str == "[DONE]":
                    break
                try:
                    json_data = json.loads(json_str)
                except json.JSONDecodeError:
                    logger.error(f"ReqId={req_id} {self.__class__.__name__} model stream error: json={json_str}")
                    continue
                if json_data["code"] != 0:
                    logger.error(
                        f"ReqId={req_id} {self.__class__.__name__} model error:"
                        f" code={json_data['code']} {json_data['message']}"
                    )
                    break
                choice = json_data["choices"][0]
                try:
                    usage = choice["usage"]
                except KeyError:
                    pass
                else:
                    logger.info(f"ReqId={req_id} {self.__class__.__name__} model usage: {usage}")
                    break
                txt += choice["delta"]["content"]
            yield txt.encode("utf-8"), code
