from datetime import timedelta

from bson import ObjectId
from bson.tz_util import utc

from retk.models.client import client
from retk.models.tps.llm import NodeExtendQueue
from retk.models.tps.node import Node
from .. import api


async def extend_on_node_post(data: Node):
    if data["md"].strip() == "":
        return
    q: NodeExtendQueue = NodeExtendQueue(
        _id=ObjectId(),
        uid=data["uid"],
        nid=data["id"],
        modifiedAt=int(data["modifiedAt"].replace(tzinfo=utc).timestamp()),
        summaryService="baidu",
        summaryModel=api.BaiduModelEnum.ERNIE_SPEED_8K.value.key,
        extendService="moonshot",
        extendModel=api.MoonshotModelEnum.V1_8K.value.key,
    )

    # sort by _id desc
    docs = await client.coll.llm_extend_node_queue.find(
        filter={"uid": data["uid"]}
    ).sort("modifiedAt", -1).to_list(None)
    has_q = False
    for doc in docs:
        if doc["nid"] == data["id"]:
            has_q = True
            # renew the creating time
            await client.coll.llm_extend_node_queue.update_one(
                filter={"_id": doc["_id"]},
                update={"$set": {"modifiedAt": q["modifiedAt"]}},
            )
            break

    max_keep = 5
    if not has_q:
        # this is a new node in queue
        if len(docs) >= max_keep:
            # remove the oldest and only keep the latest 5
            await client.coll.llm_extend_node_queue.delete_many(
                {"_id": {"$in": [doc["_id"] for doc in docs[max_keep:]]}}
            )
        await client.coll.llm_extend_node_queue.insert_one(q)


async def extend_on_node_update(
        old_data: Node,
        new_data: Node,
        cooling_time: int = 60,
):
    # filter out frequent updates
    if new_data["modifiedAt"] - old_data["modifiedAt"] < timedelta(seconds=cooling_time):
        return
    await extend_on_node_post(new_data)
