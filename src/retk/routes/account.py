from typing import Optional

from fastapi import APIRouter, Cookie, Header
from fastapi.responses import JSONResponse

from retk import const
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
)
@utils.measure_time_spend
async def signup(
        req_id: utils.ANNOTATED_REQUEST_ID,
        req: schemas.account.SignupRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> JSONResponse:
    return await account.signup(req_id=req_id, req=req)


@router.put(
    "/auto-login",
    status_code=200,
)
@utils.measure_time_spend
async def auto_login(
        token: str = Cookie(alias=const.settings.COOKIE_ACCESS_TOKEN, default=""),
        request_id: str = Header(
            default="", alias="RequestId", max_length=const.settings.MD_MAX_LENGTH
        )
) -> schemas.user.UserInfoResponse:
    return await account.auto_login(
        token=token,
        req_id=request_id,
    )


@router.put(
    "/login",
    status_code=200,
)
@utils.measure_time_spend
async def login(
        req_id: utils.ANNOTATED_REQUEST_ID,
        req: schemas.account.LoginRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> JSONResponse:
    return await account.login(req_id=req_id, req=req)


@router.put(
    path="/password",
    status_code=200,
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
)
@utils.measure_time_spend
async def refresh_token(
        au: utils.ANNOTATED_REFRESH_TOKEN,  # check refresh token expiration
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> JSONResponse:
    return await account.get_new_access_token(au=au)


@router.put(
    "/logout",
    status_code=200,
)
@utils.measure_time_spend
async def logout(
        req_id: utils.ANNOTATED_REQUEST_ID,
        au: utils.ANNOTATED_AUTHED_USER,
) -> JSONResponse:
    return await account.logout(req_id=req_id, au=au)
