import unittest
from textwrap import dedent

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
        self.assertEqual(dedent(f"""\
            # 123
            ddd qwd [@哇塞](/n/sqaaq) 345
            [@ssw](/n/weee)
            """), new_md)

        new_md = utils.change_link_title(md, nid="weee", new_title="哇塞")
        self.assertEqual(dedent(f"""\
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
        self.assertEqual(dedent(f"""\
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
        self.assertEqual(dedent(f"""\
            # 123
            ddd qwd 345
            [@我](/n/1) [@哇塞](/n/2)
            """), new_md)

