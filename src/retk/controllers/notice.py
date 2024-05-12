from retk import const
from retk.controllers import schemas
from retk.models.tps import AuthedUser


async def put_system_notice(
        au: AuthedUser,
        req: schemas.notice.ManagerNoticeDeliveryRequest,
) -> schemas.RequestIdResponse:
    if const.USER_TYPE.id2config(au.u.type) not in (const.USER_TYPE.ADMIN, const.USER_TYPE.MANAGER):
        return const.CodeEnum.NOT_PERMITTED
