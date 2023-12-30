import unittest
from textwrap import dedent
from unittest.mock import patch

import httpx

from rethink import const, config
from rethink.models import utils


class UtilsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config.get_settings.cache_clear()

    @classmethod
    def tearDownClass(cls) -> None:
        config.get_settings.cache_clear()

    def test_short_uuid(self):
        for _ in range(10):
            uid = utils.short_uuid()
            self.assertEqual(24, len(uid), msg=uid)

    def test_md2txt(self):
        text = utils.md2txt(md="# 123\n## 456\n### 789\n")
        self.assertEqual("123\n456\n789", text)

    def test_change_link_title(self):
        md = dedent("""\
            # 123
            ddd qwd [@我是谁](/n/sqaaq) 345
            [@ssw](/n/weee)
            """)

        new_md = utils.change_link_title(md, nid="sqaaq", new_title="哇塞")
        self.assertEqual(dedent("""\
            # 123
            ddd qwd [@哇塞](/n/sqaaq) 345
            [@ssw](/n/weee)
            """), new_md)

        new_md = utils.change_link_title(md, nid="weee", new_title="哇塞")
        self.assertEqual(dedent("""\
            # 123
            ddd qwd [@我是谁](/n/sqaaq) 345
            [@哇塞](/n/weee)
            """), new_md)

        md = dedent("""\
            # 123
            ddd qwd [@我是谁](/n/sqaaq) 345
            [@我是谁](/n/sqaaq)
            """)
        new_md = utils.change_link_title(md, nid="sqaaq", new_title="哇塞")
        self.assertEqual(dedent("""\
            # 123
            ddd qwd [@哇塞](/n/sqaaq) 345
            [@哇塞](/n/sqaaq)
            """), new_md)

        md = dedent("""\
            # 123
            ddd qwd 345
            [@我](/n/1) [@我](/n/2)
            """)
        new_md = utils.change_link_title(md, nid="2", new_title="哇塞")
        self.assertEqual(dedent("""\
            # 123
            ddd qwd 345
            [@我](/n/1) [@哇塞](/n/2)
            """), new_md)

    def test_contain_only_link(self):
        for md, res in [
            ("http://rethink.run", "http://rethink.run"),
            ("[123](/n/123)", ""),
            ("few", ""),
            ("c https://rethink.run", ""),
            (" https://rethink.run  ", "https://rethink.run"),
            ("https://rethink.run  ", "https://rethink.run"),
            ("https://rethink.run", "https://rethink.run"),
            ("https://rethink.run wwq", ""),

        ]:
            self.assertEqual(res, utils.contain_only_http_link(md))


class TestAsync(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config.get_settings.cache_clear()

    @classmethod
    def tearDownClass(cls) -> None:
        config.get_settings.cache_clear()

    # @unittest.skip("skip outer connection test")
    @patch(
        "rethink.models.utils.httpx.AsyncClient.get",
    )
    async def test_get_title_description_from_link(self, mock_get):
        for url, content, res in [
            (
                    "https://github.com/MorvanZhou/rethink",
                    "<title>MorvanZhou/rethink: Rethink: a note taking web app</title>"
                    """<meta name="description" content="Rethink: a note taking web app. Contribute to 
                    MorvanZhou/rethink development by creating an account on GitHub.">""",
                    True
            ),
            (
                    "https://zhuanlan.zhihu.com/p/610939462?utm_id=0",
                    """<head>
                    <meta charSet="utf-8"/>
                    <title data-rh="true">python的httpx库如何使用 - 知乎</title>
                    <meta data-rh="true" name="description" content="httpx是一个基于Python的异步HTTP客户端库，
                    可以用于发送HTTP请求和接收HTTP响应。以下是一些httpx库的基本使用方法：
                     发送HTTP GET请求import httpx async with httpx.AsyncClient() as client: response = await…"/>""",
                    True
            ),
            (
                    "https://waqwe12f2f2fa.fffffffff",
                    "",
                    False
            ),
            (
                    "https://baidu.com",
                    """<title>百度一下，你就知道</title>
                    <meta name="description" content="全球领先的中文搜索引擎、
                    致力于让网民更便捷地获取信息，找到所求。百度超过千亿的中文网页数据库，可以瞬间找到相关的搜索结果。">""",
                    True
            ),
            (
                    "https://rethink.run",
                    """<meta content="Rethink" name="title"><title>rethink</title>
                    <meta content="Rethink: think differently" name="description">""",
                    True
            ),
            (
                    "https://baidu.com/wqwqqqqq",
                    "",
                    False
            ),
            (
                    "https://mp.weixin.qq.com/s/jbB0GXbjHpFR8m1-6TSASw",
                    """<title></title><meta name="description" content="" />""",
                    False),
            (
                    "http://127.0.0.1",
                    "",
                    False,
            ),
            (
                    "http://127.0.2.1",
                    "",
                    False,
            ),
            (
                    "http://9.0.0.1.xip.io/?id=1",
                    "",
                    False,
            ),
        ]:
            if res:
                mock_get.return_value = httpx.Response(
                    status_code=200,
                    content=content.encode("utf-8"),
                )
            else:
                mock_get.return_value = httpx.Response(
                    status_code=404,
                    content=content.encode("utf-8"),
                )
            title, desc = await utils.get_title_description_from_link(
                url, language=const.Language.EN.value)
            if res:
                self.assertNotEqual("No title found", title, msg=f"{url} {title}")
                self.assertNotEqual("No description found", desc, msg=f"{url} {desc}")
            else:
                self.assertEqual("No title found", title, msg=f"{url} {title}")
                self.assertEqual("No description found", desc, msg=f"{url} {desc}")

    def test_mask_email(self):
        for email, res in [
            ("", ""),
            ("a", "a"),
            ("a@b", "a**@b"),
            ("ab@b", "a**b@b"),
            ("abc@b", "ab**c@b"),
            ("abcd@b", "ab**d@b"),
            ("abcdef@b", "ab**f@b"),
        ]:
            self.assertEqual(res, utils.mask_email(email))
