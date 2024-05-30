import hashlib
import hmac
import json
import time
from datetime import datetime
from enum import Enum
from typing import TypedDict, Tuple, Dict, AsyncIterable, Optional

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


class TencentModelEnum(str, Enum):
    HUNYUAN_PRO = "hunyuan-pro"
    HUNYUAN_STANDARD = "hunyuan-standard"
    HUNYUAN_STANDARD_256K = "hunyuan-standard-256K"
    HUNYUAN_LITE = "hunyuan-lite"


# 计算签名摘要函数
def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


class Tencent(BaseLLM):
    service = "hunyuan"
    host = "hunyuan.tencentcloudapi.com"
    version = "2023-09-01"

    def __init__(
            self,
            top_p: float = 0.9,
            temperature: float = 0.7,
            timeout: float = 60.,
            secret_id: str = None,
            secret_key: str = None,
    ):
        super().__init__(
            endpoint=f"https://{self.host}",
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
            default_model=TencentModelEnum.HUNYUAN_LITE.value,
        )
        self.secret_id = config.get_settings().HUNYUAN_SECRET_ID if secret_id is None else secret_id
        self.secret_key = config.get_settings().HUNYUAN_SECRET_KEY if secret_key is None else secret_key
        if self.secret_id == "" or self.secret_key == "":
            raise ValueError("Tencent secret id or key is empty")

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

    def get_payload(self, model: Optional[str], messages: MessagesType, stream: bool) -> bytes:
        if model is None:
            model = self.default_model
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
        logger.error(f"ReqId={req_id} Tencent model error code={code}, msg={msg}")
        if code == 4001:
            ccode = const.CodeEnum.LLM_TIMEOUT
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
        logger.info(f"ReqId={req_id} Tencent model usage: {resp['Usage']}")
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
            txt = ""
            lines = b.splitlines()
            for line in lines:
                s = line.decode("utf-8").strip()
                if s == "":
                    continue
                try:
                    json_str = s[6:]
                except IndexError:
                    logger.error(f"ReqId={req_id} Tencent model stream error: string={s}")
                    continue
                try:
                    json_data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"ReqId={req_id} Tencent model stream error: string={s}, error={e}")
                    continue
                choice = json_data["Choices"][0]
                if choice["FinishReason"] != "":
                    logger.info(f"ReqId={req_id} Tencent model usage: {json_data['Usage']}")
                    break
                content = choice["Delta"]["Content"]
                txt += content
            yield txt.encode("utf-8"), code
