from rethink import const, core, config
from rethink.controllers import schemas
from rethink.controllers.utils import Headers, datetime2str
from rethink.core import account
from rethink.core.user import get, reset_password
from rethink.utils import mask_email, regex


def __get_user(u: dict) -> schemas.user.UserInfoResponse.User:
    u["email"] = mask_email(u["email"])
    if config.is_local_db():
        max_space = 0
    else:
        max_space = const.USER_TYPE.id2config(u["type"]).max_store_space
    last_state = u["lastState"]
    u_settings = u["settings"]
    return schemas.user.UserInfoResponse.User(
        email=u["email"],
        nickname=u["nickname"],
        avatar=u["avatar"],
        createdAt=datetime2str(u["_id"].generation_time),
        usedSpace=u["usedSpace"],
        maxSpace=max_space,
        lastState=schemas.user.UserInfoResponse.User.LastState(
            nodeDisplayMethod=last_state["nodeDisplayMethod"],
            nodeDisplaySortKey=last_state["nodeDisplaySortKey"],
        ),
        settings=schemas.user.UserInfoResponse.User.Settings(
            language=u_settings["language"],
            theme=u_settings["theme"],
            editorMode=u_settings["editorMode"],
            editorFontSize=u_settings["editorFontSize"],
            editorCodeTheme=u_settings["editorCodeTheme"],
            editorSepRightWidth=u_settings.get("editorSepRightWidth", 200),
            editorSideCurrentToolId=u_settings.get("editorSideCurrentToolId", ""),
        ),
    )


async def get_user(
        h: Headers,
) -> schemas.user.UserInfoResponse:
    if h.code != const.Code.OK:
        return schemas.user.UserInfoResponse(
            requestId=h.request_id,
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
        )
    u, code = await core.user.get(uid=h.uid)
    if code != const.Code.OK:
        return schemas.user.UserInfoResponse(
            requestId=h.request_id,
            code=code.value,
            message=const.get_msg_by_code(code, h.language),
        )
    user_meta = __get_user(u)
    return schemas.user.UserInfoResponse(
        requestId=h.request_id,
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        user=user_meta,
    )


def __return_user_resp(u: dict, code: const.Code, req_id: str) -> schemas.user.UserInfoResponse:
    if code != const.Code.OK:
        return schemas.user.UserInfoResponse(
            requestId=req_id,
            code=code.value,
            message=const.get_msg_by_code(code, u["settings"]["language"]),
        )
    user_meta = __get_user(u)
    return schemas.user.UserInfoResponse(
        requestId=req_id,
        code=code.value,
        message=const.get_msg_by_code(code, u["settings"]["language"]),
        user=user_meta,
    )


async def patch_user(
        h: Headers,
        req: schemas.user.PatchUserRequest,
) -> schemas.user.UserInfoResponse:
    if h.code != const.Code.OK:
        return schemas.user.UserInfoResponse(
            requestId=h.request_id,
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
        )
    u, code = await core.user.patch(
        uid=h.uid,
        req=req,
    )
    return __return_user_resp(u, code, h.request_id)


async def update_password(
        h: Headers,
        req: schemas.user.UpdatePasswordRequest
) -> schemas.base.AcknowledgeResponse:
    if h.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            requestId=h.request_id,
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
        )
    if regex.VALID_PASSWORD.match(req.newPassword) is None:
        code = const.Code.INVALID_PASSWORD
        return schemas.base.AcknowledgeResponse(
            code=code.value,
            message=const.get_msg_by_code(code, h.language),
            requestId=h.request_id,
        )

    u, code = await get(uid=h.uid)
    if code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=code.value,
            message=const.get_msg_by_code(code, h.language),
            requestId=h.request_id,
        )
    ok = await account.manager.is_right_password(u, req.oldPassword)
    if not ok:
        code = const.Code.OLD_PASSWORD_ERROR
        return schemas.base.AcknowledgeResponse(
            code=code.value,
            message=const.get_msg_by_code(code, h.language),
            requestId=h.request_id,
        )

    hashed = account.manager.hash_password(password=req.newPassword, email=u["email"])
    code = await reset_password(uid=h.uid, hashed=hashed)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
    )
