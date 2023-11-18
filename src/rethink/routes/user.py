from typing import Optional

from fastapi import Depends, APIRouter, Header
from typing_extensions import Annotated

from rethink.controllers import schemas
from rethink.controllers.auth import token2uid
from rethink.controllers.user import user_ops
from rethink.controllers.utils import TokenDecode
from rethink.routes.utils import measure_time_spend

router = APIRouter(
    prefix="/api",
    tags=["user"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/login",
    response_model=schemas.user.LoginResponse,
)
@measure_time_spend
async def login(
        req: schemas.user.LoginRequest
) -> schemas.user.LoginResponse:
    return await user_ops.login(req=req)


@router.put(
    "/user",
    response_model=schemas.user.LoginResponse,
)
@measure_time_spend
async def register(
        req: schemas.user.RegisterRequest
) -> schemas.user.LoginResponse:
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
        token_decode: Annotated[TokenDecode, Depends(token2uid)]
) -> schemas.user.UserInfoResponse:
    return await user_ops.update_user(
        td=token_decode,
        req=req,
    )
