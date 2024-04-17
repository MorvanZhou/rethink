from typing import Optional

from fastapi import APIRouter

from retk.controllers import schemas
from retk.controllers.app_system import get_latest_version
from retk.routes import utils

router = APIRouter(
    prefix="/api/system",
    tags=["system"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/latest-version",
    status_code=200,
    response_model=schemas.app_system.LatestVersionResponse,
)
@utils.measure_time_spend
async def latest_version(
        au: utils.ANNOTATED_AUTHED_USER,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.app_system.LatestVersionResponse:
    return await get_latest_version(au=au)
