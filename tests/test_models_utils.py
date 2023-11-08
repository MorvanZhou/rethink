import unittest
from io import BytesIO
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
        res = utils.replace_inner_link(
            md,
            exist_filename2nid=filename2nid,
            img_path_dict={},
            img_name_dict={},
            min_img_size=0,
        )
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
        res = utils.replace_inner_link(
            md,
            exist_filename2nid=filename2nid,
            img_path_dict={},
            img_name_dict={},
            min_img_size=0,
        )
        self.assertEqual(dedent(f"""\
            # 123
            ddd qwd [@123](/n/{o1}) 345
            [@我哦](/n/{filename2nid['我哦']})
            """), res)

        self.assertIn("我哦", filename2nid)

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

    def test_file_hash(self):
        self.assertEqual(
            "d41d8cd98f00b204e9800998ecf8427e",
            utils.file_hash(BytesIO(b"")))
        bio = BytesIO(b"The quick brown fox jumps over the lazy dog")
        self.assertEqual(
            "9e107d9d372bb6826bd81d3542a419d6",
            utils.file_hash(bio))

        self.assertEqual(b"The quick brown fox jumps over the lazy dog", bio.read())
