import asyncio
from datetime import datetime, timedelta

from bson.tz_util import utc

from retk import config
from retk.models.client import init_mongo
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

    # Delete all old nodes in trash
    result = await db[CollNameEnum.nodes.value].delete_many({
        "_id": {"$in": [node["_id"] for node in old_nodes]}
    })
    return result.deleted_count
