from fastapi import APIRouter

from retk.controllers import schemas, manager
from retk.routes import utils

router = APIRouter(
    prefix="/api/managers",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)

ADMIN_AUTH = utils.ANNOTATED_AUTHED_ADMIN


@router.get(
    "/",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def get_admin_info(
        au: ADMIN_AUTH,
) -> schemas.RequestIdResponse:
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


@router.put(
    "/users",
    status_code=200,
    response_model=schemas.user.UserInfoResponse,
)
@utils.measure_time_spend
async def get_user_info(
        au: ADMIN_AUTH,
        req: schemas.manager.GetUserRequest,
) -> schemas.user.UserInfoResponse:
    return await manager.get_user_info(au=au, req=req)


@router.put(
    "/users/disable",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def disable_account(
        au: ADMIN_AUTH,
        req: schemas.manager.GetUserRequest,
) -> schemas.RequestIdResponse:
    return await manager.disable_account(au=au, req=req)


@router.put(
    "/users/enable",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def enable_account(
        au: ADMIN_AUTH,
        req: schemas.manager.GetUserRequest,
) -> schemas.RequestIdResponse:
    return await manager.enable_account(au=au, req=req)


@router.put(
    "/users/delete",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def delete_account(
        au: ADMIN_AUTH,
        req: schemas.manager.GetUserRequest,
) -> schemas.RequestIdResponse:
    return await manager.delete_account(au=au, req=req)
