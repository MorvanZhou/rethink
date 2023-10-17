from typing import List, Tuple, Sequence

from rethink import const, config
from . import user, tps
from .database import COLL


def user_node(
        uid: str,
        query: str = "",
        sort_key: str = "createAt",
        sort_order: int = -1,
        page: int = 0,
        page_size: int = 0,
        nid_exclude: Sequence[str] = None,
) -> Tuple[List[tps.Node], int]:
    unids, code = user.get_node_ids(uid=uid)
    if code != const.Code.OK:
        return [], 0

    if nid_exclude is None or len(nid_exclude) == 0:
        nids = unids
    else:
        nid_exclude = nid_exclude or []
        nid_exclude = set(nid_exclude)
        nids = set(unids)
        nids.difference_update(nid_exclude)
        nids = list(nids)

    condition = {
        "id": {"$in": nids},
        "disabled": False,
        "inTrash": False,
    }
    total = COLL.nodes.count_documents(condition)

    query = query.strip().lower()

    # on remote mongodb
    if query != "" and not config.is_local_db():
        condition["$or"] = [
            {"searchKeys": {"$regex": query}},
            {"text": {"$regex": query}},
        ]

    docs = COLL.nodes.find(condition)

    if sort_key != "":
        if sort_key == "createAt":
            sort_key = "_id"
        elif sort_key == "similarity":
            sort_key = "_id"  # TODO: sort by similarity
        docs = docs.sort(sort_key, direction=sort_order)

    if page_size > 0:
        docs = docs.skip(page * page_size).limit(page_size)

    if config.is_local_db() and query != "":
        return [doc for doc in docs if query in doc["searchKeys"] or query in doc["text"]], total
    return list(docs), total


def add_recent_cursor_search(
        uid: str,
        nid: str,
        to_nid: str,
) -> const.Code:
    # add selected node to recentCursorSearchSelectedNIds
    user_c = {"id": uid}
    unid_c = {"id": uid}

    # on remote mongodb
    if not config.is_local_db():
        user_c.update({"disabled": False})
        unid_c.update({"nodeIds": {"$in": [nid, to_nid]}})

    # try finding user
    u = COLL.users.find_one(user_c)
    if u is None:
        return const.Code.ACCOUNT_OR_PASSWORD_ERROR

    # try finding node
    unids = COLL.unids.find_one(unid_c)
    if unids is None:
        return const.Code.NODE_NOT_EXIST

    # do it on local db
    if config.is_local_db():
        if u["disabled"]:
            return const.Code.ACCOUNT_OR_PASSWORD_ERROR
        if nid not in unids["nodeIds"] or to_nid not in unids["nodeIds"]:
            return const.Code.NODE_NOT_EXIST

    rns = u["recentCursorSearchSelectedNIds"]
    if to_nid in rns:
        rns.remove(to_nid)
    rns.insert(0, to_nid)
    if len(rns) > 10:
        rns = rns[:10]

    # add to recentCursorSearchSelectedNIds
    res = COLL.users.update_one(
        {"id": uid},
        {"$set": {"recentCursorSearchSelectedNIds": rns}}
    )
    if res.matched_count != 1:
        return const.Code.OPERATION_FAILED

    return const.Code.OK


def get_recent_search(uid: str) -> List[tps.Node]:
    if not user.is_exist(uid=uid):
        return []
    doc = COLL.users.find_one({"id": uid})
    nodes = COLL.nodes.find({"id": {"$in": doc["recentSearch"]}})
    return sorted(list(nodes), key=lambda x: doc["recentSearch"].index(x["id"]))


def put_recent_search(uid: str, nid: str) -> const.Code:
    if not user.is_exist(uid=uid):
        return const.Code.ACCOUNT_OR_PASSWORD_ERROR
    doc = COLL.users.find_one({"id": uid})
    if COLL.unids.count_documents({"id": uid, "nodeIds": {"$in": [nid]}}) == 0:
        return const.Code.NODE_NOT_EXIST
    rns = doc["recentSearch"]
    try:
        rns.remove(nid)
    except ValueError:
        pass
    rns.insert(0, nid)
    if len(rns) > 20:
        rns = rns[:20]
    _ = COLL.users.update_one(
        {"id": uid},
        {"$set": {"recentSearch": rns}}
    )
    return const.Code.OK
