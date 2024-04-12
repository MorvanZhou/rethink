from typing import Optional

from fastapi import APIRouter

from rethink.controllers import schemas
from rethink.controllers.app_system import get_latest_version
from rethink.routes import utils

router = APIRouter(
    prefix="/api",
    tags=["system"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/system/latest-version",
    status_code=200,
    response_model=schemas.app_system.LatestVersionResponse,
)
@utils.measure_time_spend
async def latest_version(
        h: utils.ANNOTATED_HEADERS,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.app_system.LatestVersionResponse:
    return await get_latest_version(h=h)
