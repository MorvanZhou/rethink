from retk import core, const
from retk.controllers import schemas
from retk.controllers.node.node_ops import _get_node_search_response_data
from retk.controllers.utils import maybe_raise_json_exception
from retk.models.tps import AuthedUser


async def move_to_trash(
        au: AuthedUser,
        nid: str,
) -> schemas.RequestIdResponse:
    return await move_batch_to_trash(
        au=au,
        req=schemas.node.BatchNodeIdsRequest(
            nids=[nid],
        ),
    )


async def move_batch_to_trash(
        au: AuthedUser,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.RequestIdResponse:
    code = await core.node.batch_to_trash(au=au, nids=req.nids)
    maybe_raise_json_exception(au=au, code=code)

    await core.statistic.add_user_behavior(
        uid=au.u.id,
        type_=const.UserBehaviorTypeEnum.NODE_TRASHED_OPS,
        remark="",
    )
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def get_from_trash(
        au: AuthedUser,
        p: int = 0,
        limit: int = 10,
) -> schemas.node.NodesSearchResponse:
    nodes, total = await core.node.get_nodes_in_trash(au=au, page=p, limit=limit)
    return schemas.node.NodesSearchResponse(
        requestId=au.request_id,
        data=_get_node_search_response_data(nodes=nodes, total=total),
    )


async def restore_from_trash(
        au: AuthedUser,
        nid: str,
) -> schemas.RequestIdResponse:
    return await restore_batch_from_trash(
        au=au,
        req=schemas.node.BatchNodeIdsRequest(
            nids=[nid],
        ),
    )


async def restore_batch_from_trash(
        au: AuthedUser,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.RequestIdResponse:
    code = await core.node.restore_batch_from_trash(au=au, nids=req.nids)
    maybe_raise_json_exception(au=au, code=code)

    await core.statistic.add_user_behavior(
        uid=au.u.id,
        type_=const.UserBehaviorTypeEnum.NODE_RESTORED_OPS,
        remark="",
    )
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def delete_node(
        au: AuthedUser,
        nid: str,
) -> schemas.RequestIdResponse:
    return await delete_batch_node(
        au=au,
        req=schemas.node.BatchNodeIdsRequest(
            nids=[nid],
        ),
    )


async def delete_batch_node(
        au: AuthedUser,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.RequestIdResponse:
    code = await core.node.batch_delete(au=au, nids=req.nids)
    maybe_raise_json_exception(au=au, code=code)

    await core.statistic.add_user_behavior(
        uid=au.u.id,
        type_=const.UserBehaviorTypeEnum.NODE_DELETED_OPS,
        remark="",
    )
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )
