import json
import unittest
from datetime import datetime
from unittest.mock import patch, AsyncMock

from httpx import Response

from retk import const
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

    def test_authorization(self):
        payload = {
            "Model": "hunyuan-lite",
            "Messages": [{"Role": "user", "Content": "你是谁"}],
            "Stream": False,
            "TopP": 0.9,
            "Temperature": 0.7,
            "EnableEnhancement": False,
        }
        payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        m = llm.Tencent(
            secret_id=self.sid,
            secret_key=self.skey
        )
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
        m = llm.Tencent(
            secret_id=self.sid,
            secret_key=self.skey
        )
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
        m = llm.Tencent(
            secret_id=self.sid,
            secret_key=self.skey
        )
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
        m = llm.Aliyun(api_key="testkey")
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
        m = llm.Baidu(api_key="testkey", secret_key="testkey")
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        self.assertEqual("我是一个AI助手。", text)
        # assert called twice
        mock_post.assert_called()
