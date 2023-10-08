import unittest

from rethink.models import utils


class UtilsTest(unittest.TestCase):
    def test_short_uuid(self):
        for _ in range(10):
            uid = utils.short_uuid()
            self.assertEqual(22, len(uid))

    def test_md2txt(self):
        text = utils.md2txt(text="# 123\n## 456\n### 789\n")
        self.assertEqual("123\n456\n789", text)

    def test_pinyin(self):
        res = utils.text2search_keys('中心English')
        self.assertEqual({'zhongxinenglish', '中心english', 'ㄓㄨㄥㄒㄧㄣenglish'}, set(res.split(" ")))
