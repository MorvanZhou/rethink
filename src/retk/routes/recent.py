from fastapi import APIRouter

from retk.controllers import schemas, recent
from retk.routes import utils

router = APIRouter(
    prefix="/api/recent",
    tags=["search"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    path="/at",
    status_code=201,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def add_recent_at_node(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.recent.AtNodeRequest,
) -> schemas.RequestIdResponse:
    return await recent.add_recent_at_node(
        au=au,
        req=req,
    )


@router.get(
    path="/searched",
    status_code=200,
    response_model=schemas.recent.GetRecentSearchResponse,
)
@utils.measure_time_spend
async def get_recent_searched(
        au: utils.ANNOTATED_AUTHED_USER,
) -> schemas.recent.GetRecentSearchResponse:
    return await recent.get_recent_searched(
        au=au,
    )
