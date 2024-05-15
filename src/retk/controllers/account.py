from random import randint
from typing import Tuple

from fastapi.responses import StreamingResponse, JSONResponse

from retk import config, const, safety
from retk.controllers import schemas
from retk.controllers.utils import json_exception
from retk.core import account, user, statistic
from retk.models.tps import AuthedUser
from retk.utils import get_token, jwt_encode, jwt_decode


def set_cookie_response(uid: str, req_id: str, status_code: int, access_token: str, refresh_token: str):
    resp = JSONResponse(
        status_code=status_code,
        content={
            "requestId": req_id,
        })
    s = config.get_settings()

    resp.set_cookie(
        key=const.settings.COOKIE_ACCESS_TOKEN,
        value=access_token,
        httponly=True,  # prevent JavaScript from accessing the cookie, XSS
        secure=safety.cookie_secure,  # only send the cookie over HTTPS
        samesite=safety.cookie_samesite,  # prevent CSRF
        expires=s.JWT_ACCESS_EXPIRED_MINS * 60,  # seconds
        domain=safety.cookie_domain,  # prevent CSRF
    )

    if refresh_token != "":
        resp.set_cookie(
            key=const.settings.COOKIE_REFRESH_TOKEN,
            value=refresh_token,
            httponly=True,  # prevent JavaScript from accessing the cookie, XSS
            secure=safety.cookie_secure,  # only send the cookie over HTTPS
            samesite=safety.cookie_samesite,  # prevent CSRF
            expires=s.JWT_REFRESH_EXPIRED_DAYS * 24 * 60 * 60,  # seconds
            domain=safety.cookie_domain,  # prevent CSRF
        )
        resp.set_cookie(
            key=const.settings.COOKIE_REFRESH_TOKEN_ID,
            value=uid,
            httponly=True,  # prevent JavaScript from accessing the cookie, XSS
            secure=safety.cookie_secure,  # only send the cookie over HTTPS
            samesite=safety.cookie_samesite,  # prevent CSRF
            expires=s.JWT_REFRESH_EXPIRED_DAYS * 24 * 60 * 60,  # seconds
            domain=safety.cookie_domain,  # prevent CSRF
        )
    return resp


async def signup(
        req_id: str,
        req: schemas.account.SignupRequest,
) -> JSONResponse:
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
    return set_cookie_response(
        uid=new_user["id"],
        req_id=req_id,
        status_code=201,
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def login(
        req_id: str,
        req: schemas.account.LoginRequest,
) -> JSONResponse:
    # TODO: 后台应记录成功登录用户名和 IP、时间.
    #  当尝试登录 IP 不在历史常登录 IP 地理位置时，应进行多因素二次验证用户身份，防止用户因密码泄漏被窃取账户
    u, code = await user.get_by_email(req.email, disabled=None, exclude_manager=False)
    if code != const.CodeEnum.OK:
        raise json_exception(
            request_id=req_id,
            code=code,
            language=req.language,
        )
    if u["disabled"]:
        raise json_exception(
            request_id=req_id,
            code=const.CodeEnum.USER_DISABLED,
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
    return set_cookie_response(
        uid=u["id"],
        req_id=req_id,
        status_code=200,
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def auto_login(
        token: str,
        req_id: str,
) -> schemas.user.UserInfoResponse:
    r = schemas.user.UserInfoResponse(
        requestId=req_id,
    )
    if token == "":
        return r
    try:
        payload = jwt_decode(token=token)
    except Exception:  # pylint: disable=broad-except
        return r
    u, code = await user.get(uid=payload["uid"], disabled=False)
    if code != const.CodeEnum.OK:
        return r
    return schemas.user.get_user_info_response_from_u_dict(u, request_id=req_id)


async def logout(
        req_id: str,
        au: AuthedUser,
) -> JSONResponse:
    await statistic.add_user_behavior(
        uid=au.u.id,
        type_=const.UserBehaviorTypeEnum.LOGOUT,
        remark="",
    )

    resp = JSONResponse(
        status_code=200,
        content={
            "requestId": req_id,
        }
    )
    for key in [
        const.settings.COOKIE_ACCESS_TOKEN,
        const.settings.COOKIE_REFRESH_TOKEN,
        const.settings.COOKIE_REFRESH_TOKEN_ID
    ]:
        resp.delete_cookie(
            key=key,
            domain=safety.cookie_domain,
        )

    return resp


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
        token=token,
    )


async def get_new_access_token(
        au: AuthedUser,
) -> JSONResponse:
    access_token = jwt_encode(
        exp_delta=config.get_settings().ACCESS_TOKEN_EXPIRE_DELTA,
        data={
            "is_access": True,
            "uid": au.u.id,
            "language": au.language,
        },
    )
    return set_cookie_response(
        uid=au.u.id,
        req_id=au.request_id,
        status_code=200,
        access_token=access_token,
        refresh_token="",
    )
