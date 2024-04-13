from rethink import const, core
from rethink.controllers import schemas
from rethink.controllers.node.node_ops import _get_node_search_response_data
from rethink.controllers.utils import maybe_raise_json_exception
from rethink.models.tps import AuthedUser


async def move_to_trash(
        au: AuthedUser,
        nid: str,
) -> schemas.base.AcknowledgeResponse:
    code = await core.node.to_trash(au=au, nid=nid)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, au.language),
        requestId=au.request_id,
    )


async def move_batch_to_trash(
        au: AuthedUser,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    code = await core.node.batch_to_trash(au=au, nids=req.nids)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, au.language),
        requestId=au.request_id,
    )


async def get_from_trash(
        au: AuthedUser,
        p: int = 0,
        limit: int = 10,
) -> schemas.node.GetFromTrashResponse:
    nodes, total = await core.node.get_nodes_in_trash(au=au, page=p, limit=limit)
    code = const.Code.OK
    return schemas.node.GetFromTrashResponse(
        requestId=au.request_id,
        code=code.value,
        message=const.get_msg_by_code(code, au.language),
        data=_get_node_search_response_data(nodes=nodes, total=total),
    )


async def restore_from_trash(
        au: AuthedUser,
        nid: str,
) -> schemas.base.AcknowledgeResponse:
    code = await core.node.restore_from_trash(au=au, nid=nid)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, au.language),
        requestId=au.request_id,
    )


async def restore_batch_from_trash(
        au: AuthedUser,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    code = await core.node.restore_batch_from_trash(au=au, nids=req.nids)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, au.language),
        requestId=au.request_id,
    )


async def delete_node(
        au: AuthedUser,
        nid: str,
) -> schemas.base.AcknowledgeResponse:
    code = await core.node.delete(au=au, nid=nid)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, au.language),
        requestId="",
    )


async def delete_batch_node(
        au: AuthedUser,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    code = await core.node.batch_delete(au=au, nids=req.nids)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, au.language),
        requestId=au.request_id,
    )
