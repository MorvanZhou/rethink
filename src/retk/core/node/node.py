import copy
import datetime
from typing import List, Optional, Tuple, Dict, Any

from bson import ObjectId
from bson.tz_util import utc

from retk import config, const, utils, regex
from retk import plugins
from retk.core import user
from retk.logger import logger
from retk.models import tps, db_ops
from retk.models.client import client
from retk.models.search_engine.engine import SearchDoc
from . import backup, node_utils


@plugins.handler.on_node_added
async def post(  # noqa: C901
        au: tps.AuthedUser,
        md: str,
        type_: int = const.NodeTypeEnum.MARKDOWN.value,
        from_nid: str = "",
) -> Tuple[Optional[tps.Node], const.CodeEnum]:
    md = md.strip()
    if len(md) > const.settings.MD_MAX_LENGTH:
        return None, const.CodeEnum.NOTE_EXCEED_MAX_LENGTH

    new_size = len(md.encode("utf-8"))
    if await user.user_space_not_enough(au=au):
        return None, const.CodeEnum.USER_SPACE_NOT_ENOUGH

    title, body, snippet = utils.preprocess_md(md)

    nid = utils.short_uuid()

    from_nids = []
    if from_nid != "":
        from_nids.append(from_nid)
        res = await db_ops.node_add_to_set(from_nid, "toNodeIds", nid)
        if res.modified_count != 1:
            return None, const.CodeEnum.OPERATION_FAILED

    new_to_node_ids = []
    if md != "":
        new_to_node_ids, code = await node_utils.flush_to_node_ids(nid=nid, orig_to_nid=[], new_md=md)
        if code != const.CodeEnum.OK:
            return None, code
    _id = ObjectId()
    data = utils.get_node_dict(
        _id=_id,
        nid=nid,
        uid=au.u.id,
        md=md,
        title=title,
        snippet=snippet,
        type_=type_,
        disabled=False,
        in_trash=False,
        modified_at=_id.generation_time,
        in_trash_at=None,
        from_node_ids=from_nids,
        to_node_ids=new_to_node_ids,
        history=[],
    )

    res = await client.coll.nodes.insert_one(data)
    if not res.acknowledged:
        return None, const.CodeEnum.OPERATION_FAILED

    await user.update_used_space(uid=au.u.id, delta=new_size)

    code = await backup.storage_md(node=data, keep_hist=False)
    if code != const.CodeEnum.OK:
        return data, code

    if type_ == const.NodeTypeEnum.MARKDOWN.value:
        code = await client.search.add(au=au, doc=SearchDoc(nid=nid, title=title, body=body))
        if code != const.CodeEnum.OK:
            logger.error(f"add search index failed, code: {code}")
    return data, const.CodeEnum.OK


async def get(
        au: tps.AuthedUser,
        nid: str,
        with_disabled: bool = False,
        in_trash: bool = False,
) -> Tuple[Optional[tps.Node], const.CodeEnum]:
    docs, code = await get_batch(
        au=au,
        nids=[nid],
        with_disabled=with_disabled,
        in_trash=in_trash,
    )
    return docs[0] if len(docs) > 0 else None, code


async def get_batch(
        au: tps.AuthedUser,
        nids: List[str],
        with_disabled: bool = False,
        in_trash: bool = False,
) -> Tuple[List[tps.Node], const.CodeEnum]:
    for nid in nids:
        if regex.NID.match(nid) is None:
            logger.error(f"invalid nid: {nid}")
            return [], const.CodeEnum.NODE_NOT_EXIST
    c: Dict[str, Any] = {"uid": au.u.id, "inTrash": in_trash}
    if len(nids) > 1:
        c["id"] = {"$in": nids}
    elif len(nids) == 1:
        c["id"] = nids[0]
    if not with_disabled:
        c["disabled"] = False
    docs = await client.coll.nodes.find(c).to_list(length=None)
    if len(docs) != len(nids):
        logger.error(f"docs len != nids len: {nids}")
        return [], const.CodeEnum.NODE_NOT_EXIST

    await node_utils.set_linked_nodes(
        docs=docs,
        with_disabled=with_disabled,
    )
    return docs, const.CodeEnum.OK


