from typing import Optional

from fastapi import APIRouter
from fastapi.params import Query

from retk.controllers import schemas, user
from retk.routes import utils

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
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def update_user_password(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.user.UpdatePasswordRequest,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await user.update_password(
        au=au,
        req=req,
    )


@router.get(
    path="/notices",
    status_code=200,
    response_model=schemas.user.NotificationResponse,
)
@utils.measure_time_spend
async def get_notifications(
        au: utils.ANNOTATED_AUTHED_USER,
        unread: Optional[bool] = Query(default=False),
        p: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.user.NotificationResponse:
    return await user.get_user_notices(
        au=au,
        unread_only=unread,
        page=p,
        limit=limit,
    )


@router.put(
    path="/notices/system/read/{notice_id}",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def mark_read_notice(
        au: utils.ANNOTATED_AUTHED_USER,
        notice_id: str,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await user.mark_system_notice_read(
        au=au,
        notice_id=notice_id,
    )


@router.put(
    path="/notices/system/read-all",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def mark_read_all_notices(
        au: utils.ANNOTATED_AUTHED_USER,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await user.mark_all_system_notice_read(
        au=au,
    )
