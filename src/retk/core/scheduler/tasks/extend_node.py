import asyncio
import random
import time
from typing import List

from retk import const
from retk.core.ai.llm import knowledge
from retk.logger import logger
from retk.models.client import init_mongo
from retk.models.coll import CollNameEnum
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
    total_success_count = 0
    total_summary_time = 0
    total_extend_time = 0
    while True:
        done_id_list = []
        batch: List[NodeExtendQueue] = await db[CollNameEnum.llm_extend_node_queue.value].find().limit(
            batch_size).to_list(None)
        if len(batch) == 0:
            break

        for item in batch:
            req_id = "".join([str(random.randint(0, 9)) for _ in range(10)])
            node = await db[CollNameEnum.nodes.value].find_one({"id": item["nid"]})
            # md = md[:int(8000 * 1.8)]
            s0 = time.perf_counter()
            _summary, code = await knowledge.summary(
                llm_service=knowledge.LLM_SERVICES[item["summaryService"]],
                model=item["summaryModel"],
                md=node["md"],
                req_id=req_id,
            )
            s1 = time.perf_counter()
            if code != const.CodeEnum.OK:
                logger.error(f"knowledge summary error: {code}")
                continue
            logger.debug(f"summary: {_summary}")
            e0 = time.perf_counter()
            _extended, code = await knowledge.extend(
                llm_service=knowledge.LLM_SERVICES[item["extendService"]],
                model=item["extendModel"],
                md=_summary,
                req_id=req_id,
            )
            e1 = time.perf_counter()
            if code != const.CodeEnum.OK:
                logger.error(f"knowledge extend error: {code}")
                continue
            logger.debug(f"extended: {_extended}")
            ext = ExtendedNode(
                uid=item["uid"],
                sourceNid=item["nid"],
                sourceMd=node["md"],
                extendMd=_extended,
            )
            await db[CollNameEnum.llm_extended_node.value].update_one(
                {"uid": item["uid"], "sourceNid": item["nid"]},
                {"$set": ext},
                upsert=True
            )
            done_id_list.append(item["_id"])
            total_summary_time += s1 - s0
            total_extend_time += e1 - e0

        if len(done_id_list) > 0:
            res = await db[CollNameEnum.llm_extend_node_queue.value].delete_many({"_id": {"$in": done_id_list}})
            total_success_count += res.deleted_count

    if total_success_count > 0:
        logger.info(
            f"llm extend knowledge task: "
            f"avg_summary_time: {total_summary_time / total_success_count:.2f}s, "
            f"avg_extend_time: {total_extend_time / total_success_count:.2f}s"
        )

    return f"successfully extent {len(done_id_list)} node"