@plugins.handler.on_node_updated
@plugins.handler.before_node_updated
async def update_md(  # noqa: C901
        au: tps.AuthedUser,
        nid: str,
        md: str,
        refresh_on_same_md: bool = False,
) -> Tuple[Optional[tps.Node], Optional[tps.Node], const.CodeEnum]:
    """

    Args:
        au:
        nid:
        md:
        refresh_on_same_md:

    Returns:
        Tuple[Optional[tps.Node], Optional[tps.Node], const.CodeEnum]: new node, old node, code
    """
    if regex.NID.match(nid) is None:
        return None, None, const.CodeEnum.NODE_NOT_EXIST
    md = md.strip()
    if len(md) > const.settings.MD_MAX_LENGTH:
        return None, None, const.CodeEnum.NOTE_EXCEED_MAX_LENGTH
    if await user.user_space_not_enough(au=au):
        return None, None, const.CodeEnum.USER_SPACE_NOT_ENOUGH

    title, body, snippet = utils.preprocess_md(md)

    n, code = await get(au=au, nid=nid)
    if code != const.CodeEnum.OK:
        return None, None, code
    old_n = copy.deepcopy(n)
    if n["md"] == md and not refresh_on_same_md:
        return n, old_n, const.CodeEnum.OK

    old_md_size = len(n["md"].encode("utf-8"))
    new_data = {
        "modifiedAt": datetime.datetime.now(tz=utc),
    }

    if n["title"] != title:
        # update it's title in fromNodes md's link
        from_nodes = await client.coll.nodes.find({"id": {"$in": n["fromNodeIds"]}}).to_list(length=None)
        for from_node in from_nodes:
            new_md = utils.change_link_title(md=from_node["md"], nid=nid, new_title=title)
            n, old_n, code = await update_md(au=au, nid=from_node["id"], md=new_md)
            if code != const.CodeEnum.OK:
                logger.error(f"update fromNode {from_node['id']} failed")
        new_data["title"] = title

    if n["md"] != md:
        new_data["md"] = md
        if n["snippet"] != snippet:
            new_data["snippet"] = snippet

    new_data["toNodeIds"], code = await node_utils.flush_to_node_ids(
        nid=n["id"], orig_to_nid=n["toNodeIds"], new_md=md)
    if code != const.CodeEnum.OK:
        return None, old_n, code

    if not config.is_local_db():
        doc = await client.coll.nodes.find_one_and_update(
            {"id": nid},
            {"$set": new_data},
            return_document=True,  # return updated doc
        )
    else:
        # local db not support find_one_and_update
        res = await client.coll.nodes.update_one(
            {"id": nid},
            {"$set": new_data}
        )
        if res.modified_count != 1:
            logger.error(f"update node {nid} failed")
            return None, old_n, const.CodeEnum.OPERATION_FAILED
        doc = await client.coll.nodes.find_one({"id": nid})

    if doc is None:
        return None, old_n, const.CodeEnum.NODE_NOT_EXIST
    await node_utils.set_linked_nodes(
        docs=[doc],
        with_disabled=False,
    )

    await user.update_used_space(uid=au.u.id, delta=len(md.encode("utf-8")) - old_md_size)

    if doc["type"] == const.NodeTypeEnum.MARKDOWN.value:
        code = await client.search.update(au=au, doc=SearchDoc(nid=nid, title=title, body=body))
        if code != const.CodeEnum.OK:
            logger.error(f"update search index failed, code: {code}")

    code = await backup.storage_md(node=doc, keep_hist=True)
    if code != const.CodeEnum.OK:
        return doc, old_n, code
    return doc, old_n, code


async def to_trash(au: tps.AuthedUser, nid: str) -> const.CodeEnum:
    return await batch_to_trash(au=au, nids=[nid])


async def batch_to_trash(au: tps.AuthedUser, nids: List[str]) -> const.CodeEnum:
    ns, code = await get_batch(au=au, nids=nids, with_disabled=True, in_trash=False)
    if code != const.CodeEnum.OK:
        return code

    recent_cursor_search_selected_nids = au.u.last_state.recent_cursor_search_selected_nids
    changed = False
    for n in ns:
        try:
            recent_cursor_search_selected_nids.remove(n["id"])
            changed = True
        except ValueError:
            pass
    if changed:
        res = await client.coll.users.update_one({"id": au.u.id}, {"$set": {
            "lastState.recentCursorSearchSelectedNIds": recent_cursor_search_selected_nids
        }})
        if res.modified_count != 1:
            logger.error(f"update user {au.u.id} failed")
            return const.CodeEnum.OPERATION_FAILED
    res = await client.coll.nodes.update_many({"id": {"$in": nids}}, {"$set": {
        "inTrash": True,
        "inTrashAt": datetime.datetime.now(tz=utc)
    }})
    if res.modified_count != len(nids):
        logger.error(f"update nodes {nids} failed")
        return const.CodeEnum.OPERATION_FAILED

    code = await client.search.batch_to_trash(au=au, nids=nids)
    if code != const.CodeEnum.OK:
        logger.error(f"update search index failed, code: {code}")
    return code


