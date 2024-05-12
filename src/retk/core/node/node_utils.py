from typing import List, Set, Tuple

from retk import const, regex
from retk.models import tps, db_ops
from retk.models.client import client


def get_linked_nodes(new_md) -> Tuple[set, const.CodeEnum]:
    # last first
    cache_current_to_nid: Set[str] = set()

    for match in list(regex.MD_AT_LINK.finditer(new_md))[::-1]:
        l0, l1 = match.span(1)
        link = new_md[l0:l1]
        if link.startswith("/n/"):
            # check existed nodes
            to_nid = link[3:]
            cache_current_to_nid.add(to_nid)
    return cache_current_to_nid, const.CodeEnum.OK


async def flush_to_node_ids(
        nid: str,
        orig_to_nid: List[str],
        new_md: str
) -> Tuple[List[str], const.CodeEnum]:
    new_to_nid, code = get_linked_nodes(new_md=new_md)
    if code != const.CodeEnum.OK:
        return [], code

    # remove fromNodes for linked nodes
    orig_to_nid = set(orig_to_nid)
    for to_nid in orig_to_nid.difference(new_to_nid):
        await db_ops.remove_from_node(from_nid=nid, to_nid=to_nid)

    # add fromNodes for linked nodes
    for to_nid in new_to_nid.difference(orig_to_nid):
        await db_ops.node_add_to_set(id_=to_nid, key="fromNodeIds", value=nid)

    return list(new_to_nid), const.CodeEnum.OK


async def set_linked_nodes(
        docs: List[tps.Node],
        with_disabled: bool = False,
):
    for doc in docs:
        doc["fromNodes"] = await client.coll.nodes.find({
            "id": {"$in": doc["fromNodeIds"]},
            "disabled": with_disabled,
        }).to_list(length=None)
        doc["toNodes"] = await client.coll.nodes.find({
            "id": {"$in": doc["toNodeIds"]},
            "disabled": with_disabled,
        }).to_list(length=None)
