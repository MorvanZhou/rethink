from rethink import const, models
from rethink.controllers import schemas
from rethink.controllers.utils import TokenDecode, datetime2str


async def move_to_trash(
        td: TokenDecode,
        req: schemas.node.RestoreFromTrashRequest,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = await models.node.to_trash(uid=td.uid, nid=req.nid)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )


async def move_batch_to_trash(
        td: TokenDecode,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = await models.node.batch_to_trash(uid=td.uid, nids=req.nids)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )


async def get_from_trash(
        td: TokenDecode,
        p: int = 0,
        ps: int = 10,
        rid: str = "",
) -> schemas.node.GetFromTrashResponse:
    nodes, total = await models.node.get_nodes_in_trash(uid=td.uid, page=p, page_size=ps)
    code = const.Code.OK
    data = schemas.search.NodesSearchResponse.Data(
        nodes=[schemas.search.NodesSearchResponse.Data.Node(
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
        requestId=rid,
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        data=data,
    )


async def restore_from_trash(
        td: TokenDecode,
        req: schemas.node.RestoreFromTrashRequest,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = await models.node.restore_from_trash(uid=td.uid, nid=req.nid)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )


async def restore_batch_from_trash(
        td: TokenDecode,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = await models.node.restore_batch_from_trash(uid=td.uid, nids=req.nids)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )


async def delete_node(
        td: TokenDecode,
        nid: str,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId="",
        )
    code = await models.node.delete(uid=td.uid, nid=nid)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId="",
    )


async def delete_batch_node(
        td: TokenDecode,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = await models.node.batch_delete(uid=td.uid, nids=req.nids)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )
