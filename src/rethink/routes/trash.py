from fastapi import Depends, APIRouter
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
    return trash_ops.move_to_trash(
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
) -> schemas.node.GetFromTrashResponse:
    return trash_ops.get_from_trash(
        td=token_decode,
        p=p,
        ps=ps,
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
    return trash_ops.restore_from_trash(
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
    return trash_ops.delete_node(
        td=token_decode,
        nid=nid,
    )
