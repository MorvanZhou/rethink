from typing import Literal, Optional

from rethink import const, core
from rethink.controllers import schemas
from rethink.controllers.utils import Headers


async def user_nodes(
        h: Headers,
        q: str,
        sort: Literal["createdAt", "modifiedAt", "title", "similarity"],
        order: Literal["asc", "desc"],
        page: int,
        limit: int,
) -> schemas.node.NodesSearchResponse:
    if h.code != const.Code.OK:
        return schemas.node.NodesSearchResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            nodes=[],
        )
    nodes, total = await core.node.search.user_nodes(
        uid=h.uid,
        query=q,
        sort_key=sort,
        reverse=order == "desc",
        page=page,
        limit=limit,
        exclude_nids=[],
    )
    code = const.Code.OK
    return schemas.node.NodesSearchResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
        data=schemas.node.NodesSearchResponse.Data(
            nodes=nodes,
            total=total,
        )
    )


async def node_at_query(
        h: Headers,
        nid: str,
        q: Optional[str],
        p: int,
        limit: int,
) -> schemas.node.NodesSearchResponse:
    if h.code != const.Code.OK:
        return schemas.node.NodesSearchResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            data=None
        )
    nodes, total = await core.node.search.at(
        uid=h.uid,
        nid=nid,
        query=q,
        page=p,
        limit=limit,
    )
    code = const.Code.OK
    return schemas.node.NodesSearchResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
        data=schemas.node.NodesSearchResponse.Data(
            nodes=nodes,
            total=total,
        )
    )


async def recommend_nodes(
        h: Headers,
        nid: str,
        content: str,
) -> schemas.node.RecommendNodesResponse:
    if h.code != const.Code.OK:
        return schemas.node.RecommendNodesResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            nodes=[],
        )
    max_return = 5
    nodes = await core.node.search.recommend(
        uid=h.uid,
        content=content,
        max_return=max_return,
        exclude_nids=[nid],
    )
    code = const.Code.OK
    return schemas.node.RecommendNodesResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
        nodes=nodes
    )
