from typing import Literal, Optional

from rethink import const, core
from rethink.controllers import schemas
from rethink.models.tps import AuthedUser


async def user_nodes(
        au: AuthedUser,
        q: str,
        sort: Literal["createdAt", "modifiedAt", "title", "similarity"],
        order: Literal["asc", "desc"],
        page: int,
        limit: int,
) -> schemas.node.NodesSearchResponse:
    nodes, total = await core.node.search.user_nodes(
        au=au,
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
        message=const.get_msg_by_code(code, au.language),
        requestId=au.request_id,
        data=schemas.node.NodesSearchResponse.Data(
            nodes=nodes,
            total=total,
        )
    )


async def node_at_query(
        au: AuthedUser,
        nid: str,
        q: Optional[str],
        p: int,
        limit: int,
) -> schemas.node.NodesSearchResponse:
    nodes, total = await core.node.search.at(
        au=au,
        nid=nid,
        query=q,
        page=p,
        limit=limit,
    )
    code = const.Code.OK
    return schemas.node.NodesSearchResponse(
        code=code.value,
        message=const.get_msg_by_code(code, au.language),
        requestId=au.request_id,
        data=schemas.node.NodesSearchResponse.Data(
            nodes=nodes,
            total=total,
        )
    )


async def recommend_nodes(
        au: AuthedUser,
        nid: str,
        content: str,
) -> schemas.node.RecommendNodesResponse:
    max_return = 5
    nodes = await core.node.search.recommend(
        au=au,
        content=content,
        max_return=max_return,
        exclude_nids=[nid],
    )
    code = const.Code.OK
    return schemas.node.RecommendNodesResponse(
        code=code.value,
        message=const.get_msg_by_code(code, au.language),
        requestId=au.request_id,
        nodes=nodes
    )
