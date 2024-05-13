from fastapi import APIRouter

from retk.controllers import schemas, notice
from retk.core import scheduler
from retk.core.notice import deliver_unscheduled_system_notices
from retk.routes import utils

router = APIRouter(
    prefix="/api/notices",
    tags=["node"],
    responses={404: {"description": "Not found"}},
)


@router.on_event("startup")
async def startup_event():
    scheduler.run_every_at(
        func=deliver_unscheduled_system_notices,
        second=0,
    )


@router.post(
    "/manager",
    response_model=schemas.RequestIdResponse,
    summary="Post in manager delivery",
    description="Post a notice in manager delivery",
)
@utils.measure_time_spend
async def post_in_manager_delivery(
        au: utils.ANNOTATED_AUTHED_ADMIN,
        req: schemas.notice.ManagerNoticeDeliveryRequest,
) -> schemas.RequestIdResponse:
    return await notice.post_in_manager_delivery(au=au, req=req)


@router.get(
    "/users",
    response_model=schemas.notice.NotificationResponse,
    summary="Get user notice",
    description="Get user notice",
)
@utils.measure_time_spend
async def get_user_notice(
        au: utils.ANNOTATED_AUTHED_USER,
) -> schemas.notice.NotificationResponse:
    return await notice.get_user_notice(au=au)
