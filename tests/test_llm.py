import json
import unittest
from datetime import datetime
from unittest.mock import patch, AsyncMock, Mock

from httpx import Response

from retk import const, config
from retk.core.ai import llm
from . import utils


async def mock_baidu_post(url, *args, **kwargs):
    if url == "https://aip.baidubce.com/oauth/2.0/token":
        return Response(
            status_code=200,
            json={
                "expires_in": 5000,
                "access_token": "testtoken"
            }
        )
    elif url.startswith("https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/"):
        return Response(
            status_code=200,
            json={
                "result": "我是一个AI助手。",
                "usage": {
                    "prompt_tokens": 341,
                    "completion_tokens": 189,
                    "total_tokens": 530
                }
            }
        )
    else:
        raise ValueError(f"Unexpected URL: {url}")


class ChatBotTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.sid = "testid"
        cls.skey = "testkey"
        utils.set_env(".env.test.local")

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

    def tearDown(self):
        c = config.get_settings()
        c.HUNYUAN_SECRET_ID = ""
        c.HUNYUAN_SECRET_KEY = ""
        c.ALIYUN_DASHSCOPE_API_KEY = ""
        c.BAIDU_QIANFAN_API_KEY = ""
        c.BAIDU_QIANFAN_SECRET_KEY = ""
        c.OPENAI_API_KEY = ""
        c.XFYUN_APP_ID = ""
        c.XFYUN_API_SECRET = ""
        c.XFYUN_API_KEY = ""

    async def test_hunyuan_complete(self):
        try:
            m = llm.Tencent()
        except ValueError:
            return
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        print(text)

    async def test_hunyuan_stream_complete(self):
        try:
            m = llm.Tencent()
        except ValueError:
            return
        async for b, code in m.stream_complete([{"role": "user", "content": "你是谁"}]):
            self.assertEqual(const.CodeEnum.OK, code)
            s = b.decode("utf-8")
            print(s)

    async def test_aliyun_complete(self):
        try:
            m = llm.Aliyun()
        except ValueError:
            return
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        print(text)

    async def test_aliyun_stream_complete(self):
        try:
            m = llm.Aliyun()
        except ValueError:
            return
        async for b, code in m.stream_complete([{"role": "user", "content": "你是谁"}]):
            self.assertEqual(const.CodeEnum.OK, code)
            print(b.decode("utf-8"))

    async def test_baidu_complete(self):
        try:
            m = llm.Baidu()
        except ValueError:
            return
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        print(text)

    async def test_baidu_stream_complete(self):
        try:
            m = llm.Baidu()
        except ValueError:
            return
        async for b, code in m.stream_complete([{"role": "user", "content": "你是谁"}]):
            self.assertEqual(const.CodeEnum.OK, code)
            print(b.decode("utf-8"))

    async def test_openai_complete(self):
        try:
            m = llm.OpenAI()
        except ValueError:
            return
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        print(text)

    async def test_openai_stream_complete(self):
        try:
            m = llm.OpenAI()
        except ValueError:
            return
        async for b, code in m.stream_complete([{"role": "user", "content": "你是谁"}]):
            self.assertEqual(const.CodeEnum.OK, code)
            print(b.decode("utf-8"))

    async def test_xfyun_complete(self):
        try:
            m = llm.XfYun()
        except ValueError:
            return
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        print(text)

    async def test_xfyun_stream_complete(self):
        try:
            m = llm.XfYun()
        except ValueError:
            return
        async for b, code in m.stream_complete([{"role": "user", "content": "你是谁"}]):
            self.assertEqual(const.CodeEnum.OK, code)
            print(b.decode("utf-8"))

    def test_hunyuan_authorization(self):
        payload = {
            "Model": "hunyuan-lite",
            "Messages": [{"Role": "user", "Content": "你是谁"}],
            "Stream": False,
            "TopP": 0.9,
            "Temperature": 0.7,
            "EnableEnhancement": False,
        }
        payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        config.get_settings().HUNYUAN_SECRET_ID = self.sid
        config.get_settings().HUNYUAN_SECRET_KEY = self.skey
        m = llm.Tencent()
        auth = m.get_auth(
            action="ChatCompletions",
            payload=payload,
            timestamp=1716913478,
            content_type="application/json"
        )
        self.assertEqual(
            f"TC3-HMAC-SHA256 Credential={self.sid}/2024-05-28/hunyuan/tc3_request,"
            f" SignedHeaders=content-type;host;x-tc-action,"
            f" Signature=f628e271c4acdf72a4618fe59e3a31591f2ddedbd44e5befe6e02c05949b01b3",
            auth)

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_hunyuan_auth_failed(self, mock_post):
        mock_post.return_value = Response(
            status_code=200,
            json={
                "Response": {
                    "Error": {
                        "Message": "SecretId不存在，请输入正确的密钥。",
                        "Code": "AuthFailure.SecretIdNotFound"
                    }
                }
            }
        )
        config.get_settings().HUNYUAN_SECRET_ID = self.sid
        config.get_settings().HUNYUAN_SECRET_KEY = self.skey
        m = llm.Tencent()
        self.assertEqual("hunyuan-lite", m.default_model)
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.LLM_SERVICE_ERROR, code, msg=text)
        self.assertEqual("SecretId不存在，请输入正确的密钥。", text)
        mock_post.assert_called_once()

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_hunyuan_complete_mock(self, mock_post):
        mock_post.return_value = Response(
            status_code=200,
            json={
                "Response": {
                    "Choices": [
                        {
                            "Message": {
                                "Role": "assistant",
                                "Content": "我是一个AI助手。"
                            }
                        }
                    ],
                    "Usage": {
                        "PromptTokens": 3,
                        "CompletionTokens": 14,
                        "TotalTokens": 17
                    }
                }
            }
        )
        config.get_settings().HUNYUAN_SECRET_ID = self.sid
        config.get_settings().HUNYUAN_SECRET_KEY = self.skey
        m = llm.Tencent()
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        self.assertEqual("我是一个AI助手。", text)
        mock_post.assert_called_once()

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_aliyun_complete_mock(self, mock_post):
        mock_post.return_value = Response(
            status_code=200,
            json={
                "status_code": 200,
                "output": {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "我是一个AI助手。"
                            }
                        }
                    ]
                },
                "usage": {
                    "computation_time": 341,
                    "input_tokens": 189,
                    "output_tokens": 530
                }
            }
        )
        config.get_settings().ALIYUN_DASHSCOPE_API_KEY = self.skey
        m = llm.Aliyun()
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        self.assertEqual("我是一个AI助手。", text)
        mock_post.assert_called_once()

    async def test_baidu_token(self):
        try:
            m = llm.Baidu()
        except ValueError:
            return
        await m.set_token()
        self.assertNotEqual("", m.token)
        self.assertGreater(m.token_expires_at, datetime.now().timestamp())

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=mock_baidu_post)
    async def test_baidu_complete_mock(self, mock_post):
        config.get_settings().BAIDU_QIANFAN_API_KEY = self.sid
        config.get_settings().BAIDU_QIANFAN_SECRET_KEY = self.skey
        m = llm.Baidu()
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        self.assertEqual("我是一个AI助手。", text)
        # assert called twice
        mock_post.assert_called()

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_openai_complete_mock(self, mock_post):
        mock_post.return_value = Response(
            status_code=200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "我是一个AI助手。"
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 14,
                    "total_tokens": 17
                }
            }
        )
        config.get_settings().OPENAI_API_KEY = self.sid
        m = llm.OpenAI()
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        self.assertEqual("我是一个AI助手。", text)
        mock_post.assert_called_once()

    @patch("wsgiref.handlers.format_date_time")
    def test_xfyun_auth(self, mock_format_date_time: Mock):
        mock_format_date_time.return_value = "Fri, 05 May 2023 10:43:39 GMT"
        config.get_settings().XFYUN_API_KEY = "addd2272b6d8b7c8abdd79531420ca3b"
        config.get_settings().XFYUN_API_SECRET = "MjlmNzkzNmZkMDQ2OTc0ZDdmNGE2ZTZi"
        config.get_settings().XFYUN_APP_ID = "testappid"
        m = llm.XfYun()
        url = m.get_url(
            model="v1.1",
        )
        self.assertEqual(
            "wss://spark-api.xf-yun.com/v1.1/chat?"
            "authorization=YXBpX2tleT0iYWRkZDIyNzJiNmQ4YjdjOGFiZGQ3OTUzMTQyMGNhM2IiLCBhbGdvcml0aG09ImhtYWMtc2"
            "hhMjU2IiwgaGVhZGVycz0iaG9zdCBkYXRlIHJlcXVlc3QtbGluZSIsIHNpZ25hdHVyZT0iejVnSGR1M3B4VlY0QURNeWs0Njd"
            "3T1dEUTlxNkJRelIzbmZNVGpjL0RhUT0i&date=Fri%2C+05+May+2023+10%3A43%3A39+GMT&host=spark-api.xf-yun.com",
            url
        )

    @patch("websockets.connect")
    async def test_xfyun_complete_mock(self, mock_connect):
        config.get_settings().XFYUN_API_KEY = "testkey"
        config.get_settings().XFYUN_API_SECRET = "testsecret"
        config.get_settings().XFYUN_APP_ID = "testappid"

        def get_mock_messages():
            # 返回模拟的消息
            for _ in range(3):
                message = {
                    "header": {"code": 0},
                    "payload": {
                        "choices": {
                            "status": 1,
                            "text": [{"content": "mocked_content"}]
                        },
                        "usage": "mocked_usage"
                    }
                }
                yield json.dumps(message)

        # 创建一个 AsyncMock 对象模拟 ws
        mock_ws = AsyncMock()

        # 设置 ws.send 和 ws.__aiter__ 的返回值
        mock_ws.send.return_value = None
        mock_ws.__aiter__.return_value = get_mock_messages()

        # 设置 websockets.connect 的返回值
        mock_connect.return_value.__aenter__.return_value = mock_ws

        m = llm.XfYun()

        async for result in m.stream_complete([{"role": "user", "content": "你是谁"}]):
            # 对返回的结果进行断言
            self.assertEqual(result, (b"mocked_content", const.CodeEnum.OK))
