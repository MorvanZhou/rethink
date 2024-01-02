import datetime
import re
from pathlib import Path
from typing import List, Optional, Set, Tuple, Dict, Any

from bson import ObjectId
from bson.tz_util import utc

from rethink import config, const
from rethink.logger import logger
from rethink.models.search_engine.engine import SearchDoc
from . import user, tps, utils, db_ops
from .database import COLL, searcher

AT_PTN = re.compile(r'\[@[ \w\u4e00-\u9fa5！？。，￥【】「」]+?]\(([\w/]+?)\)', re.MULTILINE)
CURSOR_AT_PTN = re.compile(r'\s+?@([\w ]*)$')
NID_PTN = re.compile(fr"^[A-Za-z0-9]{{20,{const.NID_MAX_LENGTH}}}$")


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


async def __flush_to_node_ids(
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
        await db_ops.remove_from_node(from_nid=nid, to_nid=to_nid)

    # add fromNodes for linked nodes
    for to_nid in new_to_nid.difference(orig_to_nid):
        await db_ops.node_add_to_set(id_=to_nid, key="fromNodeIds", value=nid)

    return list(new_to_nid), const.Code.OK


def __local_usage_write_file(nid: str, md: str):
    if not config.is_local_db():
        return
    md_dir = Path(config.get_settings().LOCAL_STORAGE_PATH) / ".data" / "md"
    md_dir.mkdir(parents=True, exist_ok=True)
    with open(md_dir / f"{nid}.md", "w", encoding="utf-8") as f:
        f.write(md)


def __local_usage_delete_files(nids: List[str]):
    if not config.is_local_db():
        return
    dir_ = Path(config.get_settings().LOCAL_STORAGE_PATH) / ".data" / "md"
    for nid in nids:
        md_dir = dir_ / f"{nid}.md"
        if md_dir.exists():
            md_dir.unlink()


async def add(
        uid: str,
        md: str,
        type_: int = const.NodeType.MARKDOWN.value,
        from_nid: str = "",
) -> Tuple[Optional[tps.Node], const.Code]:
    md = md.strip()
    if len(md) > const.MD_MAX_LENGTH:
        return None, const.Code.NOTE_EXCEED_MAX_LENGTH

    u, code = await user.get(uid=uid)
    if code != const.Code.OK:
        return None, code

    new_size = len(md.encode("utf-8"))
    if await user.user_space_not_enough(u=u):
        return None, const.Code.USER_SPACE_NOT_ENOUGH

    title, body, snippet = utils.preprocess_md(md)

    nid = utils.short_uuid()

    from_nids = []
    if from_nid != "":
        from_nids.append(from_nid)
        res = await db_ops.node_add_to_set(from_nid, "toNodeIds", nid)
        if res.modified_count != 1:
            return None, const.Code.OPERATION_FAILED

    new_to_node_ids = []
    if md != "":
        new_to_node_ids, code = await __flush_to_node_ids(nid=nid, orig_to_nid=[], new_md=md)
        if code != const.Code.OK:
            return None, code
    _id = ObjectId()
    data: tps.Node = {
        "_id": _id,
        "id": nid,
        "uid": uid,
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
    }
    res = await COLL.nodes.insert_one(data)
    if not res.acknowledged:
        return None, const.Code.OPERATION_FAILED

    await user.update_used_space(uid=uid, delta=new_size)

    __local_usage_write_file(nid=nid, md=md)

    if type_ == const.NodeType.MARKDOWN.value:
        code = await searcher().add(uid=uid, doc=SearchDoc(nid=nid, title=title, body=body))
        if code != const.Code.OK:
            logger.error(f"add search index failed, code: {code}")
    return data, const.Code.OK


async def __set_linked_nodes(
        docs: List[tps.Node],
        with_disabled: bool = False,
):
    for doc in docs:
        doc["fromNodes"] = await COLL.nodes.find({
            "id": {"$in": doc["fromNodeIds"]},
            "disabled": with_disabled,
        }).to_list(length=None)
        doc["toNodes"] = await COLL.nodes.find({
            "id": {"$in": doc["toNodeIds"]},
            "disabled": with_disabled,
        }).to_list(length=None)


async def get(
        uid: str,
        nid: str,
        with_disabled: bool = False,
        in_trash: bool = False,
) -> Tuple[Optional[tps.Node], const.Code]:
    docs, code = await get_batch(
        uid=uid,
        nids=[nid],
        with_disabled=with_disabled,
        in_trash=in_trash,
    )
    return docs[0] if len(docs) > 0 else None, code


async def get_batch(
        uid: str,
        nids: List[str],
        with_disabled: bool = False,
        in_trash: bool = False,
) -> Tuple[List[tps.Node], const.Code]:
    for nid in nids:
        if NID_PTN.match(nid) is None:
            logger.error(f"invalid nid: {nid}")
            return [], const.Code.NODE_NOT_EXIST
    c: Dict[str, Any] = {"uid": uid, "inTrash": in_trash}
    if len(nids) > 1:
        c["id"] = {"$in": nids}
    elif len(nids) == 1:
        c["id"] = nids[0]
    if not with_disabled:
        c["disabled"] = False
    docs = await COLL.nodes.find(c).to_list(length=None)
    if len(docs) != len(nids):
        logger.error(f"docs len != nids len: {nids}")
        return [], const.Code.NODE_NOT_EXIST

    await __set_linked_nodes(
        docs=docs,
        with_disabled=with_disabled,
    )
    return docs, const.Code.OK


async def update(
        uid: str,
        nid: str,
        md: str,
        refresh_on_same_md: bool = False,
) -> Tuple[Optional[tps.Node], const.Code]:
    if NID_PTN.match(nid) is None:
        return None, const.Code.NODE_NOT_EXIST
    md = md.strip()
    if len(md) > const.MD_MAX_LENGTH:
        return None, const.Code.NOTE_EXCEED_MAX_LENGTH
    u, code = await user.get(uid=uid)
    if code != const.Code.OK:
        return None, const.Code.ACCOUNT_OR_PASSWORD_ERROR
    if await user.user_space_not_enough(u=u):
        return None, const.Code.USER_SPACE_NOT_ENOUGH

    title, body, snippet = utils.preprocess_md(md)

    n, code = await get(uid=uid, nid=nid)
    if code != const.Code.OK:
        return None, code
    if n["md"] == md and not refresh_on_same_md:
        return n, const.Code.OK

    old_md_size = len(n["md"].encode("utf-8"))
    new_data = {
        "modifiedAt": datetime.datetime.now(tz=utc),
    }

    if n["title"] != title:
        # update it's title in fromNodes md's link
        from_nodes = await COLL.nodes.find({"id": {"$in": n["fromNodeIds"]}}).to_list(length=None)
        for from_node in from_nodes:
            new_md = utils.change_link_title(md=from_node["md"], nid=nid, new_title=title)
            n, code = await update(uid=uid, nid=from_node["id"], md=new_md)
            if code != const.Code.OK:
                logger.info(f"update fromNode {from_node['id']} failed")
        new_data["title"] = title

    if n["md"] != md:
        new_data["md"] = md
        if n["snippet"] != snippet:
            new_data["snippet"] = snippet

    new_data["toNodeIds"], code = await __flush_to_node_ids(
        nid=n["id"], orig_to_nid=n["toNodeIds"], new_md=md)
    if code != const.Code.OK:
        return None, code

    if not config.is_local_db():
        doc = await COLL.nodes.find_one_and_update(
            {"id": nid},
            {"$set": new_data},
            return_document=True,  # return updated doc
        )
    else:
        # local db not support find_one_and_update
        res = await COLL.nodes.update_one(
            {"id": nid},
            {"$set": new_data}
        )
        if res.modified_count != 1:
            logger.error(f"update node {nid} failed")
            return None, const.Code.OPERATION_FAILED
        doc = await COLL.nodes.find_one({"id": nid})

    if doc is None:
        return None, const.Code.NODE_NOT_EXIST
    await __set_linked_nodes(
        docs=[doc],
        with_disabled=False,
    )

    await user.update_used_space(uid=uid, delta=len(md.encode("utf-8")) - old_md_size)

    __local_usage_write_file(nid=nid, md=md)
    if doc["type"] == const.NodeType.MARKDOWN.value:
        code = await searcher().update(uid=uid, doc=SearchDoc(nid=nid, title=title, body=body))
        if code != const.Code.OK:
            logger.error(f"update search index failed, code: {code}")
    return doc, code


async def to_trash(uid: str, nid: str) -> const.Code:
    return await batch_to_trash(uid=uid, nids=[nid])


async def batch_to_trash(uid: str, nids: List[str]) -> const.Code:
    ns, code = await get_batch(uid=uid, nids=nids, with_disabled=True, in_trash=False)
    if code != const.Code.OK:
        return code
    u = await COLL.users.find_one({"id": uid})
    changed = False
    for n in ns:
        try:
            u["lastState"]["recentCursorSearchSelectedNIds"].remove(n["id"])
            changed = True
        except ValueError:
            pass
    if changed:
        res = await COLL.users.update_one({"id": uid}, {"$set": {
            "lastState.recentCursorSearchSelectedNIds": u["lastState"]["recentCursorSearchSelectedNIds"]
        }})
        if res.modified_count != 1:
            logger.error(f"update user {uid} failed")
            return const.Code.OPERATION_FAILED
    res = await COLL.nodes.update_many({"id": {"$in": nids}}, {"$set": {
        "inTrash": True,
        "inTrashAt": datetime.datetime.now(tz=utc)
    }})
    if res.modified_count != len(nids):
        logger.error(f"update nodes {nids} failed")
        return const.Code.OPERATION_FAILED

    code = await searcher().batch_to_trash(uid=uid, nids=nids)
    if code != const.Code.OK:
        logger.error(f"update search index failed, code: {code}")
    return code


async def get_nodes_in_trash(uid: str, page: int, page_size: int) -> Tuple[List[tps.Node], int]:
    condition = {
        "uid": uid,
        "disabled": False,
        "inTrash": True,
    }
    docs = COLL.nodes.find(condition).sort([("inTrashAt", -1), ("_id", -1)])
    total = await COLL.nodes.count_documents(condition)
    if page_size > 0:
        docs = docs.skip(page * page_size).limit(page_size)

    return await docs.to_list(length=None), total


async def restore_from_trash(uid: str, nid: str) -> const.Code:
    return await restore_batch_from_trash(uid=uid, nids=[nid])


async def restore_batch_from_trash(uid: str, nids: List[str]) -> const.Code:
    ns, code = await get_batch(uid=uid, nids=nids, with_disabled=False, in_trash=True)
    if code != const.Code.OK:
        return code

    # remove nodes
    res = await COLL.nodes.update_many({"id": {"$in": nids}}, {"$set": {
        "inTrash": False,
        "inTrashAt": None,
    }})
    if res.modified_count != len(nids):
        logger.error(f"restore nodes {nids} failed")
        return const.Code.OPERATION_FAILED

    code = await searcher().restore_batch_from_trash(uid=uid, nids=nids)
    if code != const.Code.OK:
        logger.error(f"restore search index failed, code: {code}")
    return code


async def delete(uid: str, nid: str) -> const.Code:
    return await batch_delete(uid=uid, nids=[nid])


async def batch_delete(uid: str, nids: List[str]) -> const.Code:
    ns, code = await get_batch(uid=uid, nids=nids, with_disabled=True, in_trash=True)
    if code != const.Code.OK:
        return code

    # remove fromNodes for linked nodes, not necessary
    # for n in ns:
    #     for linked_nid in n["fromNodeIds"]:
    #         db_ops.remove_to_node(from_nid=linked_nid, to_nid=n["id"])

    used_space_delta = 0
    # remove toNodes for linked nodes
    for n in ns:
        used_space_delta -= len(n["md"].encode("utf-8"))
        for linked_nid in n["toNodeIds"]:
            await db_ops.remove_from_node(from_nid=n["id"], to_nid=linked_nid)

    # delete user file
    await user.update_used_space(uid=uid, delta=used_space_delta)

    # remove node
    res = await COLL.nodes.delete_many({"id": {"$in": nids}, "uid": uid})
    if res.deleted_count != len(nids):
        logger.error(f"delete nodes {nids} failed")
        return const.Code.OPERATION_FAILED

    __local_usage_delete_files(nids=nids)

    code = await searcher().delete_batch(uid=uid, nids=nids)
    if code != const.Code.OK:
        logger.error(f"delete search index failed, code: {code}")
    return code


async def disable(
        uid: str,
        nid: str,
) -> const.Code:
    if NID_PTN.match(nid) is None:
        return const.Code.NODE_NOT_EXIST
    if not await user.is_exist(uid=uid):
        return const.Code.ACCOUNT_OR_PASSWORD_ERROR
    res = await COLL.nodes.update_one(
        {"id": nid},
        {"$set": {"disabled": True}}
    )
    if res.modified_count != 1:
        logger.error(f"disable node {nid} failed")
        return const.Code.OPERATION_FAILED
    code = await searcher().disable(uid=uid, nid=nid)
    if code != const.Code.OK:
        logger.error(f"disable search index failed, code: {code}")
    return const.Code.OK


async def new_user_add_default_nodes(language: str, uid: str) -> const.Code:
    lns = const.NEW_USER_DEFAULT_NODES[language]
    n, code = await add(
        uid=uid,
        md=lns[0],
    )
    if code != const.Code.OK:
        return code
    _, code = await add(
        uid=uid,
        md=lns[1].format(n["id"]),
    )
    await searcher().refresh()
    return code