async def get_nodes_in_trash(
        au: tps.AuthedUser,
        page: int,
        limit: int
) -> Tuple[List[tps.Node], int]:
    condition = {
        "uid": au.u.id,
        "disabled": False,
        "inTrash": True,
    }
    docs = client.coll.nodes.find(condition).sort([("inTrashAt", -1), ("_id", -1)])
    total = await client.coll.nodes.count_documents(condition)
    if limit > 0:
        docs = docs.skip(page * limit).limit(limit)

    return await docs.to_list(length=None), total


async def restore_from_trash(au: tps.AuthedUser, nid: str) -> const.CodeEnum:
    return await restore_batch_from_trash(au=au, nids=[nid])


async def restore_batch_from_trash(au: tps.AuthedUser, nids: List[str]) -> const.CodeEnum:
    # restore nodes
    res = await client.coll.nodes.update_many({"id": {"$in": nids}}, {"$set": {
        "inTrash": False,
        "inTrashAt": None,
    }})
    if res.modified_count != len(nids):
        logger.error(f"restore nodes {nids} failed")
        return const.CodeEnum.OPERATION_FAILED

    code = await client.search.restore_batch_from_trash(au=au, nids=nids)
    if code != const.CodeEnum.OK:
        logger.error(f"restore search index failed, code: {code}")
    return code


async def delete(au: tps.AuthedUser, nid: str) -> const.CodeEnum:
    return await batch_delete(au=au, nids=[nid])


async def batch_delete(au: tps.AuthedUser, nids: List[str]) -> const.CodeEnum:
    ns, code = await get_batch(au=au, nids=nids, with_disabled=True, in_trash=True)
    if code != const.CodeEnum.OK:
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
    await user.update_used_space(uid=au.u.id, delta=used_space_delta)

    # remove node
    res = await client.coll.nodes.delete_many({"id": {"$in": nids}, "uid": au.u.id})
    if res.deleted_count != len(nids):
        logger.error(f"delete nodes {nids} failed")
        return const.CodeEnum.OPERATION_FAILED

    backup.delete_node_md(uid=au.u.id, nids=nids)

    code = await client.search.delete_batch(au=au, nids=nids)
    if code != const.CodeEnum.OK:
        logger.error(f"delete search index failed, code: {code}")

    return code


async def disable(
        au: tps.AuthedUser,
        nid: str,
) -> const.CodeEnum:
    if regex.NID.match(nid) is None:
        return const.CodeEnum.NODE_NOT_EXIST
    res = await client.coll.nodes.update_one(
        {"id": nid},
        {"$set": {"disabled": True}}
    )
    if res.modified_count != 1:
        logger.error(f"disable node {nid} failed")
        return const.CodeEnum.OPERATION_FAILED
    code = await client.search.disable(au=au, nid=nid)
    if code != const.CodeEnum.OK:
        logger.error(f"disable search index failed, code: {code}")
    return const.CodeEnum.OK


async def core_nodes(
        au: tps.AuthedUser,
        page: int,
        limit: int,
) -> Tuple[List[tps.Node], int]:
    condition = {
        "uid": au.u.id,
        "disabled": False,
        "inTrash": False,
    }
    # the key of toNodeIds is a list, sort by the toNodeIds length, from large to small
    docs = db_ops.sort_nodes_by_to_nids(condition=condition, page=page, limit=limit)
    total = await client.coll.nodes.count_documents(condition)
    return await docs.to_list(length=None), total


async def new_user_add_default_nodes(language: str, uid: str) -> const.CodeEnum:
    lns = const.NEW_USER_DEFAULT_NODES[language]
    u = await client.coll.users.find_one({"id": uid})
    if u is None:
        return const.CodeEnum.USER_NOT_EXIST
    au = tps.AuthedUser(u=tps.convert_user_dict_to_authed_user(u), language=language, request_id="")
    n, code = await post(
        au=au,
        md=lns[0],
    )
    if code != const.CodeEnum.OK:
        return code
    _, code = await post(
        au=au,
        md=lns[1].format(n["id"]),
    )
    await client.search.refresh()
    return code


async def get_hist_editions(
        au: tps.AuthedUser,
        nid: str
) -> Tuple[List[str], const.CodeEnum]:
    """

    Args:
        au:
        nid:

    Returns:
        Tuple[List[str], const.CodeEnum]: history, code
    """
    n, code = await get(au=au, nid=nid)
    if code != const.CodeEnum.OK:
        return [], code
    return n.get("history", []), const.CodeEnum.OK


async def get_hist_edition_md(au: tps.AuthedUser, nid: str, version: str) -> Tuple[str, const.CodeEnum]:
    n, code = await get(au=au, nid=nid)
    if code != const.CodeEnum.OK:
        return "", code
    if version not in n["history"]:
        return "", const.CodeEnum.NODE_NOT_EXIST
    return backup.get_md(uid=au.u.id, nid=nid, version=version)
