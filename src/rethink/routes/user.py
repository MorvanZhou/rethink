from typing import Optional

from fastapi import APIRouter

from rethink.controllers import schemas, user
from rethink.routes import utils

router = APIRouter(
    prefix="/api/users",
    tags=["user"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    path="/",
    status_code=200,
    response_model=schemas.user.UserInfoResponse,
)
@utils.measure_time_spend
async def get_user(
        au: utils.ANNOTATED_AUTHED_USER,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.user.UserInfoResponse:
    return await user.get_user(
        au=au,
    )


@router.patch(
    path="/",
    status_code=200,
    response_model=schemas.user.UserInfoResponse,
)
@utils.measure_time_spend
async def update_user(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.user.PatchUserRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.user.UserInfoResponse:
    return await user.patch_user(
        au=au,
        req=req,
    )


@router.put(
    path="/password",
    status_code=200,
    response_model=schemas.base.AcknowledgeResponse,
)
@utils.measure_time_spend
async def update_user_password(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.user.UpdatePasswordRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.base.AcknowledgeResponse:
    return await user.update_password(
        au=au,
        req=req,
    )
