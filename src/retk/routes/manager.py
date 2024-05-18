from fastapi import APIRouter, Query

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
    response_model=schemas.manager.GetManagerDataResponse,
)
@utils.measure_time_spend
async def get_manager_data(
        au: ADMIN_AUTH,
) -> schemas.manager.GetManagerDataResponse:
    return await manager.get_manager_data(au=au)


@router.put(
    "/users",
    status_code=200,
    response_model=schemas.manager.GetUserResponse,
)
@utils.measure_time_spend
async def get_user_info(
        au: ADMIN_AUTH,
        req: schemas.manager.GetUserRequest,
) -> schemas.manager.GetUserResponse:
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


@router.post(
    "/notices/system",
    status_code=201,
    response_model=schemas.RequestIdResponse,
    summary="Post in manager delivery",
    description="Post a notice in manager delivery",
)
@utils.measure_time_spend
async def post_in_manager_delivery(
        au: utils.ANNOTATED_AUTHED_ADMIN,
        req: schemas.manager.ManagerNoticeDeliveryRequest,
) -> schemas.RequestIdResponse:
    return await manager.post_in_manager_delivery(au=au, req=req)


@router.get(
    "/notices/system",
    status_code=200,
    response_model=schemas.manager.GetSystemNoticesResponse,
    summary="Get unscheduled system notices",
    description="Get unscheduled system notices",
)
@utils.measure_time_spend
async def get_unscheduled_system_notices(
        au: ADMIN_AUTH,
        p: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
) -> schemas.manager.GetSystemNoticesResponse:
    return await manager.get_system_notices(au=au, page=p, limit=limit)
