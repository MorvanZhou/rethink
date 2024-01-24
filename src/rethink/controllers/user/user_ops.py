from rethink import const, core, config
from rethink.controllers import schemas, auth
from rethink.controllers.utils import TokenDecode, datetime2str
from rethink.core.verify.verification import verify_captcha
from rethink.utils import jwt_encode, mask_email


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
        ),
    )


async def put(req: schemas.user.RegisterRequest) -> schemas.base.TokenResponse:
    if req.language not in const.Language.__members__:
        req.language = const.Language.EN.value
    code = verify_captcha(token=req.captchaToken, code_str=req.captchaCode)
    if code != const.Code.OK:
        return schemas.base.TokenResponse(
            requestId=req.requestId,
            code=code.value,
            message=const.get_msg_by_code(code, req.language),
            token="",
        )

    new_user_id, code = await auth.register_user(
        req.email,
        req.password,
        req.language,
    )
    if code != const.Code.OK:
        return schemas.base.TokenResponse(
            requestId=req.requestId,
            code=code.value,
            message=const.get_msg_by_code(code, req.language),
            token="",
        )

    token = jwt_encode(
        exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
        data={"uid": new_user_id, "language": req.language},
    )
    return schemas.base.TokenResponse(
        requestId=req.requestId,
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, req.language),
        token=token,
    )


async def login(req: schemas.user.LoginRequest) -> schemas.base.TokenResponse:
    # TODO: 后台应记录成功登录用户名和 IP、时间.
    #  当尝试登录 IP 不在历史常登录 IP 地理位置时，应进行多因素二次验证用户身份，防止用户因密码泄漏被窃取账户
    u, code = await auth.get_user_by_email(req.email)
    if code != const.Code.OK:
        return schemas.base.TokenResponse(
            requestId=req.requestId,
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            token="",
        )
    if not await auth.verify_user(u, req.password):
        code = const.Code.ACCOUNT_OR_PASSWORD_ERROR
        return schemas.base.TokenResponse(
            requestId=req.requestId,
            code=code.value,
            message=const.get_msg_by_code(code, u["settings"]["language"]),
            token="",
        )
    token = jwt_encode(
        exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
        data={"uid": u["id"], "language": u["settings"]["language"]},
    )
    return schemas.base.TokenResponse(
        requestId=req.requestId,
        code=code.value,
        message=const.get_msg_by_code(code, u["settings"]["language"]),
        token=token,
    )


async def get_user(
        req_id: str,
        td: TokenDecode,
) -> schemas.user.UserInfoResponse:
    if td.code != const.Code.OK:
        return schemas.user.UserInfoResponse(
            requestId=req_id,
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
        )
    u, code = await core.user.get(uid=td.uid)
    if code != const.Code.OK:
        return schemas.user.UserInfoResponse(
            requestId=req_id,
            code=code.value,
            message=const.get_msg_by_code(code, td.language),
        )
    user_meta = __get_user(u)
    return schemas.user.UserInfoResponse(
        requestId=req_id,
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
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


async def update_user(
        td: TokenDecode,
        req: schemas.user.UpdateRequest,
) -> schemas.user.UserInfoResponse:
    if td.code != const.Code.OK:
        return schemas.user.UserInfoResponse(
            requestId=req.requestId,
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
        )
    u, code = await core.user.update(
        uid=td.uid,
        nickname=req.nickname,
        avatar=req.avatar,
        node_display_method=req.nodeDisplayMethod,
        node_display_sort_key=req.nodeDisplaySortKey,
    )
    return __return_user_resp(u, code, req.requestId)


async def update_settings(
        td: TokenDecode,
        req: schemas.user.UpdateSettingsRequest,
) -> schemas.user.UserInfoResponse:
    if td.code != const.Code.OK:
        return schemas.user.UserInfoResponse(
            requestId=req.requestId,
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
        )
    u, code = await core.user.update_settings(
        uid=td.uid,
        language=req.language,
        theme=req.theme,
        editor_mode=req.editorMode,
        editor_font_size=req.editorFontSize,
        editor_code_theme=req.editorCodeTheme,
    )
    return __return_user_resp(u, code, req.requestId)
