import asyncio
import json
import random
import time
from typing import List

from retk import const, config
from retk.core.ai.llm import knowledge
from retk.core.statistic import add_user_behavior
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


async def get_cases(db, batch: List[NodeExtendQueue]) -> List[knowledge.ExtendCase]:
    cases: List[knowledge.ExtendCase] = []

    nid2item = {item["nid"]: item for item in batch}

    nodes = await db[CollNameEnum.nodes.value].find({"id": {"$in": list(nid2item.keys())}}).to_list(None)
    for node in nodes:
        if node is None:
            continue
        item = nid2item[node["id"]]
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
    return cases


async def update_extended_nodes(db, case: knowledge.ExtendCase):
    ext = ExtendedNode(
        uid=case.uid,
        sourceNid=case.nid,
        sourceMd=case.md,
        extendMd=case.extend_md,
        extendSearchTerms=case.extend_search_terms,
    )
    if config.is_local_db():
        doc = await db[CollNameEnum.llm_extended_node.value].find_one(
            {"uid": case.uid, "sourceNid": case.nid}
        )
        if doc is None:
            await db[CollNameEnum.llm_extended_node.value].insert_one(ext)
        else:
            await db[CollNameEnum.llm_extended_node.value].update_one(
                {"uid": case.uid, "sourceNid": case.nid},
                {"$set": ext}
            )
    else:
        await db[CollNameEnum.llm_extended_node.value].update_one(
            {"uid": case.uid, "sourceNid": case.nid},
            {"$set": ext},
            upsert=True
        )


async def async_deliver_unscheduled_extend_nodes() -> str:
    _, db = init_mongo(connection_timeout=5)
    batch_size = 40
    total_success_count = 0
    total_summary_time = 0
    total_extend_time = 0
    while True:
        done_id_list = []
        batch: List[NodeExtendQueue] = await db[CollNameEnum.llm_extend_node_queue.value].find().limit(
            batch_size
        ).to_list(None)
        if len(batch) == 0:
            break
        req_id = "".join([str(random.randint(0, 9)) for _ in range(10)])
        cases = await get_cases(db, batch)

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
            await add_user_behavior(
                uid=case.uid,
                type_=const.user_behavior_types.UserBehaviorTypeEnum.LLM_KNOWLEDGE_RESPONSE,
                remark=json.dumps(
                    {
                        "md": case.stripped_md,
                        "summary": case.summary,
                        "summaryService": case.summary_service,
                        "summaryModel": case.summary_model,
                        "extend": case.extend_md,
                        "extendService": case.extend_service,
                        "extendModel": case.extend_model,
                    },
                    ensure_ascii=False
                ),
            )
            done_id_list.append(case._id)
            if case.summary_code != const.CodeEnum.OK or case.extend_code != const.CodeEnum.OK:
                continue

            await update_extended_nodes(db, case)

        total_summary_time += s1 - s0
        total_extend_time += e1 - e0

        # remove the batch
        await db[CollNameEnum.llm_extend_node_queue.value].delete_many(
            {"_id": {"$in": [b["_id"] for b in batch]}}
        )

    if len(done_id_list) > 0:
        logger.info(
            f"llm extend knowledge task: "
            f"avg_summary_time: {total_summary_time / total_success_count:.2f}s, "
            f"avg_extend_time: {total_extend_time / total_success_count:.2f}s"
        )

    return f"successfully extent {len(done_id_list)} node"
