from retk import const
from retk.models.client import client
from retk.models.tps import AuthedUser


async def added_at_node(
        au: AuthedUser,
        nid: str,
        to_nid: str,
) -> const.CodeEnum:
    # add selected node to recentCursorSearchSelectedNIds
    node_c = {"uid": au.u.id, "id": {"$in": [nid, to_nid]}}

    # try finding node
    ns = await client.coll.nodes.find(node_c).to_list(length=None)
    if len(ns) != 2:
        return const.CodeEnum.NODE_NOT_EXIST

    rns = au.u.last_state.recent_cursor_search_selected_nids
    if to_nid in rns:
        rns.remove(to_nid)
    rns.insert(0, to_nid)
    if len(rns) > 10:
        rns = rns[:10]

    # add to recentCursorSearchSelectedNIds
    res = await client.coll.users.update_one(
        {"id": au.u.id},
        {"$set": {"lastState.recentCursorSearchSelectedNIds": rns}}
    )
    if res.matched_count != 1:
        return const.CodeEnum.OPERATION_FAILED

    return const.CodeEnum.OK


async def put_recent_search(au: AuthedUser, query: str) -> const.CodeEnum:
    rns = au.u.last_state.recent_search
    try:
        rns.remove(query)
    except ValueError:
        pass
    rns.insert(0, query)
    if len(rns) > 20:
        rns = rns[:20]
    _ = await client.coll.users.update_one(
        {"id": au.u.id},
        {"$set": {"lastState.recentSearch": rns}}
    )
    return const.CodeEnum.OK
