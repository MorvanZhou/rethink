from typing import List, Dict, Tuple, Sequence, Literal

from rethink import const
from rethink.controllers.schemas.search import NodesSearchResponse
from rethink.controllers.utils import datetime2str
from rethink.models import tps
from rethink.models.database import COLL, searcher
from rethink.models.search_engine.engine import SearchResult


async def _2node_data(
        hits: Sequence[SearchResult],
) -> List[NodesSearchResponse.Data.Node]:
    nodes = await COLL.nodes.find({"id": {"$in": [hit.nid for hit in hits]}}).to_list(length=None)
    nodes_map: Dict[str, tps.Node] = {n["id"]: n for n in nodes}
    results = []
    for hit in hits:
        n = nodes_map[hit.nid]
        r = NodesSearchResponse.Data.Node(
            id=n["id"],
            title=n["title"],
            snippet=n["snippet"],
            titleHighlight=hit.titleHighlight,
            bodyHighlights=hit.bodyHighlights,
            score=hit.score,
            type=n["type"],
            createdAt=datetime2str(n["_id"].generation_time),
            modifiedAt=datetime2str(n["modifiedAt"]),
        )
        results.append(r)
    return results


async def search(
        uid: str,
        query: str,
        sort_key: Literal[
            "createdAt", "modifiedAt", "title", "similarity"
        ],
        reverse: bool,
        page: int,
        page_size: int,
        exclude_nids: Sequence[str],
) -> Tuple[List[NodesSearchResponse.Data.Node], int]:
    # search nodes
    hits, total = await searcher().search(
        uid=uid,
        query=query,
        sort_key=sort_key,
        reverse=reverse,
        page=page,
        page_size=page_size,
        exclude_nids=exclude_nids,
    )
    results = await _2node_data(hits)

    if query != "":
        await put_recent_search(uid, query)
    return results, total


async def recommend(
        uid: str,
        content: str,
        max_return: int = 5,
        exclude_nids: Sequence[str] = None,
) -> List[NodesSearchResponse.Data.Node]:
    if content == "":
        return []
    # search nodes
    hits = await searcher().recommend(
        uid=uid,
        content=content,
        max_return=max_return,
        exclude_nids=exclude_nids,
    )
    return await _2node_data(hits)


async def cursor_query(
        uid: str,
        nid: str,
        query: str,
        page: int,
        page_size: int,
) -> Tuple[List[NodesSearchResponse.Data.Node], int]:
    # if cursor_text.startswith("@"):
    #     query = cursor_text[1:].strip()
    # else:
    #     found = CURSOR_AT_PTN.search(cursor_text)
    #     if found is None:
    #         return None, []
    #     query = found.group(1).strip()

    query = query.strip()

    # if query == "", return recent nodes
    if query == "":
        u = await COLL.users.find_one({"id": uid})
        if u is None:
            return [], 0
        rn = u["lastState"]["recentCursorSearchSelectedNIds"]
        try:
            rn.remove(nid)
        except ValueError:
            pass
        nodes = sorted(
            await COLL.nodes.find({"id": {"$in": rn}}).to_list(length=None), key=lambda x: rn.index(x["id"])
        )
        return [
            NodesSearchResponse.Data.Node(
                id=n["id"],
                title=n["title"],
                snippet=n["snippet"][:60] + "...",
                titleHighlight=n["title"],
                bodyHighlights=[n["snippet"][:60] + "..."],
                score=0,
                type=n["type"],
                createdAt=datetime2str(n["_id"].generation_time),
                modifiedAt=datetime2str(n["modifiedAt"]),
            ) for n in nodes
        ], len(rn)

    return await search(
        uid=uid,
        query=query,
        sort_key="similarity",
        reverse=True,
        page=page,
        page_size=page_size,
        exclude_nids=[nid],
    )


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
