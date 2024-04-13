from rethink import utils
from rethink.controllers import schemas
from rethink.controllers.utils import maybe_raise_json_exception
from rethink.models.tps import AuthedUser


async def get_latest_version(
        au: AuthedUser,
) -> schemas.app_system.LatestVersionResponse:
    version, code = await utils.get_latest_version()
    maybe_raise_json_exception(au=au, code=code)

    return schemas.app_system.LatestVersionResponse(
        requestId=au.request_id,
        version=version
    )
