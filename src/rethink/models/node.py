import datetime
import re
from typing import List, Optional, Set, Tuple

from bson import ObjectId
from bson.tz_util import utc

from rethink import config, const
from . import user, tps, utils, db_ops
from .database import COLL
from .search import user_node

AT_PTN = re.compile(r'\[@[\w ]+?]\(([\w/]+?)\)', re.MULTILINE)
CURSOR_AT_PTN = re.compile(r'\s+?@([\w ]*)$')


def __get_linked_nodes(new_md) -> Tuple[set, const.Code]:
    # last first
    cache_current_to_nid: Set[str] = set()

    for match in list(AT_PTN.finditer(new_md))[::-1]:
        l0, l1 = match.span(1)
        link = new_md[l0:l1]
        if link.startswith("/n/"):
            # check existed nodes
            to_nid = link[3:]
            cache_current_to_nid.add(to_nid)
    return cache_current_to_nid, const.Code.OK


def __flush_to_node_ids(
        nid: str,
        orig_to_nid: List[str],
        new_md: str
) -> Tuple[List[str], const.Code]:
    new_to_nid, code = __get_linked_nodes(new_md=new_md)
    if code != const.Code.OK:
        return [], code

    # remove fromNodes for linked nodes
    orig_to_nid = set(orig_to_nid)
    for to_nid in orig_to_nid.difference(new_to_nid):
        db_ops.remove_from_node(from_nid=nid, to_nid=to_nid)

    # add fromNodes for linked nodes
    for to_nid in new_to_nid.difference(orig_to_nid):
        db_ops.node_add_to_set(id_=to_nid, key="fromNodeIds", value=nid)

    return list(new_to_nid), const.Code.OK


def add(
        uid: str,
        md: str,
        type_: int = const.NodeType.MARKDOWN.value,
        from_nid: str = "",
) -> Tuple[Optional[tps.Node], const.Code]:
    if len(md) > const.MD_MAX_LENGTH:
        return None, const.Code.NOTE_EXCEED_MAX_LENGTH
    title, snippet = utils.preprocess_md(md)

    onid = utils.short_uuid()

    from_nids = []
    if from_nid != "":
        from_nids.append(from_nid)
        res = db_ops.node_add_to_set(from_nid, "toNodeIds", onid)
        if res.modified_count != 1:
            return None, const.Code.OPERATION_FAILED

    new_to_node_ids = []
    if md != "":
        new_to_node_ids, code = __flush_to_node_ids(nid=onid, orig_to_nid=[], new_md=md)
        if code != const.Code.OK:
            return None, code
    _id = ObjectId()
    data: tps.Node = {
        "_id": _id,
        "id": onid,
        "title": title,
        "snippet": snippet,
        "md": md,
        "type": type_,
        "disabled": False,
        "inTrash": False,
        "modifiedAt": _id.generation_time,
        "inTrashAt": None,
        "fromNodeIds": from_nids,
        "toNodeIds": new_to_node_ids,
        "searchKeys": utils.txt2search_keys(title),
    }
    res = COLL.nodes.insert_one(data)
    if not res.acknowledged:
        return None, const.Code.OPERATION_FAILED
    res = COLL.unids.update_one(
        {"id": uid},
        {"$push": {"nodeIds": onid}}
    )
    if res.modified_count != 1:
        return None, const.Code.OPERATION_FAILED

    return data, const.Code.OK


def __set_linked_nodes(
        docs: List[tps.Node],
        with_disabled: bool = False,
):
    for doc in docs:
        doc["fromNodes"] = list(
            COLL.nodes.find({
                "id": {"$in": doc["fromNodeIds"]},
                "disabled": with_disabled,
            }))
        doc["toNodes"] = list(
            COLL.nodes.find({
                "id": {"$in": doc["toNodeIds"]},
                "disabled": with_disabled,
            }))


