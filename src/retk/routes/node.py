from typing import Optional, Literal

from fastapi import APIRouter
from fastapi.params import Path, Query
from typing_extensions import Annotated

from retk import const
from retk.controllers import schemas
from retk.controllers.node import node_ops, search
from retk.routes import utils

router = APIRouter(
    prefix="/api/nodes",
    tags=["node"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    path="/",
    status_code=201,
    response_model=schemas.node.NodeResponse,
)
@utils.measure_time_spend
async def post_node(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.node.CreateRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.NodeResponse:
    return await node_ops.post_node(
        au=au,
        req=req,
    )


@router.post(
    path="/quick",
    status_code=201,
    response_model=schemas.node.NodeResponse,
)
@utils.measure_time_spend
async def post_quick_node(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.node.CreateRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.NodeResponse:
    return await node_ops.post_quick_node(
        au=au,
        req=req,
    )


@router.get(
    path="/",
    status_code=200,
    response_model=schemas.node.NodesSearchResponse,
)
@utils.measure_time_spend
async def get_search_nodes(
        au: utils.ANNOTATED_AUTHED_USER,
        q: str = Query(max_length=const.settings.SEARCH_QUERY_MAX_LENGTH),
        sort: Optional[
            Literal["createdAt", "modifiedAt", "title", "similarity"]
        ] = Query(default="createdAt", max_length=20),
        order: Optional[Literal["asc", "desc"]] = Query(default="asc", alias="ord"),
        page: Optional[int] = Query(default=0, ge=0, alias="p"),
        limit: Optional[int] = Query(default=20, ge=0, le=const.settings.SEARCH_LIMIT_MAX),
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.NodesSearchResponse:
    return await search.user_nodes(
        au=au,
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
    response_model=schemas.node.NodesSearchResponse,
)
@utils.measure_time_spend
async def get_core_nodes(
        au: utils.ANNOTATED_AUTHED_USER,
        p: int = Query(default=0, ge=0, description="page number"),
        limit: int = Query(default=10, ge=0, le=const.settings.SEARCH_LIMIT_MAX),
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.NodesSearchResponse:
    return await node_ops.get_core_nodes(
        au=au,
        p=p,
        limit=limit,
    )


@router.get(
    path="/{nid}",
    status_code=200,
    response_model=schemas.node.NodeResponse,
)
@utils.measure_time_spend
async def get_node(
        au: utils.ANNOTATED_AUTHED_USER,
        nid: str = utils.ANNOTATED_NID,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.NodeResponse:
    return await node_ops.get_node(
        au=au,
        nid=nid,
    )


@router.get(
    path="/{nid}/at",
    status_code=200,
    response_model=schemas.node.NodesSearchResponse,
)
@utils.measure_time_spend
async def get_at_search(
        au: utils.ANNOTATED_AUTHED_USER,
        nid: str = utils.ANNOTATED_NID,
        q: Optional[str] = Query(default="", max_length=const.settings.SEARCH_QUERY_MAX_LENGTH),
        page: Optional[int] = Query(default=0, ge=0, description="page number"),
        limit: Optional[int] = Query(default=20, ge=0, le=const.settings.SEARCH_LIMIT_MAX),
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.NodesSearchResponse:
    return await search.node_at_search(
        au=au,
        nid=nid,
        q=q,
        p=page,
        limit=limit,
    )


@router.get(
    path="/{nid}/recommend",
    status_code=200,
    response_model=schemas.node.NodesSearchResponse,
)
@utils.measure_time_spend
async def get_recommend_nodes(
        au: utils.ANNOTATED_AUTHED_USER,
        nid: str = utils.ANNOTATED_NID,
        content: str = Query(
            max_length=const.settings.SEARCH_QUERY_MAX_LENGTH,
            description="recommend based on this content"
        ),
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.NodesSearchResponse:
    return await search.recommend_nodes(
        au=au,
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
        au: utils.ANNOTATED_AUTHED_USER,
        nid: str = utils.ANNOTATED_NID,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.HistEditionsResponse:
    return await node_ops.get_hist_editions(
        au=au,
        nid=nid,
    )


@router.get(
    path="/{nid}/history/{version}/md",
    status_code=200,
    response_model=schemas.node.HistEditionMdResponse,
)
@utils.measure_time_spend
async def get_hist_md(
        au: utils.ANNOTATED_AUTHED_USER,
        nid: str = utils.ANNOTATED_NID,
        version: str = Annotated[str, Path(max_length=30)],
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.HistEditionMdResponse:
    return await node_ops.get_hist_edition_md(
        au=au,
        nid=nid,
        version=version,
    )


@router.put(
    path="/{nid}/md",
    status_code=200,
    response_model=schemas.node.NodeResponse,
)
@utils.measure_time_spend
async def put_node_md(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.node.PatchMdRequest,
        nid: str = utils.ANNOTATED_NID,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.NodeResponse:
    return await node_ops.update_md(
        au=au,
        req=req,
        nid=nid,
    )
