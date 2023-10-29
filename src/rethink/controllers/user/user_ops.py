from rethink import const, models, config
from rethink.controllers import schemas, auth
from rethink.controllers.utils import TokenDecode, datetime2str
from rethink.models.utils import jwt_encode


def put(req: schemas.user.RegisterRequest) -> schemas.user.LoginResponse:
    new_user_id, code = auth.register_user(
        req.email,
        req.password,
        req.language,
    )
    if code != const.Code.OK:
        return schemas.user.LoginResponse(
            requestId=req.requestId,
            code=code.value,
            message=const.get_msg_by_code(code, req.language),
            token="",
        )

    token = jwt_encode(
        exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
        data={"uid": new_user_id, "language": req.language},
    )
    return schemas.user.LoginResponse(
        requestId=req.requestId,
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, req.language),
        token=token,
    )


def login(req: schemas.user.LoginRequest) -> schemas.user.LoginResponse:
    u, code = auth.get_user_by_email(req.email)
    if code != const.Code.OK:
        return schemas.user.LoginResponse(
            requestId=req.requestId,
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            token="",
        )
    if not auth.verify_user(u, req.password):
        code = const.Code.ACCOUNT_OR_PASSWORD_ERROR
        return schemas.user.LoginResponse(
            requestId=req.requestId,
            code=code.value,
            message=const.get_msg_by_code(code, u["language"]),
            token="",
        )
    token = jwt_encode(
        exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
        data={"uid": u["id"], "language": u["language"]},
    )
    return schemas.user.LoginResponse(
        requestId=req.requestId,
        code=code.value,
        message=const.get_msg_by_code(code, u["language"]),
        token=token,
    )


def get_user(
        req_id: str,
        td: TokenDecode,
) -> schemas.user.UserInfoResponse:
    if td.code != const.Code.OK:
        return schemas.user.UserInfoResponse(
            requestId=req_id,
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
        )
    u, code = models.user.get(uid=td.uid)
    if code != const.Code.OK:
        return schemas.user.UserInfoResponse(
            requestId=req_id,
            code=code.value,
            message=const.get_msg_by_code(code, td.language),
        )

    return schemas.user.UserInfoResponse(
        requestId=req_id,
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        user=schemas.user.UserInfoResponse.User(
            email=u["email"],
            nickname=u["nickname"],
            avatar=u["avatar"],
            createdAt=datetime2str(u["_id"].generation_time),
            language=u["language"],
            nodeDisplayMethod=u["nodeDisplayMethod"],
        )
    )


def update_user(
        td: TokenDecode,
        req: schemas.user.UpdateRequest,
) -> schemas.user.UserInfoResponse:
    if td.code != const.Code.OK:
        return schemas.user.UserInfoResponse(
            requestId=req.requestId,
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
        )
    u, code = models.user.update(
        uid=td.uid,
        email=req.email,
        nickname=req.nickname,
        avatar=req.avatar,
        language=req.language,
        node_display_method=req.nodeDisplayMethod,
    )
    return schemas.user.UserInfoResponse(
        requestId=req.requestId,
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        user=schemas.user.UserInfoResponse.User(
            email=u["email"],
            nickname=u["nickname"],
            avatar=u["avatar"],
            createdAt=datetime2str(u["_id"].generation_time),
            language=u["language"],
            nodeDisplayMethod=u["nodeDisplayMethod"],
        ),
    )
