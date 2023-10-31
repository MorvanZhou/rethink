import unittest
from textwrap import dedent

from bson import ObjectId

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

    def test_replace_inner_link(self):
        md = dedent("""\
            # 123
            ddd qwd [[123]] 345
            [[我哦]]
            """)
        o1 = str(ObjectId())
        o2 = str(ObjectId())
        filename2nid = {"123": o1, "我哦": o2}
        res = utils.replace_inner_link(md, filename2nid=filename2nid)
        self.assertEqual(dedent(f"""\
            # 123
            ddd qwd [@123](/n/{o1}) 345
            [@我哦](/n/{o2})
            """), res)

        self.assertEqual({"123": o1, "我哦": o2}, filename2nid)

    def test_replace_inner_link_new(self):
        md = dedent("""\
            # 123
            ddd qwd [[123]] 345
            [[我哦]]
            """)

        o1 = str(ObjectId())
        filename2nid = {"123": o1}
        res = utils.replace_inner_link(md, filename2nid=filename2nid)
        self.assertEqual(dedent(f"""\
            # 123
            ddd qwd [@123](/n/{o1}) 345
            [@我哦](/n/{filename2nid['我哦']})
            """), res)

        self.assertIn("我哦", filename2nid)
