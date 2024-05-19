from retk import core
from retk.controllers import schemas
from retk.controllers.utils import maybe_raise_json_exception
from retk.models.tps import AuthedUser
from retk.utils import datetime2str


async def get_system_notice(
        au: AuthedUser,
        notice_id: str,
) -> schemas.notice.SystemNoticeResponse:
    code = await core.notice.mark_system_notice_read(
        uid=au.u.id,
        notice_id=notice_id,
    )
    maybe_raise_json_exception(au=au, code=code)

    n, code = await core.notice.get_system_notice(
        uid=au.u.id,
        notice_id=notice_id,
    )
    maybe_raise_json_exception(au=au, code=code)

    return schemas.notice.SystemNoticeResponse(
        requestId=au.request_id,
        notice=schemas.notice.SystemNoticeResponse.Notice(
            id=str(n["_id"]),
            title=n["title"],
            html=n["html"],
            publishAt=datetime2str(n["publishAt"]),
        ),
    )