def get(
        uid: str,
        nid: str,
        with_disabled: bool = False,
        in_trash: bool = False,
) -> Tuple[Optional[tps.Node], const.Code]:
    docs, code = get_batch(
        uid=uid,
        nids=[nid],
        with_disabled=with_disabled,
        in_trash=in_trash,
    )
    return docs[0] if len(docs) > 0 else None, code


def get_batch(
        uid: str,
        nids: List[str],
        with_disabled: bool = False,
        in_trash: bool = False,
) -> Tuple[List[tps.Node], const.Code]:
    unids, code = user.get_node_ids(uid=uid)
    if code != const.Code.OK:
        return [], code
    for nid in nids:
        if nid not in unids:
            return [], const.Code.NODE_NOT_EXIST
    assert_conditions = {} if with_disabled else {"disabled": False}
    assert_conditions.update({"inTrash": in_trash})
    docs = db_ops.nodes_get(ids=nids, assert_conditions=assert_conditions)
    if len(docs) != len(nids):
        return [], const.Code.NODE_NOT_EXIST

    __set_linked_nodes(
        docs=docs,
        with_disabled=with_disabled,
    )
    return docs, const.Code.OK


def update(
        uid: str,
        nid: str,
        md: str,
) -> Tuple[Optional[tps.Node], const.Code]:
    if len(md) > const.MD_MAX_LENGTH:
        return None, const.Code.NOTE_EXCEED_MAX_LENGTH
    title, snippet = utils.preprocess_md(md)

    if not user.is_exist(uid=uid):
        return None, const.Code.ACCOUNT_OR_PASSWORD_ERROR
    n, code = get(uid=uid, nid=nid)
    if code != const.Code.OK:
        return None, code
    if n["md"] == md:
        return n, const.Code.OK
    new_data = {
        "title": title,
        "searchKeys": utils.txt2search_keys(title),
        "md": md,
        "snippet": snippet,
        "modifiedAt": datetime.datetime.now(tz=utc),
    }
    new_data["toNodeIds"], code = __flush_to_node_ids(
        nid=n["id"], orig_to_nid=n["toNodeIds"], new_md=md)
    if code != const.Code.OK:
        return None, code

    if not config.is_local_db():
        doc = COLL.nodes.find_one_and_update(
            {"id": nid},
            {"$set": new_data},
            return_document=True,  # return updated doc
        )
    else:
        res = COLL.nodes.update_one(
            {"id": nid},
            {"$set": new_data}
        )
        if res.modified_count != 1:
            return None, const.Code.OPERATION_FAILED
        doc = COLL.nodes.find_one({"id": nid})

    if doc is None:
        return None, const.Code.NODE_NOT_EXIST
    __set_linked_nodes(
        docs=[doc],
        with_disabled=False,
    )
    return doc, const.Code.OK


def cursor_query(
        uid: str,
        nid: str,
        cursor_text: str,
) -> List[tps.Node]:
    # if cursor_text.startswith("@"):
    #     query = cursor_text[1:].strip()
    # else:
    #     found = CURSOR_AT_PTN.search(cursor_text)
    #     if found is None:
    #         return None, []
    #     query = found.group(1).strip()

    query = cursor_text.strip()

    if query == "":
        u = COLL.users.find_one({"id": uid})
        if u is None:
            return []
        rn = u["recentCursorSearchSelectedNIds"]
        try:
            rn.remove(nid)
        except ValueError:
            pass
        return sorted(list(COLL.nodes.find({"id": {"$in": rn}})), key=lambda x: rn.index(x["id"]))
    nodes_found, _ = user_node(
        uid=uid,
        query=query,
        sort_key="modifiedAt",
        sort_order=-1,
        page=0,
        page_size=8,
        nid_exclude=[nid],
    )
    return nodes_found


def to_trash(uid: str, nid: str) -> const.Code:
    return batch_to_trash(uid=uid, nids=[nid])


