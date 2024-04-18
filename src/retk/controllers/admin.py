from retk.controllers import schemas
from retk.controllers.utils import maybe_raise_json_exception
from retk.core import account, user
from retk.models.tps import AuthedUser


async def disable_account_by_id(
        au: AuthedUser,
        uid: str,
) -> schemas.RequestIdResponse:
    code = await account.manager.disable(uid=uid)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def enable_account_by_id(
        au: AuthedUser,
        uid: str,
) -> schemas.RequestIdResponse:
    code = await account.manager.enable(uid=uid)
    maybe_raise_json_exception(au=au, code=code)
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def delete_account_by_id(
        au: AuthedUser,
        uid: str,
) -> schemas.RequestIdResponse:
    await account.manager.delete(uid=uid)
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def disable_account_by_email(
        au: AuthedUser,
        email: str,
) -> schemas.RequestIdResponse:
    u, code = await user.get_by_email(email=email)
    maybe_raise_json_exception(au=au, code=code)

    return await disable_account_by_id(au=au, uid=u["id"])


async def enable_account_by_email(
        au: AuthedUser,
        email: str,
) -> schemas.RequestIdResponse:
    u, code = await user.get_by_email(email=email, disabled=True)
    maybe_raise_json_exception(au=au, code=code)

    return await enable_account_by_id(au=au, uid=u["id"])


async def delete_account_by_email(
        au: AuthedUser,
        email: str,
) -> schemas.RequestIdResponse:
    u, code = await user.get_by_email(email=email, disabled=True)
    if u is None:
        u, code = await user.get_by_email(email=email, disabled=False)
    maybe_raise_json_exception(au=au, code=code)

    return await delete_account_by_id(au=au, uid=u["id"])
