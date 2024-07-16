from typing import List, Tuple, Optional

from bson import ObjectId

from retk import core
from retk.config import is_local_db
from retk.const import CodeEnum
from retk.models.client import client
from retk.models.tps import AuthedUser
from retk.models.tps.llm import ExtendedNode
from retk.models.tps.node import Node
from retk.utils import get_at_node_md_link


async def get_extended_nodes(
        uid: str,
) -> List[ExtendedNode]:
    docs = await client.coll.llm_extended_node.find({"uid": uid}).to_list(None)
    return docs


async def accept_extended_node(
        au: AuthedUser,
        eid: str,
) -> Tuple[Optional[Node], CodeEnum]:
    if not is_local_db():
        doc = await client.coll.llm_extended_node.find_one_and_delete(
            {"_id": ObjectId(eid), "uid": au.u.id},
        )
    else:
        doc = await client.coll.llm_extended_node.find_one(
            {"_id": ObjectId(eid), "uid": au.u.id},
        )
        if doc is not None:
            await client.coll.llm_extended_node.delete_one(
                {"_id": ObjectId(eid), "uid": au.u.id},
            )
    if doc is None:
        return None, CodeEnum.NODE_NOT_EXIST
    title = doc["sourceMd"].split("\n", 1)[0].strip()
    at_node = get_at_node_md_link(title, doc["sourceNid"])
    md = doc["extendMd"] + "\n\n" + at_node
    n, code = await core.node.post(
        au=au,
        md=md,
        from_nid=doc["sourceNid"],
    )
    return n, code


async def reject_extended_node(
        au: AuthedUser,
        eid: str,
):
    await client.coll.llm_extended_node.delete_one(
        {"_id": ObjectId(eid), "uid": au.u.id},
    )
