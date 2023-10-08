import datetime
import re
from typing import List, Optional, Sequence, Set, Tuple

from bson import ObjectId
from bson.tz_util import utc

from rethink import config, const
from . import user, tps, utils, db_ops
from .database import COLL

AT_PTN = re.compile(r'\[@[\w ]+?]\(([\w/]+?)\)', re.MULTILINE)
TITLE_PTN = re.compile(r'^#*?\s*?(.+?)\s*$', re.MULTILINE)
CURSOR_AT_PTN = re.compile(r'\s+?@([\w ]*)$')


def __get_linked_nodes(new_text) -> Tuple[set, const.Code]:
    # last first
    cache_current_to_nid: Set[str] = set()

    for match in list(AT_PTN.finditer(new_text))[::-1]:
        l0, l1 = match.span(1)
        link = new_text[l0:l1]
        if link.startswith("/n/"):
            # check existed nodes
            to_nid = link[3:]
            cache_current_to_nid.add(to_nid)
    return cache_current_to_nid, const.Code.OK


def __flush_to_node_ids(
        nid: str,
        orig_to_nid: List[str],
        new_text: str
) -> Tuple[List[str], const.Code]:
    new_to_nid, code = __get_linked_nodes(new_text=new_text)
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


def __verify_title(title: str) -> bool:
    if title == "":
        return True
    found = TITLE_PTN.match(title)
    if found is None:
        return False
    return True