def batch_to_trash(uid: str, nids: List[str]) -> const.Code:
    ns, code = get_batch(uid=uid, nids=nids, with_disabled=True, in_trash=False)
    if code != const.Code.OK:
        return code
    u = COLL.users.find_one({"id": uid})
    changed = False
    for n in ns:
        try:
            u["recentCursorSearchSelectedNIds"].remove(n["id"])
            changed = True
        except ValueError:
            pass
    if changed:
        res = COLL.users.update_one({"id": uid}, {"$set": {
            "recentCursorSearchSelectedNIds": u["recentCursorSearchSelectedNIds"]
        }})
        if res.modified_count != 1:
            return const.Code.OPERATION_FAILED
    res = COLL.nodes.update_many({"id": {"$in": nids}}, {"$set": {
        "inTrash": True,
        "inTrashAt": datetime.datetime.now(tz=utc)
    }})
    if res.modified_count != len(nids):
        return const.Code.OPERATION_FAILED
    return const.Code.OK


def get_nodes_in_trash(uid: str, page: int, page_size: int) -> Tuple[List[tps.Node], int]:
    unids, code = user.get_node_ids(uid=uid)
    if code != const.Code.OK:
        return [], 0

    condition = {
        "id": {"$in": unids},
        "disabled": False,
        "inTrash": True,
    }
    docs = COLL.nodes.find(condition).sort("inTrashAt", direction=-1)
    total = COLL.nodes.count_documents(condition)
    if page_size > 0:
        docs = docs.skip(page * page_size).limit(page_size)

    return list(docs), total


def restore_from_trash(uid: str, nid: str) -> const.Code:
    return restore_batch_from_trash(uid=uid, nids=[nid])


def restore_batch_from_trash(uid: str, nids: List[str]) -> const.Code:
    ns, code = get_batch(uid=uid, nids=nids, with_disabled=False, in_trash=True)
    if code != const.Code.OK:
        return code

    # remove nodes
    res = COLL.nodes.update_many({"id": {"$in": nids}}, {"$set": {
        "inTrash": False,
        "inTrashAt": None,
    }})
    if res.modified_count != len(nids):
        return const.Code.OPERATION_FAILED
    return const.Code.OK


def delete(uid: str, nid: str) -> const.Code:
    return batch_delete(uid=uid, nids=[nid])


def batch_delete(uid: str, nids: List[str]) -> const.Code:
    ns, code = get_batch(uid=uid, nids=nids, with_disabled=True, in_trash=True)
    if code != const.Code.OK:
        return code

    # remove fromNodes for linked nodes, not necessary
    # for n in ns:
    #     for linked_nid in n["fromNodeIds"]:
    #         db_ops.remove_to_node(from_nid=linked_nid, to_nid=n["id"])

    # remove toNodes for linked nodes
    for n in ns:
        for linked_nid in n["toNodeIds"]:
            db_ops.remove_from_node(from_nid=n["id"], to_nid=linked_nid)

    # remove node
    res = COLL.nodes.delete_many({"id": {"$in": nids}})
    if res.deleted_count != len(nids):
        return const.Code.OPERATION_FAILED

    # update user nodeIds
    res = db_ops.remove_nids(uid, nids)
    if res.matched_count != 1:
        return const.Code.OPERATION_FAILED
    return const.Code.OK


def disable(
        uid: str,
        nid: str,
) -> const.Code:
    if not user.is_exist(uid=uid):
        return const.Code.ACCOUNT_OR_PASSWORD_ERROR
    res = COLL.nodes.update_one(
        {"id": nid},
        {"$set": {"disabled": True}}
    )
    if res.modified_count != 1:
        return const.Code.OPERATION_FAILED
    return const.Code.OK


def new_user_add_default_nodes(language: str, uid: str) -> const.Code:
    lns = const.NEW_USER_DEFAULT_NODES[language]
    n, code = add(
        uid=uid,
        md=lns[0],
    )
    if code != const.Code.OK:
        return code
    _, code = add(
        uid=uid,
        md=lns[1].format(n["id"]),
    )
    return code
