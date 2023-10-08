from fastapi import Depends, APIRouter
from typing_extensions import Annotated

from rethink.controllers import schemas
from rethink.controllers.auth import token2uid
from rethink.controllers.node import node_ops
from rethink.controllers.utils import TokenDecode
from rethink.routes.utils import measure_time_spend

router = APIRouter(
    prefix="/api",
    tags=["node"],
    responses={404: {"description": "Not found"}},
)


@router.put(
    path="/node",
    response_model=schemas.node.PutResponse,
)
@measure_time_spend
async def put_node(
        req: schemas.node.PutRequest,
        token_decode: Annotated[TokenDecode, Depends(token2uid)]
) -> schemas.node.PutResponse:
    return node_ops.put_node(
        td=token_decode,
        req=req,
    )


@router.get(
    path="/node",
    response_model=schemas.node.GetResponse,
)
@measure_time_spend
async def get_node(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        nid: str,
        rid: str = "",
) -> schemas.node.GetResponse:
    return node_ops.get_node(
        td=token_decode,
        req_id=rid,
        nid=nid,
    )


@router.post(
    path="/node",
    response_model=schemas.node.GetResponse,
)
@measure_time_spend
async def update_node(
        req: schemas.node.UpdateRequest,
        token_decode: Annotated[TokenDecode, Depends(token2uid)]
) -> schemas.node.GetResponse:
    return node_ops.update_node(
        td=token_decode,
        req=req,
    )
