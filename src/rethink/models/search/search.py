from typing import List, Tuple, Sequence

from rethink import const, config
from .. import tps
from ..database import COLL


async def user_node(
        uid: str,
        query: str = "",
        sort_key: str = "createdAt",
        sort_order: int = -1,
        page: int = 0,
        page_size: int = 0,
        nid_exclude: Sequence[str] = None,
) -> Tuple[List[tps.Node], int]:
    condition = {
        "uid": uid,
        "disabled": False,
        "inTrash": False,
    }
    if nid_exclude is not None and len(nid_exclude) > 0:
        condition["id"] = {"$nin": nid_exclude}

    total = await COLL.nodes.count_documents(condition)

    query = query.strip().lower()

    # on remote mongodb
    if query != "" and not config.is_local_db():
        condition["$or"] = [
            {"searchKeys": {"$regex": query}},
            {"md": {"$regex": query}},
        ]

    docs = COLL.nodes.find(condition)

    if sort_key != "":
        if sort_key == "createdAt":
            sort_key = "_id"
        elif sort_key == "similarity":
            sort_key = "_id"  # TODO: sort by similarity
        docs = docs.sort([(sort_key, sort_order), ("_id", -1)])

    if config.is_local_db() and query != "":
        docs = filter(lambda d: query in d["searchKeys"] or query in d["md"], await docs.to_list(length=None))
        docs = list(docs)
        if page_size > 0:
            docs = docs[page * page_size: (page + 1) * page_size]
        return docs, total

    if page_size > 0:
        docs = docs.skip(page * page_size).limit(page_size)
    return await docs.to_list(length=None), total


async def add_recent_cursor_search(
        uid: str,
        nid: str,
        to_nid: str,
) -> const.Code:
    # add selected node to recentCursorSearchSelectedNIds
    user_c = {"id": uid, "disabled": False}
    node_c = {"uid": uid, "id": {"$in": [nid, to_nid]}}

    # try finding user
    u = await COLL.users.find_one(user_c)
    if u is None:
        return const.Code.ACCOUNT_OR_PASSWORD_ERROR

    # try finding node
    ns = await COLL.nodes.find(node_c).to_list(length=None)
    if len(ns) != 2:
        return const.Code.NODE_NOT_EXIST

    rns = u["lastState"]["recentCursorSearchSelectedNIds"]
    if to_nid in rns:
        rns.remove(to_nid)
    rns.insert(0, to_nid)
    if len(rns) > 10:
        rns = rns[:10]

    # add to recentCursorSearchSelectedNIds
    res = await COLL.users.update_one(
        {"id": uid},
        {"$set": {"lastState.recentCursorSearchSelectedNIds": rns}}
    )
    if res.matched_count != 1:
        return const.Code.OPERATION_FAILED

    return const.Code.OK


async def get_recent_search(uid: str) -> List[str]:
    doc = await COLL.users.find_one({"id": uid})
    if doc is None:
        return []
    return doc["lastState"]["recentSearch"]


async def put_recent_search(uid: str, query: str) -> const.Code:
    doc = await COLL.users.find_one({"id": uid})
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
    _ = await COLL.users.update_one(
        {"id": uid},
        {"$set": {"lastState.recentSearch": rns}}
    )
    return const.Code.OK
