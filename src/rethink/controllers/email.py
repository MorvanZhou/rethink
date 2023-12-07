from random import randint
from typing import Tuple

from rethink import const
from rethink.controllers import schemas, auth
from rethink.logger import logger
from rethink.models.verify.email import email_server
from rethink.models.verify.verification import encode_numbers, verify_captcha


def __check_and_send_email(
        email: str,
        token: str,
        code_str: str,
        language: str,
) -> Tuple[str, int, const.Code]:
    code = verify_captcha(token=token, code_str=code_str)

    if code != const.Code.OK:
        return "", 0, code

    numbers = "".join([str(randint(0, 9)) for _ in range(6)])
    expired_min = 10
    code = email_server.send(
        recipient=email,
        numbers=numbers,
        expire=expired_min,
        language=language,
    )
    logger.info(f"send email to {email} with code {numbers}")
    return numbers, expired_min, code


def send_email_verification(req: schemas.user.EmailVerificationRequest) -> schemas.base.TokenResponse:
    if req.language not in const.Language.__members__:
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
            requestId=req.requestId,
        )

    token = encode_numbers(numbers=numbers, expired_min=expired_min)
    return schemas.base.TokenResponse(
        requestId=req.requestId,
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, req.language),
        token=token,
    )


async def check_email_then_send_email_verification(
        req: schemas.user.EmailVerificationRequest,
) -> schemas.base.TokenResponse:
    if req.language not in const.Language.__members__:
        req.language = const.Language.EN.value
    u, code = await auth.get_user_by_email(email=req.email)
    if code == const.Code.OK:
        code = const.Code.EMAIL_OCCUPIED
        return schemas.base.TokenResponse(
            code=code.value,
            message=const.get_msg_by_code(code, req.language),
            requestId=req.requestId,
        )
    return send_email_verification(req=req)
