from fastapi import APIRouter

from rethink.controllers import schemas, email
from rethink.routes.utils import measure_time_spend

router = APIRouter(
    prefix="/api",
    tags=["email"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    path="/email/forgetPassword",
    response_model=schemas.base.TokenResponse,
)
@measure_time_spend
async def forget_password_send_email(
        req: schemas.user.ForgetPasswordRequest,
) -> schemas.base.TokenResponse:
    return email.forget_password(req=req)
