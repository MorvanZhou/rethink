import asyncio
import random
from typing import List

from bson import ObjectId

from retk import const
from retk.core.ai.llm import knowledge
from retk.logger import logger
from retk.models.client import init_mongo
from retk.models.tps.llm import NodeExtendQueue, ExtendedNode


def deliver_unscheduled_extend_nodes():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(async_deliver_unscheduled_extend_nodes())
    loop.close()
    return res


async def async_deliver_unscheduled_extend_nodes() -> str:
    _, db = init_mongo(connection_timeout=5)
    batch_size = 3
    total_knowledge_extended = 0
    while True:
        batch: List[NodeExtendQueue] = await db["llmExtendNodeQueue"].find().limit(batch_size).to_list(None)
        if len(batch) == 0:
            break

        batch_result: List[ExtendedNode] = []
        for item in batch:
            req_id = "".join([str(random.randint(0, 9)) for _ in range(10)])
            md = await db["node"].find_one({"id": item["nid"]})
            # md = md[:int(8000 * 1.8)]
            _summary, code = await knowledge.summary(
                llm_service=knowledge.LLM_SERVICES[item["summaryService"]],
                model=item["summaryModel"],
                md=md,
                req_id=req_id,
            )
            if code != const.CodeEnum.OK:
                logger.error(f"knowledge summary error: {code}")
                continue
            _extended, code = await knowledge.extend(
                llm_service=knowledge.LLM_SERVICES[item["extendService"]],
                model=item["extendModel"],
                md=md,
                req_id=req_id,
            )
            if code != const.CodeEnum.OK:
                logger.error(f"knowledge extend error: {code}")
                continue
            batch_result.append(ExtendedNode(
                _id=ObjectId(),
                uid=item["uid"],
                sourceNids=[item["nid"]],
                sourceMd=[md],
                extendMd=_extended,
            ))
            total_knowledge_extended += 1

        if len(batch_result) > 0:
            await db["llmExtendedNode"].insert_many(batch_result)

    return f"successfully extent {total_knowledge_extended} node"
