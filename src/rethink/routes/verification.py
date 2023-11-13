
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from rethink.controllers import schemas
from rethink.controllers.verification import v_captcha
from rethink.routes.utils import measure_time_spend

router = APIRouter(
    prefix="/api",
    tags=["verification"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    path="/captcha/img",
)
@measure_time_spend
async def get_captcha_img() -> StreamingResponse:
    return v_captcha.get_captcha_img()


@router.post(
    path="/captcha/img",
    response_model=schemas.verification.VerifyCaptchaResponse,
)
@measure_time_spend
async def verify_captcha(
        req: schemas.verification.VerifyCaptchaRequest,
) -> schemas.verification.VerifyCaptchaResponse:
    return v_captcha.verify_captcha_resp(req=req)
