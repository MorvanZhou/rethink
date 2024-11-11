import asyncio
from datetime import datetime, timedelta

from bson.tz_util import utc

from retk import config, const
from retk.core.node import backup
from retk.logger import logger
from retk.models.client import init_mongo, init_search
from retk.models.coll import CollNameEnum


def auto_clean_trash(delta_days=30):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(_auto_clean_trash(delta_days=delta_days))
    loop.close()
    return res


async def _auto_clean_trash(delta_days=30):
    _, db = init_mongo(connection_timeout=5)
    # Get all nodes in trash
    if config.is_local_db():
        nodes = await db[CollNameEnum.nodes.value].find({
            "inTrash": True
        }).to_list(None)
        old_nodes = [
            node for node in nodes
            if node["inTrashAt"].astimezone(utc) < datetime.now(tz=utc) - timedelta(days=delta_days)
        ]
    else:
        old_nodes = await db[CollNameEnum.nodes.value].find({
            "inTrash": True,
            # Get all nodes in trash that are older than 30 days
            "inTrashAt": {"$lt": datetime.now(tz=utc) - timedelta(days=delta_days)}
        }).to_list(None)

    uid_nids = {}
    for node in old_nodes:
        uid = node["uid"]
        if uid not in uid_nids:
            uid_nids[uid] = []
        uid_nids[uid].append(node["id"])

    # Delete all old nodes in node_md
    for uid, nids in uid_nids.items():
        backup.delete_node_md(uid=uid, nids=nids)

    used_space_delta = {}
    # remove toNodes for linked nodes
    for n in old_nodes:
        if n["uid"] not in used_space_delta:
            used_space_delta[n["uid"]] = 0
        used_space_delta[n["uid"]] -= len(n["md"].encode("utf-8"))
        for linked_nid in n["toNodeIds"]:
            if config.is_local_db():
                # no $pull support
                to_n = await db[CollNameEnum.nodes.value].find_one({"id": linked_nid})
                if to_n is None:
                    return
                try:
                    to_n["fromNodeIds"].remove(n["id"])
                    await db[CollNameEnum.nodes.value].update_one(
                        {"id": linked_nid},
                        {"$set": {"fromNodeIds": to_n["fromNodeIds"]}}
                    )
                except ValueError:
                    pass
            else:
                await db[CollNameEnum.nodes.value].update_one(
                    {"id": linked_nid},
                    {"$pull": {"fromNodeIds": n["id"]}}
                )

    # Update space
    for uid, delta in used_space_delta.items():
        if delta == 0:
            continue
        await db[CollNameEnum.users.value].update_one(
            {"id": uid},
            {"$inc": {"usedSpace": delta}}
        )

    # Delete all old nodes in trash
    result = await db[CollNameEnum.nodes.value].delete_many({
        "_id": {"$in": [node["_id"] for node in old_nodes]}
    })

    # Delete all old nodes in elastic search
    search = await init_search()
    for uid, nids in uid_nids.items():
        code = await search.delete_batch(uid=uid, nids=nids)
        if code != const.CodeEnum.OK:
            logger.error(f"delete search index failed, code: {code}")
    logger.info(f"auto_clean_trash: {result.deleted_count} nodes deleted")
    return result.deleted_count
