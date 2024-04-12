from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from rethink.controllers import account
from rethink.routes import utils

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
async def get_captcha_img(
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> StreamingResponse:
    return account.get_captcha_img()
