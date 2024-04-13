from typing import Optional

from fastapi import APIRouter

from rethink.controllers import schemas, account
from rethink.routes import utils

router = APIRouter(
    prefix="/api/account",
    tags=["user"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/",
    status_code=201,
    response_model=schemas.base.TokenResponse,
)
@utils.measure_time_spend
async def register(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.account.SignupRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.base.TokenResponse:
    return await account.signup(au=au, req=req)


@router.put(
    "/login",
    status_code=200,
    response_model=schemas.base.TokenResponse,
)
@utils.measure_time_spend
async def login(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.account.LoginRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.base.TokenResponse:
    return await account.login(au=au, req=req)


@router.put(
    path="/password",
    status_code=200,
    response_model=schemas.base.TokenResponse,
)
@utils.measure_time_spend
async def forget_password(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.account.ForgetPasswordRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.base.AcknowledgeResponse:
    return await account.forget(au=au, req=req)


@router.put(
    path="/email/send-code",
    status_code=200,
    response_model=schemas.base.TokenResponse,
)
@utils.measure_time_spend
async def email_verification(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.account.EmailVerificationRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.base.TokenResponse:
    return account.email_send_code(au=au, req=req)
