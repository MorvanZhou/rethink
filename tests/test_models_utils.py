import unittest
from textwrap import dedent

from rethink import const
from rethink.models import utils


class UtilsTest(unittest.TestCase):
    def test_short_uuid(self):
        for _ in range(10):
            uid = utils.short_uuid()
            self.assertEqual(22, len(uid))

    def test_md2txt(self):
        text = utils.md2txt(md="# 123\n## 456\n### 789\n")
        self.assertEqual("123\n456\n789", text)

    def test_pinyin(self):
        res = utils.txt2search_keys('中心English')
        self.assertEqual({'zhongxinenglish', '中心english', 'ㄓㄨㄥㄒㄧㄣenglish'}, set(res.split(" ")))

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
    async def test_get_title_description_from_link(self):
        for url, res in [
            ("https://github.com/MorvanZhou/rethink", True),
            # ("https://zhuanlan.zhihu.com/p/610939462?utm_id=0", True),
            ("https://waqwe12f2f2fa.fffffffff", False),
            ("https://baidu.com", True),
            ("https://rethink.run", True),
            ("https://rethink.run/about", True),
            ("https://baidu.com/wqwqqqqq", False),
            ("https://mp.weixin.qq.com/s/jbB0GXbjHpFR8m1-6TSASw", True),
        ]:
            title, desc = await utils.get_title_description_from_link(
                url, language=const.Language.EN.value)
            if res:
                self.assertNotEqual("No title found", title, msg=f"{url} {title}")
                self.assertNotEqual("No description found", desc, msg=f"{url} {desc}")
            else:
                self.assertEqual("No title found", title, msg=f"{url} {title}")
                self.assertEqual("No description found", desc, msg=f"{url} {desc}")
