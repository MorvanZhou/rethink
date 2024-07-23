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
    batch_size = 40
    total_success_count = 0
    total_summary_time = 0
    total_extend_time = 0
    while True:
        done_id_list = []
        batch: List[NodeExtendQueue] = await db[CollNameEnum.llm_extend_node_queue.value].find().limit(
            batch_size).to_list(None)
        if len(batch) == 0:
            break
        cases: List[knowledge.ExtendCase] = []
        req_id = "".join([str(random.randint(0, 9)) for _ in range(10)])

        for item in batch:
            node = await db[CollNameEnum.nodes.value].find_one({"id": item["nid"]})
            cases.append(
                knowledge.ExtendCase(
                    _id=item["_id"],
                    uid=item["uid"],
                    nid=item["nid"],
                    summary_service=item["summaryService"],
                    summary_model=item["summaryModel"],
                    extend_service=item["extendService"],
                    extend_model=item["extendModel"],
                    md=node["md"],
                )
            )

        s0 = time.perf_counter()
        cases = await knowledge.batch_summary(
            cases=cases,
            req_id=req_id,
        )
        s1 = time.perf_counter()

        e0 = time.perf_counter()
        cases = await knowledge.batch_extend(
            cases=cases,
            req_id=req_id,
        )
        e1 = time.perf_counter()

        for case in cases:
            done_id_list.append(case._id)
            if case.summary_code != const.CodeEnum.OK or case.extend_code != const.CodeEnum.OK:
                continue
            ext = ExtendedNode(
                uid=case.uid,
                sourceNid=case.nid,
                sourceMd=case.md,
                extendMd=case.extend_md,
                extendSearchTerms=case.extend_search_terms,
            )
            await db[CollNameEnum.llm_extended_node.value].update_one(
                {"uid": case.uid, "sourceNid": case.nid},
                {"$set": ext},
                upsert=True
            )

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
