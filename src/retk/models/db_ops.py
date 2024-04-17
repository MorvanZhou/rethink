from typing import Any

from retk import config
from retk.depend.mongita.results import UpdateResult
from .client import client


async def remove_from_node(from_nid: str, to_nid: str):
    if config.is_local_db():
        # no $pull support
        to_n = await client.coll.nodes.find_one({"id": to_nid})
        if to_n is None:
            return
        try:
            to_n["fromNodeIds"].remove(from_nid)
            await client.coll.nodes.update_one(
                {"id": to_nid},
                {"$set": {"fromNodeIds": to_n["fromNodeIds"]}}
            )
        except ValueError:
            pass
    else:
        await client.coll.nodes.update_one(
            {"id": to_nid},
            {"$pull": {"fromNodeIds": from_nid}}
        )


async def node_add_to_set(id_: str, key: str, value: Any) -> UpdateResult:
    res = UpdateResult(0, 0)
    if config.is_local_db():
        # no $addToSet support
        has_new = False
        doc = await client.coll.nodes.find_one({"id": id_})
        if doc is None:
            return res
        if key not in doc:
            doc[key] = []
        if value not in doc[key]:
            doc[key].append(value)
            has_new = True
        if has_new:
            res = await client.coll.nodes.update_one(
                {"id": id_},
                {"$set": {key: doc[key]}}
            )
    else:
        res = await client.coll.nodes.update_one(
            {"id": id_},
            {"$addToSet": {key: value}}
        )
    return res


def sort_nodes_by_to_nids(condition: dict, page: int, limit: int):
    if config.is_local_db():
        docs = client.coll.nodes.find(condition).sort(
            [("toNodeIdsLen", -1), ("_id", -1)]
        ).skip(page * limit).limit(limit)
    else:
        docs = client.coll.nodes.aggregate([
            {"$match": condition},
            {"$addFields": {"toNodeIdsLen": {"$size": "$toNodeIds"}}},
            {"$sort": {"toNodeIdsLen": -1}},
            {"$sort": {"_id": -1}},
            {"$skip": page * limit},
            {"$limit": limit},
        ])
    return docs
