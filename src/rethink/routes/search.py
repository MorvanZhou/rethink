from typing import Optional

from fastapi import Depends, APIRouter, Header
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
    path="/search/cursor",
    response_model=schemas.search.NodesSearchResponse,
)
@measure_time_spend
async def cursor_query(
        req: schemas.search.CursorQueryRequest,
        token_decode: Annotated[TokenDecode, Depends(token2uid)]
) -> schemas.search.NodesSearchResponse:
    return await node_search.cursor_query(
        td=token_decode,
        req=req,
    )


@router.post(
    path="/search/node",
    response_model=schemas.search.NodesSearchResponse,
)
@measure_time_spend
async def search_user_nodes(
        req: schemas.search.SearchUserNodesRequest,
        token_decode: Annotated[TokenDecode, Depends(token2uid)]
) -> schemas.search.NodesSearchResponse:
    return await node_search.search_user_nodes(
        td=token_decode,
        req=req,
    )


@router.post(
    path="/search/recommend",
    response_model=schemas.search.RecommendNodesResponse,
)
@measure_time_spend
async def recommend_nodes(
        req: schemas.search.RecommendNodesRequest,
        token_decode: Annotated[TokenDecode, Depends(token2uid)]
) -> schemas.search.RecommendNodesResponse:
    return await node_search.recommend_nodes(
        td=token_decode,
        req=req,
    )


@router.put(
    path="/search/cursorSelect",
    response_model=schemas.base.AcknowledgeResponse,
)
@measure_time_spend
async def add_to_recent_cursor_search(
        req: schemas.search.AddToRecentSearchHistRequest,
        token_decode: Annotated[TokenDecode, Depends(token2uid)]
) -> schemas.base.AcknowledgeResponse:
    return await node_search.add_to_recent_cursor_search(
        td=token_decode,
        req=req,
    )


@router.get(
    path="/search/recent",
    response_model=schemas.search.GetRecentSearchResponse,
)
@measure_time_spend
async def get_recent_search(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        rid: Optional[str] = Header(None),
) -> schemas.search.GetRecentSearchResponse:
    return await node_search.get_recent(
        td=token_decode,
        rid=rid,
    )
