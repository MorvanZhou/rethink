from datetime import timedelta

from bson import ObjectId

from retk.models.client import client
from retk.models.tps.llm import NodeExtendQueue
from retk.models.tps.node import Node
from .. import api

TOP_P = 0.9
TEMPERATURE = 0.5
TIMEOUT = 60

LLM_SERVICES = {
    "tencent": api.TencentService(top_p=TOP_P, temperature=TEMPERATURE, timeout=TIMEOUT),
    "ali": api.AliyunService(top_p=TOP_P, temperature=TEMPERATURE, timeout=TIMEOUT),
    "openai": api.OpenaiService(top_p=TOP_P, temperature=TEMPERATURE, timeout=TIMEOUT),
    "moonshot": api.MoonshotService(top_p=TOP_P, temperature=TEMPERATURE, timeout=TIMEOUT),
    "xf": api.XfYunService(top_p=TOP_P, temperature=TEMPERATURE, timeout=TIMEOUT),
    "baidu": api.BaiduService(top_p=TOP_P, temperature=TEMPERATURE, timeout=TIMEOUT),
}


async def extend_on_node_post(data: Node):
    q: NodeExtendQueue = NodeExtendQueue(
        _id=ObjectId(),
        uid=data["uid"],
        nid=data["id"],
        summaryService="tencent",
        summaryModel=api.TencentModelEnum.HUNYUAN_LITE.value,
        extendService="ali",
        extendModel=api.AliyunModelEnum.QWEN_PLUS.value,
    )

    # sort by _id desc
    docs = await client.coll.llm_extend_node_queue.find(
        filter={"uid": data["uid"]}
    ).sort("_id", -1).to_list(None)
    has_q = False
    for doc in docs:
        if doc["nid"] == data["id"]:
            has_q = True
            q["_id"] = doc["_id"]
            # renew the creating time
            await client.coll.llm_extend_knowledge_queue.update_one(
                filter={"_id": doc["_id"]},
                update={"_id": q["_id"]},
            )
            break

    max_keep = 5
    if not has_q:
        if len(docs) >= max_keep:
            # remove the oldest and only keep the latest 5
            await client.coll.llm_extend_node_queue.delete_many(
                {"_id": {"$in": [doc["_id"] for doc in docs[max_keep:]]}}
            )

        await client.coll.llm_extend_node_queue.insert_one(q)


async def extend_on_node_update(old_data: Node, new_data: Node):
    # filter out frequent updates
    if new_data["modifiedAt"] - old_data["modifiedAt"] < timedelta(seconds=60):
        return

    await extend_on_node_post(new_data)
