from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from retk.controllers import account
from retk.core.utils.ratelimiter import req_limit
from retk.routes import utils

router = APIRouter(
    prefix="/api/captcha",
    tags=["captcha"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    path="/img",
    status_code=200,
)
@utils.measure_time_spend
@req_limit(requests=6, in_seconds=30)
async def get_captcha_img(
        referer: Optional[str] = utils.DEPENDS_REFERER,
        ip: Optional[str] = utils.DEPENDS_IP,
) -> StreamingResponse:
    return account.get_captcha_img()
