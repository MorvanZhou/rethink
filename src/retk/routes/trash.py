from typing import Optional

from fastapi import APIRouter, Query

from retk.controllers import schemas
from retk.controllers.node import trash_ops
from retk.routes import utils

router = APIRouter(
    prefix="/api/trash",
    tags=["trash"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    path="/",
    status_code=200,
    response_model=schemas.node.NodesSearchResponse,
)
@utils.measure_time_spend
async def get_from_trash(
        au: utils.ANNOTATED_AUTHED_USER,
        p: int = Query(default=0, ge=0, description="page number"),
        limit: int = Query(default=10, ge=0, le=200, description="page size"),
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.NodesSearchResponse:
    return await trash_ops.get_from_trash(
        au=au,
        p=p,
        limit=limit,
    )


# has to be before /{nid} otherwise it will be treated as a nid
@router.put(
    path="/batch",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def batch_nodes_to_trash(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.node.BatchNodeIdsRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await trash_ops.move_batch_to_trash(
        au=au,
        req=req,
    )


@router.put(
    path="/batch/restore",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def restore_batch_node_in_trash(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.node.BatchNodeIdsRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await trash_ops.restore_batch_from_trash(
        au=au,
        req=req,
    )


@router.put(
    path="/batch/delete",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def delete_batch_node(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.node.BatchNodeIdsRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await trash_ops.delete_batch_node(
        au=au,
        req=req,
    )


@router.put(
    path="/{nid}",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def move_to_trash(
        au: utils.ANNOTATED_AUTHED_USER,
        nid: str = utils.ANNOTATED_NID,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await trash_ops.move_to_trash(
        au=au,
        nid=nid,
    )


@router.put(
    path="/{nid}/restore",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def restore_node_in_trash(
        au: utils.ANNOTATED_AUTHED_USER,
        nid: str = utils.ANNOTATED_NID,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await trash_ops.restore_from_trash(
        au=au,
        nid=nid,
    )


@router.delete(
    path="/{nid}",
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def delete_node(
        au: utils.ANNOTATED_AUTHED_USER,
        nid: str = utils.ANNOTATED_NID,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await trash_ops.delete_node(
        au=au,
        nid=nid,
    )
