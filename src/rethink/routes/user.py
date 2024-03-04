from typing import Optional

from fastapi import Depends, APIRouter, Header
from typing_extensions import Annotated

from rethink.controllers import schemas
from rethink.controllers.auth import token2uid
from rethink.controllers.user import user_ops, password
from rethink.controllers.utils import TokenDecode
from rethink.routes.utils import measure_time_spend, verify_referer

router = APIRouter(
    prefix="/api",
    tags=["user"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/login",
    response_model=schemas.base.TokenResponse,
)
@measure_time_spend
async def login(
        req: schemas.user.LoginRequest,
        referer: Optional[str] = Depends(verify_referer),
) -> schemas.base.TokenResponse:
    return await user_ops.login(req=req)


@router.put(
    "/user",
    response_model=schemas.base.TokenResponse,
)
@measure_time_spend
async def register(
        req: schemas.user.RegisterRequest,
        referer: Optional[str] = Depends(verify_referer),
) -> schemas.base.TokenResponse:
    return await user_ops.put(req=req)


@router.get(
    path="/user",
    response_model=schemas.user.UserInfoResponse,
)
@measure_time_spend
async def get_user(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        rid: Optional[str] = Header(None),
) -> schemas.user.UserInfoResponse:
    return await user_ops.get_user(
        req_id=rid, td=token_decode
    )


@router.post(
    path="/user",
    response_model=schemas.user.UserInfoResponse,
)
@measure_time_spend
async def update_user(
        req: schemas.user.UpdateRequest,
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        referer: Optional[str] = Depends(verify_referer),
) -> schemas.user.UserInfoResponse:
    return await user_ops.update_user(
        td=token_decode,
        req=req,
    )


@router.post(
    path="/user/settings",
    response_model=schemas.user.UserInfoResponse,
)
@measure_time_spend
async def update_user_settings(
        req: schemas.user.UpdateSettingsRequest,
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        referer: Optional[str] = Depends(verify_referer),
) -> schemas.user.UserInfoResponse:
    return await user_ops.update_settings(
        td=token_decode,
        req=req,
    )


@router.post(
    path="/user/password/forget",
    response_model=schemas.base.TokenResponse,
)
@measure_time_spend
async def forget_password(
        req: schemas.user.ForgetPasswordRequest,
        referer: Optional[str] = Depends(verify_referer),
) -> schemas.base.AcknowledgeResponse:
    return await password.forget(req=req)


@router.post(
    path="/user/password/update",
    response_model=schemas.base.AcknowledgeResponse,
)
@measure_time_spend
async def update_user(
        req: schemas.user.UpdatePasswordRequest,
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        referer: Optional[str] = Depends(verify_referer),
) -> schemas.base.AcknowledgeResponse:
    return await password.update(
        td=token_decode,
        req=req,
    )
