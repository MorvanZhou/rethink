from fastapi.responses import StreamingResponse

from rethink import const
from rethink.controllers import schemas
from rethink.models.verification import random_captcha, verify_captcha


def get_captcha_img():
    token, data = random_captcha(length=4, sound=False)
    return StreamingResponse(
        data["img"],
        headers={
            "X-Captcha-Token": token
        },
        media_type="image/png",
    )


def verify_captcha_resp(
        req: schemas.verification.VerifyCaptchaRequest
) -> schemas.verification.VerifyCaptchaResponse:
    code = verify_captcha(token=req.token, code_str=req.codeStr)
    _msg = const.CODE_MESSAGES[code]
    if req.language == const.Language.ZH.value:
        msg = _msg.zh
    elif req.language == const.Language.EN.value:
        msg = _msg.en
    else:
        msg = _msg.en
    return schemas.verification.VerifyCaptchaResponse(
        code=code.value,
        message=msg,
        requestId=req.requestId,
    )
