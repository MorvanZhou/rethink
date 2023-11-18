from typing import Optional

from fastapi import Depends, APIRouter, Header
from typing_extensions import Annotated

from rethink.controllers import schemas
from rethink.controllers.auth import token2uid
from rethink.controllers.node import trash_ops
from rethink.controllers.utils import TokenDecode
from rethink.routes.utils import measure_time_spend

router = APIRouter(
    prefix="/api",
    tags=["trash"],
    responses={404: {"description": "Not found"}},
)


@router.put(
    path="/trash",
    response_model=schemas.base.AcknowledgeResponse,
)
@measure_time_spend
async def move_to_trash(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        req: schemas.node.RestoreFromTrashRequest
) -> schemas.base.AcknowledgeResponse:
    return await trash_ops.move_to_trash(
        td=token_decode,
        req=req
    )


@router.get(
    path="/trash",
    response_model=schemas.node.GetFromTrashResponse,
)
@measure_time_spend
async def get_from_trash(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        p: int = 0,
        ps: int = 10,
        rid: Optional[str] = Header(None),
) -> schemas.node.GetFromTrashResponse:
    return await trash_ops.get_from_trash(
        td=token_decode,
        p=p,
        ps=ps,
        rid=rid,
    )


@router.post(
    path="/trashRestore",
    response_model=schemas.base.AcknowledgeResponse,
)
@measure_time_spend
async def restore_node_in_trash(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        req: schemas.node.RestoreFromTrashRequest,
) -> schemas.base.AcknowledgeResponse:
    return await trash_ops.restore_from_trash(
        td=token_decode,
        req=req,
    )


@router.delete(
    path="/trash/{nid}",
    response_model=schemas.base.AcknowledgeResponse,
)
@measure_time_spend
async def delete_node(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        nid: str,
) -> schemas.base.AcknowledgeResponse:
    return await trash_ops.delete_node(
        td=token_decode,
        nid=nid,
    )


@router.put(
    path="/trash/batch",
    response_model=schemas.base.AcknowledgeResponse,
)
@measure_time_spend
async def batch_nodes_to_trash(
        req: schemas.node.BatchNodeIdsRequest,
        token_decode: Annotated[TokenDecode, Depends(token2uid)]
) -> schemas.base.AcknowledgeResponse:
    return await trash_ops.move_batch_to_trash(
        td=token_decode,
        req=req,
    )


@router.post(
    path="/trashRestore/batch",
    response_model=schemas.base.AcknowledgeResponse,
)
@measure_time_spend
async def restore_batch_node_in_trash(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    return await trash_ops.restore_batch_from_trash(
        td=token_decode,
        req=req,
    )


@router.post(
    path="/trashDelete/batch",
    response_model=schemas.base.AcknowledgeResponse,
)
@measure_time_spend
async def delete_batch_node(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        req: schemas.node.BatchNodeIdsRequest,
) -> schemas.base.AcknowledgeResponse:
    return await trash_ops.delete_batch_node(
        td=token_decode,
        req=req,
    )
