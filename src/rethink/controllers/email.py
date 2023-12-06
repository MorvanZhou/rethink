from random import randint

from rethink import const
from rethink.controllers import schemas
from rethink.controllers.utils import match_captcha
from rethink.models.verify.email import email_server
from rethink.models.verify.verification import encode_numbers


def forget_password(req: schemas.user.ForgetPasswordRequest) -> schemas.base.TokenResponse:
    code, msg = match_captcha(token=req.captchaToken, code_str=req.captchaCode, language=req.language)
    if code != const.Code.OK:
        return schemas.base.TokenResponse(
            code=code.value,
            message=msg,
            requestId=req.requestId,
        )

    numbers = "".join([str(randint(0, 9)) for _ in range(6)])
    expire_min = 5
    code = email_server.send_reset_password(
        recipient=req.email,
        numbers=numbers,
        expire=expire_min,
        language=req.language,
    )
    if code != const.Code.OK:
        return schemas.base.TokenResponse(
            code=code.value,
            message=const.get_msg_by_code(code, req.language),
            requestId=req.requestId,
        )

    token = encode_numbers(numbers)
    return schemas.base.TokenResponse(
        requestId=req.requestId,
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, req.language),
        token=token,
    )
