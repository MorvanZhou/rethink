import hashlib
import hmac
import json
import time
from abc import ABC
from datetime import datetime
from typing import TypedDict, Tuple, Dict, AsyncIterable

import httpx

from retk import config, const
from retk.logger import logger
from .base import BaseLLM, MessagesType

Headers = TypedDict("Headers", {
    "Authorization": str,
    "Content-Type": str,
    "Host": str,
    "X-TC-Action": str,
    "X-TC-Timestamp": str,
    "X-TC-Version": str,
    "X-TC-Language": str,
})


# 计算签名摘要函数
def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


class _Hunyuan(BaseLLM, ABC):
    service = "hunyuan"
    host = "hunyuan.tencentcloudapi.com"
    version = "2023-09-01"
    endpoint = f"https://{host}"

    def __init__(
            self,
            name: str,
            top_p: float = 0.9,
            temperature: float = 0.7,
            timeout: float = 60.,
    ):
        self.name = name
        super().__init__()
        self.top_p = top_p
        self.temperature = temperature
        self.timeout = timeout

        self.secret_id = config.get_settings().HUNYUAN_SECRET_ID
        self.secret_key = config.get_settings().HUNYUAN_SECRET_KEY

    def get_auth(self, action: str, payload: bytes, timestamp: int, content_type: str) -> str:
        algorithm = "TC3-HMAC-SHA256"
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")

        # ************* 步骤 1：拼接规范请求串 *************
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        canonical_headers = f"content-type:{content_type}\nhost:{self.host}\nx-tc-action:{action.lower()}\n"
        signed_headers = "content-type;host;x-tc-action"
        hashed_request_payload = hashlib.sha256(payload).hexdigest()
        canonical_request = f"{http_request_method}\n" \
                            f"{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n" \
                            f"{signed_headers}\n{hashed_request_payload}"

        # ************* 步骤 2：拼接待签名字符串 *************
        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"

        # ************* 步骤 3：计算签名 *************
        secret_date = sign(f"TC3{self.secret_key}".encode("utf-8"), date)
        secret_service = sign(secret_date, self.service)
        secret_signing = sign(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        # ************* 步骤 4：拼接 Authorization *************
        authorization = f"{algorithm}" \
                        f" Credential={self.secret_id}/{credential_scope}," \
                        f" SignedHeaders={signed_headers}," \
                        f" Signature={signature}"
        return authorization

    def get_headers(self, action: str, payload: bytes) -> Headers:
        ct = "application/json"
        timestamp = int(time.time())
        authorization = self.get_auth(action=action, payload=payload, timestamp=timestamp, content_type=ct)
        return {
            "Authorization": authorization,
            "Host": self.host,
            "X-TC-Action": action,
            "X-TC-Version": self.version,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Language": "zh-CN",
            "Content-Type": ct,
        }

    def get_payload(self, messages: MessagesType, stream: bool) -> bytes:
        return json.dumps(
            {
                "Model": self.name,
                "Messages": messages,
                "Stream": stream,
                "TopP": self.top_p,
                "Temperature": self.temperature,
                "EnableEnhancement": False,
            }, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

    @staticmethod
    def handle_err(error: Dict):
        msg = error.get("Message")
        code = error.get("Code")
        logger.error(f"Model error code={code}, msg={msg}")
        if code == 4001:
            ccode = const.CodeEnum.LLM_TIMEOUT
        else:
            ccode = const.CodeEnum.LLM_SERVICE_ERROR
        return msg, ccode

    @staticmethod
    def handle_normal_response(rj: Dict, stream: bool) -> Tuple[str, const.CodeEnum]:
        choices = rj["Choices"]
        if len(choices) == 0:
            return "No response", const.CodeEnum.LLM_NO_CHOICE
        choice = choices[0]
        m = choice["Delta"] if stream else choice["Message"]
        return m["Content"], const.CodeEnum.OK

    async def complete(self, messages: MessagesType) -> Tuple[str, const.CodeEnum]:
        action = "ChatCompletions"
        payload = self.get_payload(messages=messages, stream=False)
        headers = self.get_headers(action=action, payload=payload)

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    url=self.endpoint,
                    headers=headers,
                    content=payload,
                    follow_redirects=False,
                    timeout=self.timeout,
                )
            except (
                    httpx.ConnectTimeout,
                    httpx.ConnectError,
                    httpx.ReadTimeout,
            ) as e:
                logger.error(f"Model error: {e}")
                return "Model timeout, please try later", const.CodeEnum.LLM_TIMEOUT
            except httpx.HTTPError as e:
                logger.error(f"Model error: {e}")
                return "Model error, please try later", const.CodeEnum.LLM_SERVICE_ERROR
            if resp.status_code != 200:
                logger.error(f"Model error: {resp.text}")
                return "Model error, please try later", const.CodeEnum.LLM_SERVICE_ERROR

            rj = resp.json()["Response"]
            error = rj.get("Error")
            if error is not None:
                return self.handle_err(error)
            return self.handle_normal_response(rj=rj, stream=False)

    async def stream_complete(self, messages: MessagesType) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
        action = "ChatCompletions"
        payload = self.get_payload(messages=messages, stream=True)
        headers = self.get_headers(action=action, payload=payload)

        async with httpx.AsyncClient() as client:
            async with client.stream(
                    method="POST",
                    url=self.endpoint,
                    headers=headers,
                    content=payload,
                    follow_redirects=False,
                    timeout=self.timeout,
            ) as resp:
                if resp.status_code != 200:
                    logger.error(f"Model error: {resp.text}")
                    yield "Model error, please try later", const.CodeEnum.LLM_SERVICE_ERROR
                    return

                async for chunk in resp.aiter_bytes():
                    yield chunk, const.CodeEnum.OK


class HunyuanPro(_Hunyuan):
    model_name = "hunyuan-pro"

    def __init__(self, top_p: float = 0.9, temperature: float = 0.7):
        super().__init__(name=self.model_name, top_p=top_p, temperature=temperature)


class HunyuanStandard(_Hunyuan):
    model_name = "hunyuan-standard"

    def __init__(self, top_p: float = 0.9, temperature: float = 0.7):
        super().__init__(name=self.model_name, top_p=top_p, temperature=temperature)


class HunyuanStandard256K(_Hunyuan):
    model_name = "hunyuan-standard-256K"

    def __init__(self, top_p: float = 0.9, temperature: float = 0.7):
        super().__init__(name=self.model_name, top_p=top_p, temperature=temperature)


class HunyuanLite(_Hunyuan):
    model_name = "hunyuan-lite"

    def __init__(self, top_p: float = 0.9, temperature: float = 0.7):
        super().__init__(name=self.model_name, top_p=top_p, temperature=temperature)
