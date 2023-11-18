from typing import Any

from rethink import config
from rethink.mongita.results import UpdateResult
from .database import COLL


async def remove_from_node(from_nid: str, to_nid: str):
    if config.is_local_db():
        # no $pull support
        to_n = await COLL.nodes.find_one({"id": to_nid})
        if to_n is None:
            return
        try:
            to_n["fromNodeIds"].remove(from_nid)
            await COLL.nodes.update_one(
                {"id": to_nid},
                {"$set": {"fromNodeIds": to_n["fromNodeIds"]}}
            )
        except ValueError:
            pass
    else:
        await COLL.nodes.update_one(
            {"id": to_nid},
            {"$pull": {"fromNodeIds": from_nid}}
        )


async def node_add_to_set(id_: str, key: str, value: Any) -> UpdateResult:
    res = UpdateResult(0, 0)
    if config.is_local_db():
        # no $addToSet support
        has_new = False
        doc = await COLL.nodes.find_one({"id": id_})
        if doc is None:
            return res
        if key not in doc:
            doc[key] = []
        if value not in doc[key]:
            doc[key].append(value)
            has_new = True
        if has_new:
            res = await COLL.nodes.update_one(
                {"id": id_},
                {"$set": {key: doc[key]}}
            )
    else:
        res = await COLL.nodes.update_one(
            {"id": id_},
            {"$addToSet": {key: value}}
        )
    return res
