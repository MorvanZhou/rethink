from rethink import const
from rethink.controllers import schemas, auth
from rethink.models.verify.verification import (
    verify_numbers,
)


async def reset_password(req: schemas.user.ResetPasswordRequest) -> schemas.base.AcknowledgeResponse:
    code = verify_numbers(token=req.verificationToken, number_str=req.verification)
    if code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            requestId=req.requestId,
        )
    u, code = await auth.reset_password(
        email=req.email,
        password=req.newPassword,
    )

    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, u["language"]),
        requestId=req.requestId,
    )
