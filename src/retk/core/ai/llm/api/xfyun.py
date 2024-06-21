import base64
import hashlib
import hmac
import json
from datetime import datetime
from enum import Enum
from time import mktime
from typing import Optional, Tuple, Dict, AsyncIterable
from urllib.parse import urlencode
from wsgiref import handlers

import websockets
import websockets.exceptions

from retk import config, const
from retk.logger import logger
from .base import BaseLLMService, MessagesType, NoAPIKeyError


# https://xinghuo.xfyun.cn/sparkapi
class XfYunModelEnum(str, Enum):
    SPARK35_MAX = "v3.5"
    SPARK_PRO = "v3.1"
    SPARK_LITE = "v1.1"


_domain_map = {
    XfYunModelEnum.SPARK35_MAX.value: "generalv3.5",
    XfYunModelEnum.SPARK_PRO.value: "generalv3",
    XfYunModelEnum.SPARK_LITE.value: "general",
}


class XfYunService(BaseLLMService):
    def __init__(
            self,
            top_p: float = 0.9,
            temperature: float = 0.7,
            timeout: float = 60.,
    ):
        super().__init__(
            endpoint="wss://spark-api.xf-yun.com/",
            top_p=top_p,
            temperature=temperature,
            timeout=timeout,
            default_model=XfYunModelEnum.SPARK_LITE.value,
        )
        _s = config.get_settings()
        self.api_secret = _s.XFYUN_API_SECRET
        self.api_key = _s.XFYUN_API_KEY
        self.app_id = _s.XFYUN_APP_ID
        if self.api_secret == "" or self.api_key == "" or self.app_id == "":
            raise NoAPIKeyError("XfYun api secret or key is empty")

    def get_url(self, model: Optional[str], req_id: str = None) -> str:
        if model is None:
            model = self.default_model
        cur_time = datetime.now()
        date = handlers.format_date_time(mktime(cur_time.timetuple()))

        tmp = f"host: spark-api.xf-yun.com\ndate: {date}\nGET /{model}/chat HTTP/1.1"
        tmp_sha = hmac.new(self.api_secret.encode('utf-8'), tmp.encode('utf-8'), digestmod=hashlib.sha256).digest()

        signature = base64.b64encode(tmp_sha).decode(encoding='utf-8')
        authorization_origin = f'api_key="{self.api_key}", ' \
                               f'algorithm="hmac-sha256", ' \
                               f'headers="host date request-line", ' \
                               f'signature="{signature}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        v = {
            "authorization": authorization,  # 上方鉴权生成的authorization
            "date": date,  # 步骤1生成的date
            "host": "spark-api.xf-yun.com"  # 请求的主机名，根据具体接口替换
        }
        url = f"wss://spark-api.xf-yun.com/{model}/chat?" + urlencode(v)
        return url

    def get_data(self, model: str, messages: MessagesType) -> Dict:
        return {
            "header": {
                "app_id": self.app_id,
                "uid": "12345"
            },
            "parameter": {
                "chat": {
                    "domain": _domain_map[model],
                    "temperature": self.temperature,
                    # "max_tokens": 1024,
                }
            },
            "payload": {
                "message": {
                    # 如果想获取结合上下文的回答，需要开发者每次将历史问答信息一起传给服务端，如下示例
                    # 注意：text里面的所有content内容加一起的tokens需要控制在8192以内，开发者如有较长对话需求，需要适当裁剪历史信息
                    "text": messages,
                }
            }
        }

    async def complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None,
    ) -> Tuple[str, const.CodeEnum]:
        txt = ""
        async for content, code in self.stream_complete(messages, model, req_id):
            if code != const.CodeEnum.OK:
                return "", code
            txt += content.decode("utf-8")
        return txt, const.CodeEnum.OK

    async def stream_complete(
            self,
            messages: MessagesType,
            model: str = None,
            req_id: str = None,
    ) -> AsyncIterable[Tuple[bytes, const.CodeEnum]]:
        if model is None:
            model = self.default_model
        url = self.get_url(model, req_id)

        try:
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps(
                    self.get_data(model=model, messages=messages), ensure_ascii=False, separators=(",", ":")
                ))
                async for message in ws:
                    data = json.loads(message)
                    code = data['header']['code']
                    if code != 0:
                        logger.error(f"ReqId={req_id} 请求错误: {code}, {data}")
                        yield b"", const.CodeEnum.LLM_SERVICE_ERROR
                        break

                    choices = data["payload"]["choices"]
                    status = choices["status"]
                    content = choices["text"][0]["content"]

                    if status == 2:
                        # 关闭会话
                        break
                    yield content.encode("utf-8"), const.CodeEnum.OK

        except websockets.exceptions.InvalidStatusCode as e:
            logger.error(f"ReqId={req_id} XfYun model error: {e}")
            yield b"", const.CodeEnum.LLM_SERVICE_ERROR
        usage = data['payload']['usage']
        logger.info(f"ReqId={req_id} XfYun model usage: {usage}")
        return
