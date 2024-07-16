import unittest
from textwrap import dedent

from retk import const
from retk.core.ai import llm
from retk.core.ai.llm.knowledge.utils import parse_json_pattern
from . import utils
from .test_ai_llm_api import skip_no_api_key, clear_all_api_key

md_source = ["""\
    广东猪脚饭特点
    
    广州猪脚饭超越沙县小吃兰州拉面等，成为广东第一中式快餐。
    
    原因是
    
    1. 广东人口分布有很多外来人口，猪脚饭兼容了很多口味
    2. 工艺简单，大量的预制工作，较低出餐时间，出餐快。适合快节奏的打工人群
    3. 因为出餐快，所以不用招人，省人力成本
    
    ![IMG6992.png](https://files.rethink.run/userData/3a4344ccd6ba477e59ddf1f7f67e98bd.png)
    
    更值得一提的是猪脚饭在广东便宜，其它地方贵，原因之一是可以从香港走私猪脚，因为外国人不吃，所以产能过剩
    
    【猪脚饭如何成为广东的快餐之王？【食录】-哔哩哔哩】 https://b23.tv/YUlg1nN
    """,
             """\
             蓝莓散射光表现蓝色
             
             蓝莓是为数不多的蓝色水果。如果用化学的方法合成蓝色，那太费成本了。所以它选择用物理散射，
              [@天空为什么是蓝色](/n/4dmEv7TLvGHdPymmWtoAvhQH) 蓝天的方法，用表层的一层石蜡空心结构，
              将蓝色散射出来。同时鸟类视觉对蓝色敏感，他们更能看到蓝色
             """
             ]

md_summary = [
    """\
    标题：广东猪脚饭的快餐特色与成功因素
    
    知识点：
    1. **市场接受度**：广东猪脚饭因兼容多种口味，受到广泛欢迎，超越沙县小吃和兰州拉面成为广东最受欢迎的中式快餐。
    2. **人口结构**：广东的外来人口众多，猪脚饭满足了不同地域人群的口味需求。
    3. **工艺优势**：猪脚饭的制作工艺简单，预制工作量大，出餐速度快，适合快节奏生活。
    4. **成本效益**：快速出餐减少了人力成本，提高了经营效率。
    5. **价格因素**：猪脚饭在广东价格低廉，部分原因是可能通过香港走私猪脚，利用外国人不吃猪脚导致的产能过剩。
    """,
    """\
    标题：蓝莓的蓝色散射原理及其生态意义
    
    关键点：
    1. 蓝莓呈现蓝色的独特性：是少数天然蓝色水果之一。
    2. 物理散射机制：通过表层的石蜡空心结构实现蓝色光的散射。
    3. 经济性：物理散射相比化学合成更为经济。
    4. 生态适应性：鸟类视觉对蓝色敏感，有助于蓝莓种子的传播。
    """
]


class LLMKnowledgeExtendTest(unittest.IsolatedAsyncioTestCase):
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
    async def test_summary(self):
        for service, model in [
            (llm.api.TencentService(), llm.api.TencentModelEnum.HUNYUAN_LITE),
            (llm.api.AliyunService(), llm.api.AliyunModelEnum.QWEN_2B),
            (llm.api.BaiduService(), llm.api.BaiduModelEnum.ERNIE_SPEED_8K),
            # (llm.api.OpenaiService(), llm.api.OpenaiModelEnum.GPT4),
            (llm.api.XfYunService(), llm.api.XfYunModelEnum.SPARK_LITE),
            (llm.api.MoonshotService(), llm.api.MoonshotModelEnum.V1_8K),  # 这个总结比较好
        ]:
            for md in md_source:
                text, code = await llm.knowledge.summary(
                    llm_service=service,
                    model=model.value,
                    md=md,
                )
                self.assertEqual(const.CodeEnum.OK, code, msg=text)
                print(f"{service.__class__.__name__} {model.name}\n{text}\n\n")

    @skip_no_api_key
    async def test_extend(self):
        for service, model in [
            # (llm.api.TencentService(), llm.api.TencentModelEnum.HUNYUAN_PRO),
            (llm.api.TencentService(), llm.api.TencentModelEnum.HUNYUAN_STANDARD),
            (llm.api.AliyunService(), llm.api.AliyunModelEnum.QWEN_PLUS),
            (llm.api.BaiduService(), llm.api.BaiduModelEnum.ERNIE35_8K),
            # (llm.api.OpenaiService(), llm.api.OpenaiModelEnum.GPT4),
            (llm.api.XfYunService(), llm.api.XfYunModelEnum.SPARK_PRO),
            (llm.api.MoonshotService(), llm.api.MoonshotModelEnum.V1_8K),  # 这个延伸比较好
        ]:
            for md in md_source:
                text, code = await llm.knowledge.extend(
                    llm_service=service,
                    model=model.value,
                    md=md,
                )
                self.assertEqual(const.CodeEnum.OK, code, msg=text)
                print(f"{service.__class__.__name__} {model.name}\n{text}\n\n")

    def test_json_pattern(self):
        title, content = parse_json_pattern("""{"title": "tttt", "content": "cccc\n21\n2"}""")
        self.assertEqual("tttt", title)
        self.assertEqual("cccc\n21\n2", content)

        cases = [
            """\
            {
              "title": "tttt",
              "content": "cccc"
            }
            """,
            """{"title":"tttt","content":"cccc"}""",
            """\
            1afwenq 是当前
            轻ww 1
            {
              "title": "tttt",
              "content": "cccc"
            }
            """,
            """\
            {
              "title": "tttt",
              "content": "cccc"
            }
            23423saq1是当前
            """,
        ]
        for case in cases:
            case = dedent(case)
            title, content = parse_json_pattern(case)
            self.assertEqual("tttt", title)
            self.assertEqual("cccc", content)

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
                parse_json_pattern(case)
