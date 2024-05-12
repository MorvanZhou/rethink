from typing import Literal, Optional

from retk import core, const
from retk.controllers import schemas
from retk.models.tps import AuthedUser


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

    if q != "":
        await core.statistic.add_user_behavior(
            uid=au.u.id,
            type_=const.UserBehaviorTypeEnum.SEARCH_GLOBAL,
            remark=q,
        )
    return schemas.node.NodesSearchResponse(
        requestId=au.request_id,
        data=schemas.node.NodesSearchResponse.Data(
            nodes=nodes,
            total=total,
        )
    )


async def node_at_search(
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
    if q != "":
        await core.statistic.add_user_behavior(
            uid=au.u.id,
            type_=const.UserBehaviorTypeEnum.SEARCH_AT,
            remark=q,
        )
    return schemas.node.NodesSearchResponse(
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
) -> schemas.node.NodesSearchResponse:
    max_return = 5
    nodes = await core.node.search.recommend(
        au=au,
        content=content,
        max_return=max_return,
        exclude_nids=[nid],
    )
    return schemas.node.NodesSearchResponse(
        requestId=au.request_id,
        data=schemas.node.NodesSearchResponse.Data(
            nodes=nodes,
            total=len(nodes),
        )
    )
