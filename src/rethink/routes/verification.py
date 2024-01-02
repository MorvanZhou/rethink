from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from rethink.controllers.verify import v_captcha
from rethink.routes.utils import measure_time_spend, verify_referer

router = APIRouter(
    prefix="/api",
    tags=["verification"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    path="/captcha/img",
)
@measure_time_spend
async def get_captcha_img(
        referer: Optional[str] = Depends(verify_referer),
) -> StreamingResponse:
    return v_captcha.get_captcha_img()
