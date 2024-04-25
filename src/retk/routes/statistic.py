from fastapi import APIRouter

from retk.controllers import schemas, statistic
from retk.routes import utils

router = APIRouter(
    prefix="/api/statistic",
    tags=["statistic"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    path="/user-behavior",
    status_code=201,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def add_user_behavior(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.statistic.UserBehaviorRequest,
) -> schemas.RequestIdResponse:
    return await statistic.add_user_behavior(
        au=au,
        req=req,
    )
