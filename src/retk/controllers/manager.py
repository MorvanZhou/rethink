from retk import const
from retk.controllers import schemas
from retk.controllers.utils import maybe_raise_json_exception, json_exception
from retk.core import account, user, notice
from retk.models.tps import AuthedUser


def __check_use_uid(au: AuthedUser, req: schemas.manager.GetUserRequest) -> bool:
    if req.uid is None and req.email is None:
        raise json_exception(
            request_id=au.request_id,
            code=const.CodeEnum.INVALID_PARAMS,
            log_msg="uid and email can't be both not None",
        )
    return req.uid is not None


async def get_user_info(
        au: AuthedUser,
        req: schemas.manager.GetUserRequest,
) -> schemas.user.UserInfoResponse:
    if __check_use_uid(au=au, req=req):
        u, code = await user.get(uid=req.uid, disabled=None, exclude_manager=True)
    else:
        u, code = await user.get_by_email(email=req.email, disabled=None, exclude_manager=True)
    maybe_raise_json_exception(au=au, code=code)
    return schemas.user.get_user_info_response_from_u_dict(u=u, request_id=au.request_id)


async def disable_account(
        au: AuthedUser,
        req: schemas.manager.GetUserRequest,
) -> schemas.RequestIdResponse:
    if __check_use_uid(au=au, req=req):
        code = await account.manager.disable_by_uid(uid=req.uid)
    else:
        code = await account.manager.disable_by_email(email=req.email)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def enable_account(
        au: AuthedUser,
        req: schemas.manager.GetUserRequest,
) -> schemas.RequestIdResponse:
    if __check_use_uid(au=au, req=req):
        code = await account.manager.enable_by_uid(uid=req.uid)
    else:
        code = await account.manager.enable_by_email(email=req.email)
    maybe_raise_json_exception(au=au, code=code)
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def delete_account(
        au: AuthedUser,
        req: schemas.manager.GetUserRequest,
) -> schemas.RequestIdResponse:
    if __check_use_uid(au=au, req=req):
        await account.manager.delete_by_uid(uid=req.uid)
    else:
        await account.manager.delete_by_email(email=req.email)
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def post_in_manager_delivery(
        au: AuthedUser,
        req: schemas.manager.ManagerNoticeDeliveryRequest,
) -> schemas.RequestIdResponse:
    _, code = await notice.post_in_manager_delivery(
        au=au,
        title=req.title,
        content=req.content,
        recipient_type=req.recipientType,
        batch_type_ids=req.batchTypeIds,
        publish_at=req.publishAt,
    )
    maybe_raise_json_exception(au=au, code=code)

    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )
