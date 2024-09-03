import unittest

from bson import ObjectId

from retk import const
from retk.core.ai import llm
from retk.core.ai.llm.knowledge.ops import ExtendCase
from tests import utils
from tests.test_ai_llm_api import skip_no_api_key, clear_all_api_key

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
            (llm.api.TencentService.name, llm.api.TencentModelEnum.HUNYUAN_LITE),
            (llm.api.AliyunService.name, llm.api.AliyunModelEnum.QWEN_2B),
            (llm.api.BaiduService.name, llm.api.BaiduModelEnum.ERNIE_SPEED_8K),
            # (llm.api.OpenaiService.name, llm.api.OpenaiModelEnum.GPT4),
            (llm.api.XfYunService.name, llm.api.XfYunModelEnum.SPARK_LITE),
            (llm.api.MoonshotService.name, llm.api.MoonshotModelEnum.V1_8K),  # 这个总结比较好
            (llm.api.VolcEngineService.name, llm.api.VolcEngineModelEnum.DOUBAO_PRO_32K),
            (llm.api.GLMService.name, llm.api.GLMModelEnum.GLM4_FLASH),
        ]:
            cases = [
                ExtendCase(
                    _id=ObjectId(),
                    uid="testuid",
                    nid="testnid",
                    summary_service=service,
                    summary_model=model.value.key,
                    extend_service=service,
                    extend_model=model.value.key,
                    md=md,
                ) for md in md_source
            ]
            await llm.knowledge.batch_summary(
                cases=cases,
            )
            for case in cases:
                self.assertEqual(const.CodeEnum.OK, case.extend_code, msg=case.md)
                print(f"{service} {model.value.key}\n{case.summary}\n\n")

    @skip_no_api_key
    async def test_extend(self):
        for service, model in [
            # (llm.api.TencentService.name, llm.api.TencentModelEnum.HUNYUAN_PRO),
            (llm.api.TencentService.name, llm.api.TencentModelEnum.HUNYUAN_STANDARD),
            (llm.api.AliyunService.name, llm.api.AliyunModelEnum.QWEN_PLUS),
            (llm.api.BaiduService.name, llm.api.BaiduModelEnum.ERNIE35_8K),
            # (llm.api.OpenaiService.name, llm.api.OpenaiModelEnum.GPT4),
            (llm.api.XfYunService.name, llm.api.XfYunModelEnum.SPARK_PRO),
            (llm.api.MoonshotService.name, llm.api.MoonshotModelEnum.V1_8K),  # 这个延伸比较好
            (llm.api.VolcEngineService.name, llm.api.VolcEngineModelEnum.DOUBAO_PRO_32K),  # 这个延伸比较好
            (llm.api.GLMService.name, llm.api.GLMModelEnum.GLM4_PLUS),
        ]:
            cases = [
                ExtendCase(
                    _id=ObjectId(),
                    uid="testuid",
                    nid="testnid",
                    summary_service=service,
                    summary_model=model.value.key,
                    extend_service=service,
                    extend_model=model.value.key,
                    md=md,
                    summary=md
                ) for md in md_summary
            ]
            await llm.knowledge.batch_extend(
                cases=cases
            )
            for case in cases:
                # self.assertEqual(const.CodeEnum.OK, case.extend_code, msg=case.summary)
                print(f"{service} {model.value.key}\n{case.extend_md}\nkeywords={case.extend_search_terms}\n\n")
