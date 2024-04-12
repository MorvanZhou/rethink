from rethink import const, utils
from rethink.controllers import schemas
from rethink.controllers.utils import Headers


async def get_latest_version(
        h: Headers,
) -> schemas.app_system.LatestVersionResponse:
    if h.code != const.Code.OK:
        return schemas.app_system.LatestVersionResponse(
            code=h.code.value,
            requestId=h.request_id,
            version=()
        )

    version, code = await utils.get_latest_version()
    return schemas.app_system.LatestVersionResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
        version=version
    )