def add(
        uid: str,
        title: str,
        text: str,
        type_: int = const.NodeType.MARKDOWN.value,
        from_nid: str = "",
) -> Tuple[Optional[tps.Node], const.Code]:
    title = title.strip()
    if __verify_title(title=title) is False:
        return None, const.Code.INVALID_TITLE
    text = text.strip()
    onid = utils.short_uuid()

    from_nids = []
    if from_nid != "":
        from_nids.append(from_nid)
        res = db_ops.node_add_to_set(from_nid, "toNodeIds", onid)
        if res.modified_count != 1:
            return None, const.Code.OPERATION_FAILED

    new_to_node_ids = []
    if text != "":
        new_to_node_ids, code = __flush_to_node_ids(nid=onid, orig_to_nid=[], new_text=text)
        if code != const.Code.OK:
            return None, code
    _id = ObjectId()
    data: tps.Node = {
        "_id": _id,
        "id": onid,
        "title": title,
        "text": text,
        "snippet": utils.md2txt(text=text)[:200],
        "type": type_,
        "disabled": False,
        "inTrash": False,
        "modifiedAt": _id.generation_time,
        "inTrashAt": None,
        "fromNodeIds": from_nids,
        "toNodeIds": new_to_node_ids,
        "searchKeys": utils.text2search_keys(title),
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


def __set_linked_nodes(doc: tps.Node):
    doc["fromNodes"] = list(COLL.nodes.find({"id": {"$in": doc["fromNodeIds"]}}))
    doc["toNodes"] = list(COLL.nodes.find({"id": {"$in": doc["toNodeIds"]}}))


def get(
        uid: str,
        nid: str,
        with_disabled: bool = False,
        in_trash: bool = False,
) -> Tuple[Optional[tps.Node], const.Code]:
    unids, code = user.get_node_ids(uid=uid)
    if code != const.Code.OK:
        return None, code
    if nid not in unids:
        return None, const.Code.NODE_NOT_EXIST
    assert_conditions = {} if with_disabled else {"disabled": False}
    assert_conditions.update({"inTrash": in_trash})
    doc = db_ops.node_get(id_=nid, assert_conditions=assert_conditions)
    if doc is None:
        return None, const.Code.NODE_NOT_EXIST

    __set_linked_nodes(doc=doc)
    return doc, const.Code.OK


def update(
        uid: str,
        nid: str,
        title: str = "",
        text: str = "",
) -> Tuple[Optional[tps.Node], const.Code]:
    title = title.strip()
    if __verify_title(title=title) is False:
        return None, const.Code.INVALID_TITLE
    text = text.strip()

    if not user.is_exist(uid=uid):
        return None, const.Code.ACCOUNT_OR_PASSWORD_ERROR
    n, code = get(uid=uid, nid=nid)
    if code != const.Code.OK:
        return None, code
    if n["title"] == title and n["text"] == text:
        return n, const.Code.OK
    new_data = {"title": title, "searchKeys": utils.text2search_keys(title), }
    if text != n["text"]:
        new_data["toNodeIds"], code = __flush_to_node_ids(
            nid=n["id"], orig_to_nid=n["toNodeIds"], new_text=text)
        if code != const.Code.OK:
            return None, code
        new_data["text"] = text
        new_data["snippet"] = utils.md2txt(text=text)[:200]
    new_data["modifiedAt"] = datetime.datetime.now(tz=utc)

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
    __set_linked_nodes(doc=doc)
    return doc, const.Code.OK


def cursor_query(
        uid: str,
        nid: str,
        cursor_text: str,
) -> Tuple[Optional[str], List[tps.Node]]:
    if cursor_text.startswith("@"):
        query = cursor_text[1:].strip()
    else:
        found = CURSOR_AT_PTN.search(cursor_text)
        if found is None:
            return None, []
        query = found.group(1).strip()

    if query == "":
        u = COLL.users.find_one({"id": uid})
        if u is None:
            return query, []
        rn = u["recentSearchedNodeIds"]
        try:
            rn.remove(nid)
        except ValueError:
            pass
        return query, list(COLL.nodes.find({"id": {"$in": rn}}))
    return query, search_user_node(
        uid=uid,
        query=query,
        sort_key="modifiedAt",
        sort_order=-1,
        page=0,
        page_size=8,
        nid_exclude=[nid],
    )


def to_trash(uid: str, nid: str) -> const.Code:
    n, code = get(uid=uid, nid=nid, with_disabled=True, in_trash=False)
    if code != const.Code.OK:
        return code

    # remove node
    u = COLL.users.find_one({"id": uid})
    try:
        u["recentSearchedNodeIds"].remove(nid)
    except ValueError:
        pass
    else:
        res = COLL.users.update_one({"id": uid}, {"$set": {
            "recentSearchedNodeIds": u["recentSearchedNodeIds"]
        }})
        if res.modified_count != 1:
            return const.Code.OPERATION_FAILED
    res = COLL.nodes.update_one({"id": nid}, {"$set": {
        "inTrash": True,
        "inTrashAt": datetime.datetime.now(tz=utc)
    }})
    if res.modified_count != 1:
        return const.Code.OPERATION_FAILED
    return const.Code.OK


def get_nodes_in_trash(uid: str, page: int, page_size: int) -> List[tps.Node]:
    unids, code = user.get_node_ids(uid=uid)
    if code != const.Code.OK:
        return []

    condition = {
        "id": {"$in": unids},
        "disabled": False,
        "inTrash": True,
    }
    docs = COLL.nodes.find(condition).sort("inTrashAt", direction=-1)

    if page_size > 0:
        docs = docs.skip(page * page_size).limit(page_size)

    return list(docs)


def restore_from_trash(uid: str, nid: str) -> const.Code:
    n, code = get(uid=uid, nid=nid, with_disabled=False, in_trash=True)
    if code != const.Code.OK:
        return code

    # remove node
    res = COLL.nodes.update_one({"id": nid}, {"$set": {
        "inTrash": False,
        "inTrashAt": None,
    }})
    if res.modified_count != 1:
        return const.Code.OPERATION_FAILED
    return const.Code.OK


def delete(uid: str, nid: str) -> const.Code:
    n, code = get(uid=uid, nid=nid, with_disabled=True, in_trash=True)
    if code != const.Code.OK:
        return code

    # remove fromNodes for linked nodes, not necessary
    # for linked_nid in n["fromNodeIds"]:
    #     db_ops.remove_to_node(from_nid=linked_nid, to_nid=nid)

    # remove toNodes for linked nodes
    for linked_nid in n["toNodeIds"]:
        db_ops.remove_from_node(from_nid=nid, to_nid=linked_nid)

    # remove node
    res = COLL.nodes.delete_one({"id": nid})
    if res.deleted_count != 1:
        return const.Code.OPERATION_FAILED

    # update user nodeIds
    res = db_ops.unids_pull(uid, "nodeIds", nid)
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


def search_user_node(
        uid: str,
        query: str = "",
        sort_key: str = "createAt",
        sort_order: int = -1,
        page: int = 0,
        page_size: int = 0,
        nid_exclude: Sequence[str] = None,
) -> List[tps.Node]:
    unids, code = user.get_node_ids(uid=uid)
    if code != const.Code.OK:
        return []

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
        return [doc for doc in docs if query in doc["searchKeys"] or query in doc["text"]]
    return list(docs)


def add_to_recent_history(
        uid: str,
        nid: str,
        to_nid: str,
) -> const.Code:
    # add selected node to recentSearchedNodeIds
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

    rns = u["recentSearchedNodeIds"]
    if to_nid in rns:
        rns.remove(to_nid)
    rns.insert(0, to_nid)
    if len(rns) > 10:
        rns = rns[:10]

    # add to recentSearchedNodeIds
    res = COLL.users.update_one(
        {"id": uid},
        {"$set": {"recentSearchedNodeIds": rns}}
    )
    if res.matched_count != 1:
        return const.Code.OPERATION_FAILED

    return const.Code.OK


def new_user_add_default_nodes(language: str, uid: str) -> const.Code:
    lns = const.NEW_USER_DEFAULT_NODES[language]
    n, code = add(
        uid=uid,
        title=lns[0]["title"],
        text=lns[0]["text"],
    )
    if code != const.Code.OK:
        return code
    _, code = add(
        uid=uid,
        title=lns[1]["title"],
        text=lns[1]["text"].format(n["id"]),
    )
    return code
