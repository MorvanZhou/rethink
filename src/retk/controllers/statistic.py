from retk import core, const
from retk.controllers import schemas
from retk.controllers.utils import json_exception
from retk.models.tps import AuthedUser


async def add_user_behavior(
        au: AuthedUser,
        req: schemas.statistic.UserBehaviorRequest,
) -> schemas.RequestIdResponse:
    try:
        t = const.USER_BEHAVIOR_TYPE_MAP[req.type]
    except KeyError:
        raise json_exception(
            request_id=au.request_id,
            code=const.CodeEnum.INVALID_PARAM,
            language=au.u.language,
        )
    await core.statistic.add_user_behavior(uid=au.u.id, type_=t, remark=req.remark)

    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )
