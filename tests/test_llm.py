import json
import unittest
from unittest.mock import patch, AsyncMock

from httpx import Response

from retk import const
from retk.core.ai import llm
from . import utils


class HunyuanTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.sid = "testid"
        cls.skey = "testkey"
        utils.set_env(".env.test.local")

    @classmethod
    def tearDownClass(cls) -> None:
        utils.drop_env(".env.test.local")

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
        m = llm.hunyuan.HunyuanLite(
            secret_id=self.sid, secret_key=self.skey
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

    async def test_hunyuan_auth_failed(self):
        m = llm.hunyuan.HunyuanLite(
            secret_id=self.sid, secret_key=self.skey
        )
        self.assertEqual("hunyuan-lite", m.name)
        text, code = await m.complete([{"Role": "user", "Content": "你是谁"}])
        self.assertEqual(const.CodeEnum.LLM_SERVICE_ERROR, code, msg=text)
        self.assertEqual("SecretId不存在，请输入正确的密钥。", text)

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_hunyuan_complete(self, mock_post):
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
                    ]
                }
            }
        )
        m = llm.hunyuan.HunyuanLite(
            secret_id=self.sid, secret_key=self.skey
        )
        text, code = await m.complete([{"Role": "user", "Content": "你是谁"}])
        self.assertEqual(const.CodeEnum.OK, code, msg=text)
        self.assertEqual("我是一个AI助手。", text)
        mock_post.assert_called_once()

    # async def test_hunyuan_stream_complete(self):
    #     m = llm.hunyuan.HunyuanLite()
    #
    #     async for b, code in m.stream_complete([{"Role": "user", "Content": "你是谁"}]):
    #         self.assertEqual(const.CodeEnum.OK, code)
    #         s = b.decode("utf-8")
    #         lines = s.splitlines()
    #         for line in lines:
    #             if line.strip() == "":
    #                 continue
    #             self.assertTrue(line.startswith("data: "))
    #             json_str = line[6:]
    #             json_data = json.loads(json_str)
    #             self.assertIn("Choices", json_data)
    #             choices = json_data["Choices"]
    #             self.assertEqual(1, len(choices))
    #             choice = choices[0]
    #             self.assertIn("Delta", choice)
    #             delta = choice["Delta"]
    #             self.assertIn("Content", delta)
    #             if choice["FinishReason"] == "":
    #                 self.assertGreater(len(delta["Content"]), 0)
    #             else:
    #                 self.assertEqual("", delta["Content"])
    #             self.assertEqual("assistant", delta["Role"])
