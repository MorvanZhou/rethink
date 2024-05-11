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
        req_id: utils.ANNOTATED_REQUEST_ID,
        req: schemas.account.SignupRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.account.TokenResponse:
    return await account.signup(req_id=req_id, req=req)


@router.put(
    "/login",
    status_code=200,
    response_model=schemas.account.TokenResponse,
)
@utils.measure_time_spend
async def login(
        req_id: utils.ANNOTATED_REQUEST_ID,
        req: schemas.account.LoginRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.account.TokenResponse:
    return await account.login(req_id=req_id, req=req)


@router.put(
    path="/password",
    status_code=200,
    response_model=schemas.account.TokenResponse,
)
@utils.measure_time_spend
async def forget_password(
        req_id: utils.ANNOTATED_REQUEST_ID,
        req: schemas.account.ForgetPasswordRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await account.forget(req_id=req_id, req=req)


@router.put(
    path="/email/send-code",
    status_code=200,
    response_model=schemas.account.TokenResponse,
)
@utils.measure_time_spend
async def email_verification(
        req_id: utils.ANNOTATED_REQUEST_ID,
        req: schemas.account.EmailVerificationRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.account.TokenResponse:
    return await account.email_send_code(req_id=req_id, req=req)


@router.get(
    "/access-token",
    status_code=200,
    response_model=schemas.account.TokenResponse,
)
@utils.measure_time_spend
async def refresh_token(
        au: utils.ANNOTATED_REFRESH_TOKEN,  # check refresh token expiration
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.account.TokenResponse:
    return await account.get_new_access_token(au=au)
