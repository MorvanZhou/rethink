from fastapi import APIRouter

from retk.controllers import schemas, admin
from retk.routes import utils

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)

ADMIN_AUTH = utils.ANNOTATED_AUTHED_ADMIN


@router.put(
    "/users/disable",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def disable_account(
        au: ADMIN_AUTH,
        req: schemas.admin.UidRequest,
) -> schemas.RequestIdResponse:
    return await admin.disable_account_by_id(au=au, uid=req.uid)


@router.put(
    "/users/enable",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def enable_account(
        au: ADMIN_AUTH,
        req: schemas.admin.UidRequest,
) -> schemas.RequestIdResponse:
    return await admin.enable_account_by_id(au=au, uid=req.uid)


@router.put(
    "/users/delete",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def delete_account(
        au: ADMIN_AUTH,
        req: schemas.admin.UidRequest,
) -> schemas.RequestIdResponse:
    return await admin.delete_account_by_id(au=au, uid=req.uid)


@router.put(
    "/users/disable/email",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def disable_account_by_email(
        au: ADMIN_AUTH,
        req: schemas.RequestIdResponse,
) -> schemas.RequestIdResponse:
    return await admin.disable_account_by_email(au=au, email=req.email)


@router.put(
    "/users/enable/email",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def enable_account_by_email(
        au: ADMIN_AUTH,
        req: schemas.RequestIdResponse,
) -> schemas.RequestIdResponse:
    return await admin.enable_account_by_email(au=au, email=req.email)


@router.put(
    "/users/delete/email",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
@utils.measure_time_spend
async def delete_account_by_email(
        au: ADMIN_AUTH,
        req: schemas.RequestIdResponse,
) -> schemas.RequestIdResponse:
    return await admin.delete_account_by_email(au=au, email=req.email)
