from rethink import const, core
from rethink.controllers import schemas
from rethink.controllers.utils import Headers, datetime2str


async def move_to_trash(
        h: Headers,
        nid: str,
) -> schemas.base.AcknowledgeResponse:
    if h.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
        )
    code = await core.node.to_trash(uid=h.uid, nid=nid)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
    )


async def move_batch_to_trash(
        h: Headers,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    if h.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
        )
    code = await core.node.batch_to_trash(uid=h.uid, nids=req.nids)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
    )


async def get_from_trash(
        h: Headers,
        p: int = 0,
        limit: int = 10,
) -> schemas.node.GetFromTrashResponse:
    nodes, total = await core.node.get_nodes_in_trash(uid=h.uid, page=p, limit=limit)
    code = const.Code.OK
    data = schemas.node.NodesSearchResponse.Data(
        nodes=[schemas.node.NodesSearchResponse.Data.Node(
            id=n["id"],
            title=n["title"],
            snippet=n["snippet"],
            titleHighlight="",
            bodyHighlights=[],
            score=0,
            type=n["type"],
            createdAt=datetime2str(n["_id"].generation_time),
            modifiedAt=datetime2str(n["modifiedAt"]),
        ) for n in nodes],
        total=total,
    )
    return schemas.node.GetFromTrashResponse(
        requestId=h.request_id,
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        data=data,
    )


async def restore_from_trash(
        h: Headers,
        nid: str,
) -> schemas.base.AcknowledgeResponse:
    if h.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
        )
    code = await core.node.restore_from_trash(uid=h.uid, nid=nid)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
    )


async def restore_batch_from_trash(
        h: Headers,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    if h.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
        )
    code = await core.node.restore_batch_from_trash(uid=h.uid, nids=req.nids)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
    )


async def delete_node(
        h: Headers,
        nid: str,
) -> schemas.base.AcknowledgeResponse:
    if h.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId="",
        )
    code = await core.node.delete(uid=h.uid, nid=nid)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId="",
    )


async def delete_batch_node(
        h: Headers,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    if h.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
        )
    code = await core.node.batch_delete(uid=h.uid, nids=req.nids)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
    )
