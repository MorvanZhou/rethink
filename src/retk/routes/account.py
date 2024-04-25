from typing import Optional

from fastapi import APIRouter

from retk.controllers import schemas, account
from retk.routes import utils

router = APIRouter(
    prefix="/api/account",
    tags=["user"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/",
    status_code=201,
    response_model=schemas.account.TokenResponse,
)
@utils.measure_time_spend
async def signup(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.account.SignupRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.account.TokenResponse:
    return await account.signup(au=au, req=req)


@router.put(
    "/login",
    status_code=200,
    response_model=schemas.account.TokenResponse,
)
@utils.measure_time_spend
async def login(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.account.LoginRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.account.TokenResponse:
    return await account.login(au=au, req=req)


@router.put(
    path="/password",
    status_code=200,
    response_model=schemas.account.TokenResponse,
)
@utils.measure_time_spend
async def forget_password(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.account.ForgetPasswordRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await account.forget(au=au, req=req)


@router.put(
    path="/email/send-code",
    status_code=200,
    response_model=schemas.account.TokenResponse,
)
@utils.measure_time_spend
async def email_verification(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.account.EmailVerificationRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.account.TokenResponse:
    return await account.email_send_code(au=au, req=req)


@router.get(
    "/access-token",
    status_code=200,
    response_model=schemas.account.TokenResponse,
)
@utils.measure_time_spend
async def refresh_token(
        au: utils.ANNOTATED_AUTHED_USER,  # check refresh token expiration
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.account.TokenResponse:
    return await account.get_new_access_token(au=au)
