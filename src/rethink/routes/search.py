from fastapi import Depends, APIRouter
from typing_extensions import Annotated

from rethink.controllers import schemas
from rethink.controllers.auth import token2uid
from rethink.controllers.search import node_search
from rethink.controllers.utils import TokenDecode
from rethink.routes.utils import measure_time_spend

router = APIRouter(
    prefix="/api",
    tags=["search"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    path="/cursorQuery",
    response_model=schemas.search.CursorQueryResponse,
)
@measure_time_spend
async def cursor_query(
        req: schemas.search.CursorQueryRequest,
        token_decode: Annotated[TokenDecode, Depends(token2uid)]
) -> schemas.search.CursorQueryResponse:
    return node_search.cursor_query(
        td=token_decode,
        req=req,
    )


@router.post(
    path="/searchUserNodes",
    response_model=schemas.node.NodesInfoResponse,
)
@measure_time_spend
async def search_user_nodes(
        req: schemas.search.SearchUserNodesRequest,
        token_decode: Annotated[TokenDecode, Depends(token2uid)]
) -> schemas.node.NodesInfoResponse:
    return node_search.search_user_nodes(
        td=token_decode,
        req=req,
    )


@router.put(
    path="/cursorSearchSelect",
    response_model=schemas.base.AcknowledgeResponse,
)
@measure_time_spend
async def cursor_search_select(
        req: schemas.search.AddToRecentSearchHistRequest,
        token_decode: Annotated[TokenDecode, Depends(token2uid)]
) -> schemas.base.AcknowledgeResponse:
    return node_search.add_to_recent_search_history(
        td=token_decode,
        req=req,
    )
