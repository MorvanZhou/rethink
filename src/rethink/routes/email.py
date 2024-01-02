from typing import Optional

from fastapi import APIRouter, Depends

from rethink.controllers import schemas, email
from rethink.routes.utils import measure_time_spend, verify_referer

router = APIRouter(
    prefix="/api",
    tags=["email"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    path="/email/verify",
    response_model=schemas.base.TokenResponse,
)
@measure_time_spend
async def email_verification(
        req: schemas.user.EmailVerificationRequest,
        referer: Optional[str] = Depends(verify_referer),
) -> schemas.base.TokenResponse:
    return email.send_email_verification(req=req)


@router.post(
    path="/email/register",
    response_model=schemas.base.TokenResponse,
)
@measure_time_spend
async def email_register(
        req: schemas.user.EmailVerificationRequest,
        referer: Optional[str] = Depends(verify_referer),
) -> schemas.base.TokenResponse:
    return await email.check_email_then_send_email_verification(req=req)
