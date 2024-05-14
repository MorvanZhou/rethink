from random import randint
from typing import Tuple

from fastapi.responses import StreamingResponse

from retk import config
from retk import const
from retk.controllers import schemas
from retk.controllers.utils import json_exception
from retk.core import account, user, statistic
from retk.models.tps import AuthedUser
from retk.utils import get_token, jwt_encode


async def signup(
        req_id: str,
        req: schemas.account.SignupRequest,
) -> schemas.account.TokenResponse:
    if not const.LanguageEnum.is_valid(req.language):
        req.language = const.LanguageEnum.EN.value
    code = account.app_captcha.verify_captcha(token=req.verificationToken, code_str=req.verification)
    if code != const.CodeEnum.OK:
        raise json_exception(
            request_id=req_id,
            code=code,
            language=req.language,
        )

    new_user, code = await account.manager.signup(
        req.email,
        req.password,
        req.language,
    )
    if code != const.CodeEnum.OK:
        raise json_exception(
            request_id=req_id,
            code=code,
            language=req.language,
        )

    access_token, refresh_token = get_token(
        uid=new_user["id"],
        language=req.language,
    )
    return schemas.account.TokenResponse(
        requestId=req_id,
        accessToken=access_token,
        refreshToken=refresh_token,
    )


async def login(
        req_id: str,
        req: schemas.account.LoginRequest,
) -> schemas.account.TokenResponse:
    # TODO: 后台应记录成功登录用户名和 IP、时间.
    #  当尝试登录 IP 不在历史常登录 IP 地理位置时，应进行多因素二次验证用户身份，防止用户因密码泄漏被窃取账户
    u, code = await user.get_by_email(req.email, disabled=False, exclude_manager=False)
    if code != const.CodeEnum.OK:
        raise json_exception(
            request_id=req_id,
            code=code,
            language=req.language,
        )

    if not await account.manager.is_right_password(
            email=u["email"],
            hashed=u["hashed"],
            password=req.password,
    ):
        code = const.CodeEnum.ACCOUNT_OR_PASSWORD_ERROR
        raise json_exception(
            request_id=req_id,
            code=code,
            language=req.language,
        )
    access_token, refresh_token = get_token(
        uid=u["id"],
        language=u["settings"]["language"],
    )
    await statistic.add_user_behavior(
        uid=u["id"],
        type_=const.UserBehaviorTypeEnum.LOGIN,
        remark="",
    )
    return schemas.account.TokenResponse(
        requestId=req_id,
        accessToken=access_token,
        refreshToken=refresh_token,
    )


async def forget(
        req_id: str,
        req: schemas.account.ForgetPasswordRequest
) -> schemas.RequestIdResponse:
    code = account.email.verify_number(token=req.verificationToken, number_str=req.verification)
    if code != const.CodeEnum.OK:
        raise json_exception(
            request_id=req_id,
            code=code,
            language=req.language,
        )
    u, code = await user.get_by_email(email=req.email)
    if code != const.CodeEnum.OK:
        raise json_exception(
            request_id=req_id,
            code=code,
            language=req.language,
        )

    if u is None:
        raise json_exception(
            request_id=req_id,
            code=const.CodeEnum.INVALID_AUTH,
            language=req.language,
        )

    code = await user.reset_password(
        uid=u["id"],
        hashed=account.manager.hash_password(password=req.newPassword, email=req.email)
    )
    if code != const.CodeEnum.OK:
        raise json_exception(
            request_id=req_id,
            code=code,
            language=const.LanguageEnum.EN.value,
        )
    return schemas.RequestIdResponse(
        requestId=req_id,
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
) -> Tuple[str, int, const.CodeEnum]:
    # verify captcha code in image
    code = account.app_captcha.verify_captcha(token=token, code_str=code_str)

    if code != const.CodeEnum.OK:
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
        req_id: str,
        req: schemas.account.EmailVerificationRequest
) -> schemas.account.TokenResponse:
    if req.language not in [lang.value for lang in const.LanguageEnum.__members__.values()]:
        req.language = const.LanguageEnum.EN.value

    if not req.userExistOk:
        u, code = await user.get_by_email(email=req.email)
        if u is not None:
            raise json_exception(
                request_id=req_id,
                code=const.CodeEnum.ACCOUNT_EXIST_TRY_FORGET_PASSWORD,
                language=req.language,
            )

    numbers, expired_min, code = __check_and_send_email(
        email=req.email,
        token=req.captchaToken,
        code_str=req.captchaCode,
        language=req.language,
    )
    if code != const.CodeEnum.OK:
        raise json_exception(
            request_id=req_id,
            code=code,
            language=req.language,
        )

    token = account.email.encode_number(number=numbers, expired_min=expired_min)
    return schemas.account.TokenResponse(
        requestId=req_id,
        accessToken=token,
        refreshToken="",
    )


async def get_new_access_token(
        au: AuthedUser,
) -> schemas.account.TokenResponse:
    access_token = jwt_encode(
        exp_delta=config.get_settings().ACCESS_TOKEN_EXPIRE_DELTA,
        data={
            "is_access": True,
            "uid": au.u.id,
            "language": au.language,
        },
    )
    return schemas.account.TokenResponse(
        requestId=au.request_id,
        accessToken=access_token,
        refreshToken="",
    )
