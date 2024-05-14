from retk import const, core, config
from retk.controllers import schemas
from retk.controllers.utils import datetime2str, maybe_raise_json_exception
from retk.core import account
from retk.core.user import reset_password
from retk.models.tps import AuthedUser
from retk.utils import mask_email, regex


async def get_user(
        au: AuthedUser,
) -> schemas.user.UserInfoResponse:
    _email = mask_email(au.u.email)
    if config.is_local_db():
        max_space = 0
    else:
        max_space = const.USER_TYPE.id2config(au.u.type).max_store_space
    return schemas.user.UserInfoResponse(
        requestId=au.request_id,
        user=schemas.user.UserInfoResponse.User(
            email=_email,
            nickname=au.u.nickname,
            avatar=au.u.avatar,
            source=au.u.source,
            createdAt=datetime2str(au.u._id.generation_time),
            usedSpace=au.u.used_space,
            maxSpace=max_space,
            lastState=schemas.user.UserInfoResponse.User.LastState(
                nodeDisplayMethod=au.u.last_state.node_display_method,
                nodeDisplaySortKey=au.u.last_state.node_display_sort_key,
            ),
            settings=schemas.user.UserInfoResponse.User.Settings(
                language=au.u.settings.language,
                theme=au.u.settings.theme,
                editorMode=au.u.settings.editor_mode,
                editorFontSize=au.u.settings.editor_font_size,
                editorCodeTheme=au.u.settings.editor_code_theme,
                editorSepRightWidth=au.u.settings.editor_sep_right_width,
                editorSideCurrentToolId=au.u.settings.editor_side_current_tool_id,
            ),
        ),
    )


async def patch_user(
        au: AuthedUser,
        req: schemas.user.PatchUserRequest,
) -> schemas.user.UserInfoResponse:
    u, code = await core.user.patch(
        au=au,
        req=req,
    )
    maybe_raise_json_exception(au=au, code=code)

    u["email"] = mask_email(u["email"])
    return schemas.user.get_user_info_response_from_u_dict(u=u, request_id=au.request_id)


async def update_password(
        au: AuthedUser,
        req: schemas.user.UpdatePasswordRequest
) -> schemas.RequestIdResponse:
    if regex.VALID_PASSWORD.match(req.newPassword) is None:
        return maybe_raise_json_exception(au=au, code=const.CodeEnum.INVALID_PASSWORD)

    ok = await account.manager.is_right_password(
        email=au.u.email,
        hashed=au.u.hashed,
        password=req.oldPassword,
    )
    if not ok:
        return maybe_raise_json_exception(au=au, code=const.CodeEnum.OLD_PASSWORD_ERROR)

    hashed = account.manager.hash_password(password=req.newPassword, email=au.u.email)
    code = await reset_password(uid=au.u.id, hashed=hashed)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def get_notifications(
        au: AuthedUser,
) -> schemas.notice.NotificationResponse:
    notifications = []
    return schemas.notice.NotificationResponse(
        requestId=au.request_id,
        notifications=notifications,
    )
