from retk import const
from retk.controllers import schemas
from retk.controllers.utils import maybe_raise_json_exception, json_exception
from retk.core import account, user, notice
from retk.models.tps import AuthedUser
from retk.utils import datetime2str


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
) -> schemas.manager.GetUserResponse:
    if __check_use_uid(au=au, req=req):
        u, code = await user.get(uid=req.uid, disabled=None, exclude_manager=True)
    else:
        u, code = await user.get_by_email(email=req.email, disabled=None, exclude_manager=True)
    maybe_raise_json_exception(au=au, code=code)
    return schemas.manager.GetUserResponse(
        requestId=au.request_id,
        user=schemas.manager.GetUserResponse.User(
            id=u["id"],
            source=u["source"],
            account=u["account"],
            nickname=u["nickname"],
            email=u["email"],
            avatar=u["avatar"],
            disabled=u["disabled"],
            createdAt=datetime2str(u["_id"].generation_time),
            modifiedAt=datetime2str(u["modifiedAt"]),
            usedSpace=u["usedSpace"],
            type=u["type"],
            lastState=schemas.manager.GetUserResponse.User.LastState(
                nodeDisplayMethod=u["lastState"]["nodeDisplayMethod"],
                nodeDisplaySortKey=u["lastState"]["nodeDisplaySortKey"],
                recentSearch=u["lastState"]["recentSearch"],
                recentCursorSearchSelectedNIds=u["lastState"]["recentCursorSearchSelectedNIds"],
            ),
            settings=schemas.manager.GetUserResponse.User.Settings(
                language=u["settings"]["language"],
                theme=u["settings"]["theme"],
                editorMode=u["settings"]["editorMode"],
                editorFontSize=u["settings"]["editorFontSize"],
                editorCodeTheme=u["settings"]["editorCodeTheme"],
                editorSepRightWidth=u["settings"]["editorSepRightWidth"],
                editorSideCurrentToolId=u["settings"]["editorSideCurrentToolId"],
            ),
        ),
    )


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


async def get_system_notices(
        au: AuthedUser,
        page: int,
        limit: int,
) -> schemas.manager.GetSystemNoticesResponse:
    notices, total = await notice.get_system_notices(
        page=page,
        limit=limit,
    )
    for n in notices:
        n["id"] = str(n["_id"])
        del n["_id"]
    return schemas.manager.GetSystemNoticesResponse(
        requestId=au.request_id,
        notices=notices,
        total=total,
    )
