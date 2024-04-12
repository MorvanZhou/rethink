from fastapi import APIRouter

from rethink.controllers import schemas, recent
from rethink.routes import utils

router = APIRouter(
    prefix="/api/recent",
    tags=["search"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    path="/at",
    status_code=201,
    response_model=schemas.base.AcknowledgeResponse,
)
@utils.measure_time_spend
async def add_recent_at_node(
        h: utils.ANNOTATED_HEADERS,
        req: schemas.recent.AddToRecentSearchHistRequest,
) -> schemas.base.AcknowledgeResponse:
    return await recent.add_recent_at_node(
        h=h,
        req=req,
    )


@router.get(
    path="/searched",
    status_code=200,
    response_model=schemas.recent.GetRecentSearchResponse,
)
@utils.measure_time_spend
async def get_recent_searched(
        h: utils.ANNOTATED_HEADERS,
) -> schemas.recent.GetRecentSearchResponse:
    return await recent.get_recent_searched(
        h=h,
    )
