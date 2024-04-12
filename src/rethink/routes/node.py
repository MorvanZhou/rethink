from typing import Optional, Literal

from fastapi import APIRouter
from fastapi.params import Path, Query
from typing_extensions import Annotated

from rethink import const
from rethink.controllers import schemas
from rethink.controllers.node import node_ops, search
from rethink.routes import utils

router = APIRouter(
    prefix="/api/nodes",
    tags=["node"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    path="/",
    status_code=201,
    response_model=schemas.node.CreateResponse,
)
@utils.measure_time_spend
async def post_node(
        h: utils.ANNOTATED_HEADERS,
        req: schemas.node.CreateRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.CreateResponse:
    return await node_ops.post_node(
        h=h,
        req=req,
    )


@router.post(
    path="/quick",
    status_code=201,
    response_model=schemas.node.CreateResponse,
)
@utils.measure_time_spend
async def post_quick_node(
        h: utils.ANNOTATED_HEADERS,
        req: schemas.node.CreateRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.CreateResponse:
    return await node_ops.post_quick_node(
        h=h,
        req=req,
    )


@router.get(
    path="/",
    status_code=200,
    response_model=schemas.node.NodesSearchResponse,
)
@utils.measure_time_spend
async def get_search_nodes(
        h: utils.ANNOTATED_HEADERS,
        q: str = Query(max_length=const.SEARCH_QUERY_MAX_LENGTH),
        sort: Optional[
            Literal["createdAt", "modifiedAt", "title", "similarity"]
        ] = Query(default="createdAt", max_length=20),
        order: Optional[Literal["asc", "desc"]] = Query(default="asc", alias="ord"),
        page: Optional[int] = Query(default=0, ge=0, alias="p"),
        limit: Optional[int] = Query(default=20, ge=0, le=const.SEARCH_LIMIT_MAX),
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.NodesSearchResponse:
    return await search.user_nodes(
        h=h,
        q=q,
        sort=sort,
        order=order,
        page=page,
        limit=limit,
    )


# make sure this is before /{nid} otherwise it will be treated as a nid
@router.get(
    path="/core",
    status_code=200,
    response_model=schemas.node.CoreNodesResponse,
)
@utils.measure_time_spend
async def get_core_nodes(
        h: utils.ANNOTATED_HEADERS,
        p: int = Query(default=0, ge=0, description="page number"),
        limit: int = Query(default=10, ge=0, le=const.SEARCH_LIMIT_MAX),
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.CoreNodesResponse:
    return await node_ops.get_core_nodes(
        h=h,
        p=p,
        limit=limit,
    )


@router.get(
    path="/{nid}",
    status_code=200,
    response_model=schemas.node.GetResponse,
)
@utils.measure_time_spend
async def get_node(
        h: utils.ANNOTATED_HEADERS,
        nid: str = utils.ANNOTATED_NID,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.GetResponse:
    return await node_ops.get_node(
        h=h,
        nid=nid,
    )


@router.get(
    path="/{nid}/at",
    status_code=200,
    response_model=schemas.node.NodesSearchResponse,
)
@utils.measure_time_spend
async def get_at_query(
        h: utils.ANNOTATED_HEADERS,
        nid: str = utils.ANNOTATED_NID,
        q: Optional[str] = Query(default="", max_length=const.SEARCH_QUERY_MAX_LENGTH),
        page: Optional[int] = Query(default=0, ge=0, description="page number"),
        limit: Optional[int] = Query(default=20, ge=0, le=const.SEARCH_LIMIT_MAX),
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.NodesSearchResponse:
    return await search.node_at_query(
        h=h,
        nid=nid,
        q=q,
        p=page,
        limit=limit,
    )


@router.get(
    path="/{nid}/recommend",
    status_code=200,
    response_model=schemas.node.RecommendNodesResponse,
)
@utils.measure_time_spend
async def get_recommend_nodes(
        h: utils.ANNOTATED_HEADERS,
        nid: str = utils.ANNOTATED_NID,
        content: str = Query(
            max_length=const.RECOMMEND_CONTENT_MAX_LENGTH,
            description="recommend based on this content"
        ),
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.RecommendNodesResponse:
    return await search.recommend_nodes(
        h=h,
        nid=nid,
        content=content,
    )


@router.get(
    path="/{nid}/history",
    status_code=200,
    response_model=schemas.node.HistEditionsResponse,
)
@utils.measure_time_spend
async def get_hist_editions(
        h: utils.ANNOTATED_HEADERS,
        nid: str = utils.ANNOTATED_NID,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.HistEditionsResponse:
    return await node_ops.get_hist_editions(
        h=h,
        nid=nid,
    )


@router.get(
    path="/{nid}/history/{version}/md",
    status_code=200,
    response_model=schemas.node.HistEditionMdResponse,
)
@utils.measure_time_spend
async def get_hist_md(
        h: utils.ANNOTATED_HEADERS,
        nid: str = utils.ANNOTATED_NID,
        version: str = Annotated[str, Path(max_length=30)],
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.HistEditionMdResponse:
    return await node_ops.get_hist_edition_md(
        h=h,
        nid=nid,
        version=version,
    )


@router.put(
    path="/{nid}/md",
    status_code=200,
    response_model=schemas.node.GetResponse,
)
@utils.measure_time_spend
async def put_node_md(
        h: utils.ANNOTATED_HEADERS,
        req: schemas.node.PatchMdRequest,
        nid: str = utils.ANNOTATED_NID,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.GetResponse:
    return await node_ops.update_md(
        h=h,
        req=req,
        nid=nid,
    )
