from retk import utils, const
from retk._version import __version__
from retk.controllers import schemas
from retk.controllers.utils import maybe_raise_json_exception
from retk.models.tps import AuthedUser


async def get_latest_version(
        au: AuthedUser,
) -> schemas.app_system.LatestVersionResponse:
    remote, code = await utils.get_latest_version()
    maybe_raise_json_exception(au=au, code=code)

    local = utils.parse_version(__version__)
    if local is None:
        code = const.CodeEnum.OPERATION_FAILED
    maybe_raise_json_exception(au=au, code=code)

    has_new_version = False
    for vr, vl in zip(remote, local):
        if vr > vl:
            has_new_version = True
            break

    return schemas.app_system.LatestVersionResponse(
        requestId=au.request_id,
        hasNewVersion=has_new_version,
        local=local,
        remote=remote,
    )
