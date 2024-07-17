import json
from datetime import datetime
from enum import Enum
from typing import Tuple, AsyncIterable

import httpx

from retk import config, const
from retk.logger import logger
from .base import BaseLLMService, MessagesType, NoAPIKeyError, ModelConfig


# https://cloud.baidu.com/doc/WENXINWORKSHOP/s/hlrk4akp7#tokens%E7%94%A8%E9%87%8F%E5%90%8E%E4%BB%98%E8%B4%B9
class BaiduModelEnum(Enum):
    ERNIE4_8K = ModelConfig(
        key="completions_pro",
        max_tokens=8000,
        RPM=120,
        TPM=120_000,
    )  # 0.12 / 0.12
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
    def __init__(
            self,
            top_p: float = 0.9,
            temperature: float = 0.7,
            timeout: float = 60.,
    ):
        super().__init__(
            endpoint="https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/",
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
            default_model=BaiduModelEnum.ERNIE_SPEED_8K.value,
        )
        self.headers = {
            "Content-Type": "application/json",
        }

        self.token_expires_at = datetime.now().timestamp()
        self.token = ""

    @staticmethod
    def get_concurrency() -> int:
        return 9999

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
            logger.error(f"ReqId={req_id} Baidu model error: {resp.text}")
            return ""
        rj = resp.json()
        if rj.get("error") is not None:
            logger.error(f"ReqId={req_id} Baidu model token error: {rj['error_description']}")
            return ""

        self.token_expires_at = rj["expires_in"] + datetime.now().timestamp()
        self.token = rj["access_token"]

    @staticmethod
    def get_payload(messages: MessagesType, stream: bool) -> bytes:
        if messages[0]["role"] == "system":
            messages[0]["role"] = "user"
            if messages[1]["role"] == "user":
                messages.insert(1, {"role": "assistant", "content": "明白。"})
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
        payload = self.get_payload(messages=messages, stream=False)

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
            logger.error(f"ReqId={req_id} Baidu model error: code={resp['error_code']} {resp['error_msg']}")
            return resp["error_msg"], const.CodeEnum.LLM_SERVICE_ERROR
        logger.info(f"ReqId={req_id} Baidu model usage: {resp['usage']}")
        return resp["result"], const.CodeEnum.OK

    async def stream_complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None,
    ) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
        if model is None:
            model = self.default_model.key
        payload = self.get_payload(messages=messages, stream=True)

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
                    logger.error(f"ReqId={req_id} Baidu model stream error: string={s}")
                    continue
                try:
                    json_data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"ReqId={req_id} Baidu model stream error: string={s}, error={e}")
                    continue

                if json_data["is_end"]:
                    logger.info(f"ReqId={req_id} Baidu model usage: {json_data['usage']}")
                    break
                txt += json_data["result"]
            yield txt.encode("utf-8"), code
