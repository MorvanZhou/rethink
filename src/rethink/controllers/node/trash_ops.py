from rethink import const, models
from rethink.controllers import schemas
from rethink.controllers.utils import TokenDecode, datetime2str


def move_to_trash(
        td: TokenDecode,
        req: schemas.node.RestoreFromTrashRequest,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = models.node.to_trash(uid=td.uid, nid=req.nid)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )


def get_from_trash(
        td: TokenDecode,
        p: int = 0,
        ps: int = 10,
        rid: str = "",
) -> schemas.node.GetFromTrashResponse:
    ns = models.node.get_nodes_in_trash(uid=td.uid, page=p, page_size=ps)
    code = const.Code.OK
    return schemas.node.GetFromTrashResponse(
        requestId=rid,
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        nodes=[schemas.node.NodesInfoResponse.NodeInfo(
            id=n["id"],
            title=n["title"],
            snippet=n["snippet"],
            type=n["type"],
            createdAt=datetime2str(n["_id"].generation_time),
            modifiedAt=datetime2str(n["modifiedAt"]),
        ) for n in ns],
    )


def restore_from_trash(
        td: TokenDecode,
        req: schemas.node.RestoreFromTrashRequest,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = models.node.restore_from_trash(uid=td.uid, nid=req.nid)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )


def delete_node(
        td: TokenDecode,
        nid: str,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId="",
        )
    code = models.node.delete(uid=td.uid, nid=nid)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId="",
    )
