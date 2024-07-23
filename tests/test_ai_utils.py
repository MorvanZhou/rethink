import unittest
from textwrap import dedent

from retk.core.ai.llm import utils


def char_generator(text):
    for char in text:
        yield char


class TestUtils(unittest.TestCase):
    def test_json_pattern(self):
        d = utils.parse_json_pattern("""{"title": "tttt", "content": "cccc\n21\n2", "q": "qqq"}""")
        self.assertEqual("tttt", d["title"])
        self.assertEqual("cccc\n21\n2", d["content"])
        self.assertEqual("qqq", d["q"])

        cases = [
            """\
            {
              "title": "tttt",
              "content": "cccc",
              "q": "qqq"
            }
            """,
            """{"title":"tttt","content":"cccc","q":"qqq"}""",
            """\
            1afwenq 是当前
            轻ww 1
            {
              "title": "tttt",
              "content": "cccc",
              "q": "qqq"
            }
            """,
            """\
            {
              "title": "tttt",
              "content": "cccc",
              "q": "qqq"
            }
            23423saq1是当前
            """,
            """\
            这是一个关于午睡对大脑健康益处的内容描述，以下是按照要求以json格式返回的结果：

            ```json
            {
              "title": "tttt",
              "content": "cccc",
              "q": "qqq"
            }
            ```. msg: 这结果：```json
            {  "标题": "午睡对", "内容": "午睡进身心健康。" , "q": "qqq"}```
            """
        ]
        for case in cases:
            case = dedent(case)
            d = utils.parse_json_pattern(case)
            self.assertEqual("tttt", d["title"])
            self.assertEqual("cccc", d["content"])
            self.assertEqual("qqq", d["q"])

        bad_cases = [
            """\
            {
              'title': "tttt",
              "content": "cccc"
            }
            """,
            """\
            {
              "title": 'tttt',
              "content": "cccc"
            }
            """,
            """\
            {
              "t1itle": "tttt",
              "content": "cccc"
            }
            """
        ]

        for case in bad_cases:
            case = dedent(case)
            with self.assertRaises(ValueError):
                utils.parse_json_pattern(case)
