from random import randint
from typing import Tuple

from fastapi.responses import StreamingResponse

from rethink import config
from rethink import const
from rethink.controllers import schemas
from rethink.controllers.utils import Headers
from rethink.core import account
from rethink.utils import jwt_encode


async def signup(h: Headers, req: schemas.account.SignupRequest) -> schemas.base.TokenResponse:
    if not const.Language.is_valid(req.language):
        req.language = const.Language.EN.value
    code = account.app_captcha.verify_captcha(token=req.captchaToken, code_str=req.captchaCode)
    if code != const.Code.OK:
        return schemas.base.TokenResponse(
            requestId=h.request_id,
            code=code.value,
            message=const.get_msg_by_code(code, req.language),
            token="",
        )

    new_user_id, code = await account.manager.signup(
        req.email,
        req.password,
        req.language,
    )
    if code != const.Code.OK:
        return schemas.base.TokenResponse(
            requestId=h.request_id,
            code=code.value,
            message=const.get_msg_by_code(code, req.language),
            token="",
        )

    token = jwt_encode(
        exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
        data={"uid": new_user_id, "language": req.language},
    )
    return schemas.base.TokenResponse(
        requestId=h.request_id,
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, req.language),
        token=token,
    )


async def login(h: Headers, req: schemas.account.LoginRequest) -> schemas.base.TokenResponse:
    # TODO: 后台应记录成功登录用户名和 IP、时间.
    #  当尝试登录 IP 不在历史常登录 IP 地理位置时，应进行多因素二次验证用户身份，防止用户因密码泄漏被窃取账户
    u, code = await account.manager.get_user_by_email(req.email)
    if code != const.Code.OK:
        return schemas.base.TokenResponse(
            requestId=h.request_id,
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            token="",
        )
    if not await account.manager.is_right_password(u, req.password):
        code = const.Code.ACCOUNT_OR_PASSWORD_ERROR
        return schemas.base.TokenResponse(
            requestId=h.request_id,
            code=code.value,
            message=const.get_msg_by_code(code, u["settings"]["language"]),
            token="",
        )
    token = jwt_encode(
        exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
        data={"uid": u["id"], "language": u["settings"]["language"]},
    )
    return schemas.base.TokenResponse(
        requestId=h.request_id,
        code=code.value,
        message=const.get_msg_by_code(code, u["settings"]["language"]),
        token=token,
    )


async def forget(h: Headers, req: schemas.account.ForgetPasswordRequest) -> schemas.base.AcknowledgeResponse:
    code = account.email.verify_number(token=req.verificationToken, number_str=req.verification)
    if code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            requestId=h.request_id,
        )
    u, code = await account.manager.reset_password(
        email=req.email,
        password=req.newPassword,
    )
    if code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            requestId=h.request_id,
        )
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, u["settings"]["language"]),
        requestId=h.request_id,
    )


def get_captcha_img():
    token, data = account.app_captcha.generate(length=4, sound=False)
    return StreamingResponse(
        data["img"],
        headers={
            "X-Captcha-Token": token
        },
        media_type="image/png",
    )


def __check_and_send_email(
        email: str,
        token: str,
        code_str: str,
        language: str,
) -> Tuple[str, int, const.Code]:
    code = account.app_captcha.verify_captcha(token=token, code_str=code_str)

    if code != const.Code.OK:
        return "", 0, code

    numbers = "".join([str(randint(0, 9)) for _ in range(6)])
    expired_min = 10
    code = account.email.email_server.send(
        recipient=email,
        numbers=numbers,
        expire=expired_min,
        language=language,
    )
    return numbers, expired_min, code


def email_send_code(
        h: Headers,
        req: schemas.account.EmailVerificationRequest
) -> schemas.base.TokenResponse:
    if req.language not in [lang.value for lang in const.Language.__members__.values()]:
        req.language = const.Language.EN.value
    numbers, expired_min, code = __check_and_send_email(
        email=req.email,
        token=req.captchaToken,
        code_str=req.captchaCode,
        language=req.language,
    )
    if code != const.Code.OK:
        return schemas.base.TokenResponse(
            code=code.value,
            message=const.get_msg_by_code(code, req.language),
            requestId=h.request_id,
        )

    token = account.email.encode_number(number=numbers, expired_min=expired_min)
    return schemas.base.TokenResponse(
        requestId=h.request_id,
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, req.language),
        token=token,
    )
