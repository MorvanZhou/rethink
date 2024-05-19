from fastapi import APIRouter
from fastapi.params import Path

from retk.controllers import schemas, notice
from retk.routes import utils

router = APIRouter(
    prefix="/api/notices",
    tags=["notices"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    path="/system/{notice_id}",
    status_code=200,
    response_model=schemas.notice.SystemNoticeResponse,
)
@utils.measure_time_spend
async def get_system_notice(
        au: utils.ANNOTATED_AUTHED_USER,
        notice_id: str = Path(max_length=24, title="The ID of the notice"),
) -> schemas.notice.SystemNoticeResponse:
    return await notice.get_system_notice(
        au=au,
        notice_id=notice_id,
    )
