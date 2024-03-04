from rethink import const
from rethink.controllers import schemas, auth
from rethink.controllers.utils import TokenDecode
from rethink.core.user import get, reset_password
from rethink.core.verify.verification import (
    verify_numbers,
)
from rethink.utils import regex


async def forget(req: schemas.user.ForgetPasswordRequest) -> schemas.base.AcknowledgeResponse:
    code = verify_numbers(token=req.verificationToken, number_str=req.verification)
    if code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            requestId=req.requestId,
        )
    u, code = await auth.update_password(
        email=req.email,
        password=req.newPassword,
    )
    if code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            requestId=req.requestId,
        )
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, u["settings"]["language"]),
        requestId=req.requestId,
    )


async def update(
        td: TokenDecode,
        req: schemas.user.UpdatePasswordRequest
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            requestId=req.requestId,
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
        )
    if regex.VALID_PASSWORD.match(req.newPassword) is None:
        code = const.Code.INVALID_PASSWORD
        return schemas.base.AcknowledgeResponse(
            code=code.value,
            message=const.get_msg_by_code(code, td.language),
            requestId=req.requestId,
        )

    u, code = await get(uid=td.uid)
    if code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=code.value,
            message=const.get_msg_by_code(code, td.language),
            requestId=req.requestId,
        )
    ok = await auth.verify_user(u, req.oldPassword)
    if not ok:
        code = const.Code.OLD_PASSWORD_ERROR
        return schemas.base.AcknowledgeResponse(
            code=code.value,
            message=const.get_msg_by_code(code, td.language),
            requestId=req.requestId,
        )

    hashed = auth.hash_password(password=req.newPassword, email=u["email"])
    code = await reset_password(uid=td.uid, hashed=hashed)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )
