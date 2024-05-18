from typing import List, Dict, Tuple, Sequence, Literal

from retk.controllers.schemas.node import NodesSearchResponse
from retk.core.recent import put_recent_search
from retk.models import tps
from retk.models.client import client
from retk.models.search_engine.engine import SearchResult
from retk.utils import datetime2str


async def _2node_data(
        hits: Sequence[SearchResult],
) -> List[NodesSearchResponse.Data.Node]:
    nodes = await client.coll.nodes.find({"id": {"$in": [hit.nid for hit in hits]}}).to_list(length=None)
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


async def user_nodes(
        au: tps.AuthedUser,
        query: str,
        sort_key: Literal[
            "createdAt", "modifiedAt", "title", "similarity"
        ],
        reverse: bool,
        page: int,
        limit: int,
        exclude_nids: Sequence[str],
) -> Tuple[List[NodesSearchResponse.Data.Node], int]:
    # search nodes
    hits, total = await client.search.search(
        au=au,
        query=query,
        sort_key=sort_key,
        reverse=reverse,
        page=page,
        limit=limit,
        exclude_nids=exclude_nids,
    )
    results = await _2node_data(hits)

    if query != "":
        await put_recent_search(au=au, query=query)
    return results, total


async def recommend(
        au: tps.AuthedUser,
        content: str,
        max_return: int = 5,
        exclude_nids: Sequence[str] = None,
) -> List[NodesSearchResponse.Data.Node]:
    if content == "":
        return []
    # search nodes
    hits = await client.search.recommend(
        au=au,
        content=content,
        max_return=max_return,
        exclude_nids=exclude_nids,
    )
    return await _2node_data(hits)


async def at(
        au: tps.AuthedUser,
        nid: str,
        query: str,
        page: int,
        limit: int,
) -> Tuple[List[NodesSearchResponse.Data.Node], int]:
    query = query.strip()

    # if query == "", return recent nodes
    if query == "":
        rn = au.u.last_state.recent_cursor_search_selected_nids
        try:
            rn.remove(nid)
        except ValueError:
            pass
        _nodes = sorted(
            await client.coll.nodes.find({"id": {"$in": rn}}).to_list(length=None), key=lambda x: rn.index(x["id"])
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
            ) for n in _nodes
        ], len(rn)

    return await user_nodes(
        au=au,
        query=query,
        sort_key="similarity",
        reverse=True,
        page=page,
        limit=limit,
        exclude_nids=[nid],
    )
