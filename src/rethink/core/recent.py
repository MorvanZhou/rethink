from typing import List

from rethink import const
from rethink.models.client import client


async def added_at_node(
        uid: str,
        nid: str,
        to_nid: str,
) -> const.Code:
    # add selected node to recentCursorSearchSelectedNIds
    user_c = {"id": uid, "disabled": False}
    node_c = {"uid": uid, "id": {"$in": [nid, to_nid]}}

    # try finding user
    u = await client.coll.users.find_one(user_c)
    if u is None:
        return const.Code.ACCOUNT_OR_PASSWORD_ERROR

    # try finding node
    ns = await client.coll.nodes.find(node_c).to_list(length=None)
    if len(ns) != 2:
        return const.Code.NODE_NOT_EXIST

    rns = u["lastState"]["recentCursorSearchSelectedNIds"]
    if to_nid in rns:
        rns.remove(to_nid)
    rns.insert(0, to_nid)
    if len(rns) > 10:
        rns = rns[:10]

    # add to recentCursorSearchSelectedNIds
    res = await client.coll.users.update_one(
        {"id": uid},
        {"$set": {"lastState.recentCursorSearchSelectedNIds": rns}}
    )
    if res.matched_count != 1:
        return const.Code.OPERATION_FAILED

    return const.Code.OK


async def get_recent_searched(uid: str) -> List[str]:
    doc = await client.coll.users.find_one({"id": uid})
    if doc is None:
        return []
    return doc["lastState"]["recentSearch"]


async def put_recent_search(uid: str, query: str) -> const.Code:
    doc = await client.coll.users.find_one({"id": uid})
    if doc is None:
        return const.Code.ACCOUNT_OR_PASSWORD_ERROR
    rns = doc["lastState"]["recentSearch"]
    try:
        rns.remove(query)
    except ValueError:
        pass
    rns.insert(0, query)
    if len(rns) > 20:
        rns = rns[:20]
    _ = await client.coll.users.update_one(
        {"id": uid},
        {"$set": {"lastState.recentSearch": rns}}
    )
    return const.Code.OK
