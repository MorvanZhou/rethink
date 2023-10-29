from rethink import const, models
from rethink.controllers import schemas
from rethink.controllers.utils import TokenDecode


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


def move_batch_to_trash(
        td: TokenDecode,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = models.node.batch_to_trash(uid=td.uid, nids=req.nids)
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
    ns, total = models.node.get_nodes_in_trash(uid=td.uid, page=p, page_size=ps)
    code = const.Code.OK
    return schemas.node.GetFromTrashResponse(
        requestId=rid,
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        data=schemas.node.parse_nodes_info(ns, total)
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


def restore_batch_from_trash(
        td: TokenDecode,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = models.node.restore_batch_from_trash(uid=td.uid, nids=req.nids)
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


def delete_batch_node(
        td: TokenDecode,
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = models.node.batch_delete(uid=td.uid, nids=req.nids)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )
