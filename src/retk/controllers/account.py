from random import randint
from typing import Tuple

from fastapi.responses import StreamingResponse

from retk import config
from retk import const
from retk.controllers import schemas
from retk.controllers.utils import json_exception
from retk.core import account, user
from retk.models.tps import AuthedUser
from retk.utils import jwt_encode


async def signup(
        au: AuthedUser,
        req: schemas.account.SignupRequest,
) -> schemas.account.TokenResponse:
    if not const.Language.is_valid(req.language):
        req.language = const.Language.EN.value
    code = account.app_captcha.verify_captcha(token=req.captchaToken, code_str=req.captchaCode)
    if code != const.Code.OK:
        raise json_exception(
            request_id=au.request_id,
            code=code,
            language=req.language,
        )

    new_user, code = await account.manager.signup(
        req.email,
        req.password,
        req.language,
    )
    if code != const.Code.OK:
        raise json_exception(
            request_id=au.request_id,
            code=code,
            language=req.language,
        )

    token = jwt_encode(
        exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
        data={"uid": new_user["id"], "language": req.language},
    )
    return schemas.account.TokenResponse(
        requestId=au.request_id,
        token=token,
    )


async def login(
        au: AuthedUser,
        req: schemas.account.LoginRequest,
) -> schemas.account.TokenResponse:
    # TODO: 后台应记录成功登录用户名和 IP、时间.
    #  当尝试登录 IP 不在历史常登录 IP 地理位置时，应进行多因素二次验证用户身份，防止用户因密码泄漏被窃取账户
    u, code = await account.manager.get_user_by_email(req.email)
    if code != const.Code.OK:
        raise json_exception(
            request_id=au.request_id,
            code=code,
            language=req.language,
        )

    if not await account.manager.is_right_password(
            email=u["email"],
            hashed=u["hashed"],
            password=req.password,
    ):
        code = const.Code.ACCOUNT_OR_PASSWORD_ERROR
        raise json_exception(
            request_id=au.request_id,
            code=code,
            language=req.language,
        )
    token = jwt_encode(
        exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
        data={"uid": u["id"], "language": u["settings"]["language"]},
    )
    return schemas.account.TokenResponse(
        requestId=au.request_id,
        token=token,
    )


async def forget(
        au: AuthedUser,
        req: schemas.account.ForgetPasswordRequest
) -> schemas.RequestIdResponse:
    code = account.email.verify_number(token=req.verificationToken, number_str=req.verification)
    if code != const.Code.OK:
        raise json_exception(
            request_id=au.request_id,
            code=code,
            language=req.language,
        )
    u, code = await user.get_by_email(email=req.email)
    if code != const.Code.OK:
        raise json_exception(
            request_id=au.request_id,
            code=code,
            language=req.language,
        )

    if u is None:
        raise json_exception(
            request_id=au.request_id,
            code=const.Code.INVALID_AUTH,
            language=req.language,
        )

    code = await user.reset_password(
        uid=u["id"],
        hashed=account.manager.hash_password(password=req.newPassword, email=req.email)
    )
    if code != const.Code.OK:
        raise json_exception(
            request_id=au.request_id,
            code=code,
            language=const.Language.EN.value,
        )
    return schemas.RequestIdResponse(
        requestId=au.request_id,
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


async def email_send_code(
        au: AuthedUser,
        req: schemas.account.EmailVerificationRequest
) -> schemas.account.TokenResponse:
    if req.language not in [lang.value for lang in const.Language.__members__.values()]:
        req.language = const.Language.EN.value

    if not req.userExistOk:
        u, code = await user.get_by_email(email=req.email)
        if code != const.Code.OK:
            raise json_exception(
                request_id=au.request_id,
                code=code,
                language=req.language,
            )
        if u is not None:
            raise json_exception(
                request_id=au.request_id,
                code=const.Code.ACCOUNT_EXIST_TRY_FORGET_PASSWORD,
                language=req.language,
            )

    numbers, expired_min, code = __check_and_send_email(
        email=req.email,
        token=req.captchaToken,
        code_str=req.captchaCode,
        language=req.language,
    )
    if code != const.Code.OK:
        raise json_exception(
            request_id=au.request_id,
            code=code,
            language=req.language,
        )

    token = account.email.encode_number(number=numbers, expired_min=expired_min)
    return schemas.account.TokenResponse(
        requestId=au.request_id,
        token=token,
    )
