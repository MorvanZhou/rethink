import json
import unittest
from datetime import datetime
from unittest.mock import patch, AsyncMock

from httpx import Response

from retk import const, config
from retk.core.ai import llm
from retk.core.ai.llm.api.base import NoAPIKeyError
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


def skip_no_api_key(fn):
    async def wrapper(*args):
        try:
            return await fn(*args)
        except NoAPIKeyError:
            pass

    return wrapper


def clear_all_api_key():
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
    c.MOONSHOT_API_KEY = ""


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
        clear_all_api_key()

    @skip_no_api_key
    async def test_hunyuan_complete(self):
        m = llm.api.TencentService()
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        print(text)

    @skip_no_api_key
    async def test_hunyuan_stream_complete(self):
        m = llm.api.TencentService()
        async for b, code in m.stream_complete([{"role": "user", "content": "你是谁"}]):
            self.assertEqual(const.CodeEnum.OK, code)
            s = b.decode("utf-8")
            print(s)

    @skip_no_api_key
    async def test_hunyuan_batch_complete(self):
        m = llm.api.TencentService()
        res = await m.batch_complete(
            [[{"role": "user", "content": "你是谁"}]] * 11,
        )
        for text, code in res:
            self.assertEqual(const.CodeEnum.OK, code, msg=text)
            print(text)

        m = llm.api.TencentService()
        m.concurrency = 6
        res = await m.batch_complete(
            [[{"role": "user", "content": "你是谁"}]] * 11,
        )
        reach_limit = False
        for text, code in res:
            if code == const.CodeEnum.LLM_API_LIMIT_EXCEEDED:
                reach_limit = True
                break
        self.assertTrue(reach_limit)

    @skip_no_api_key
    async def test_aliyun_complete(self):
        m = llm.api.AliyunService()
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        print(text)

    @skip_no_api_key
    async def test_aliyun_stream_complete(self):
        m = llm.api.AliyunService()
        async for b, code in m.stream_complete([{"role": "user", "content": "你是谁"}]):
            self.assertEqual(const.CodeEnum.OK, code)
            print(b.decode("utf-8"))

    @skip_no_api_key
    async def test_aliyun_batch_complete(self):
        m = llm.api.AliyunService()
        res = await m.batch_complete(
            [[{"role": "user", "content": "你是谁"}]] * 11,
        )
        for text, code in res:
            self.assertEqual(const.CodeEnum.OK, code, msg=text)
            print(text)

    @skip_no_api_key
    async def test_baidu_complete(self):
        m = llm.api.BaiduService()
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        print(text)

    @skip_no_api_key
    async def test_baidu_stream_complete(self):
        m = llm.api.BaiduService()
        async for b, code in m.stream_complete([{"role": "user", "content": "你是谁"}]):
            self.assertEqual(const.CodeEnum.OK, code)
            print(b.decode("utf-8"))

    @skip_no_api_key
    async def test_baidu_batch_complete(self):
        m = llm.api.BaiduService()
        res = await m.batch_complete(
            [[{"role": "user", "content": "你是谁"}]] * 11,
        )
        for text, code in res:
            self.assertEqual(const.CodeEnum.OK, code, msg=text)
            print(text)

    @skip_no_api_key
    async def test_openai_complete(self):
        m = llm.api.OpenaiService()
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        print(text)

    @skip_no_api_key
    async def test_openai_stream_complete(self):
        m = llm.api.OpenaiService()
        async for b, code in m.stream_complete([{"role": "user", "content": "你是谁"}]):
            self.assertEqual(const.CodeEnum.OK, code)
            print(b.decode("utf-8"))

    @skip_no_api_key
    async def test_openai_batch_complete(self):
        m = llm.api.OpenaiService()
        res = await m.batch_complete(
            [[{"role": "user", "content": "你是谁"}]] * 11,
        )
        for text, code in res:
            self.assertEqual(const.CodeEnum.OK, code, msg=text)
            print(text)

    @skip_no_api_key
    async def test_xfyun_complete(self):
        m = llm.api.XfYunService()
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        print(text)

    @skip_no_api_key
    async def test_xfyun_stream_complete(self):
        m = llm.api.XfYunService()
        async for b, code in m.stream_complete([{"role": "user", "content": "你是谁"}]):
            self.assertEqual(const.CodeEnum.OK, code)
            print(b.decode("utf-8"))

    @skip_no_api_key
    async def test_xfyun_batch_complete(self):
        m = llm.api.XfYunService()
        res = await m.batch_complete(
            [[{"role": "user", "content": "你是谁"}]] * 11,
        )
        for text, code in res:
            self.assertEqual(const.CodeEnum.OK, code, msg=text)
            print(text)

    @skip_no_api_key
    async def test_moonshot_complete(self):
        m = llm.api.MoonshotService()
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        print(text)

    @skip_no_api_key
    async def test_moonshot_stream_complete(self):
        m = llm.api.MoonshotService()
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
        m = llm.api.TencentService()
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
        m = llm.api.TencentService()
        self.assertEqual("hunyuan-lite", m.default_model.key)
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
        m = llm.api.TencentService()
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
        m = llm.api.AliyunService()
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        self.assertEqual("我是一个AI助手。", text)
        mock_post.assert_called_once()

    @skip_no_api_key
    async def test_baidu_token(self):
        m = llm.api.BaiduService()
        await m.set_token()
        self.assertNotEqual("", m.token)
        self.assertGreater(m.token_expires_at, datetime.now().timestamp())

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=mock_baidu_post)
    async def test_baidu_complete_mock(self, mock_post):
        config.get_settings().BAIDU_QIANFAN_API_KEY = self.sid
        config.get_settings().BAIDU_QIANFAN_SECRET_KEY = self.skey
        m = llm.api.BaiduService()
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
        m = llm.api.OpenaiService()
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        self.assertEqual("我是一个AI助手。", text)
        mock_post.assert_called_once()

    @patch("httpx.AsyncClient.post")
    async def test_xfyun_complete_mock(self, mock_post):
        mock_post.return_value = Response(
            status_code=200,
            json={
                "code": 0,
                "message": "success",
                "sid": "chaxxxxx",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "我是一个AI助手。"
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 14,
                    "total_tokens": 17
                }
            }
        )
        config.get_settings().XFYUN_API_KEY = "testkey"
        config.get_settings().XFYUN_API_SECRET = "testsecret"
        m = llm.api.XfYunService()

        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        self.assertEqual("我是一个AI助手。", text)
        mock_post.assert_called_once()

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_moonshot_complete_mock(self, mock_post):
        mock_post.return_value = Response(
            status_code=200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "我是一个AI助手。"
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 14,
                    "total_tokens": 17
                }
            }
        )
        config.get_settings().MOONSHOT_API_KEY = self.sid
        m = llm.api.MoonshotService()
        text, code = await m.complete([{"role": "user", "content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        self.assertEqual("我是一个AI助手。", text)
        mock_post.assert_called_once()
