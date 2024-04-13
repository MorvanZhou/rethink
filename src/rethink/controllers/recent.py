from rethink import const, core
from rethink.controllers import schemas
from rethink.controllers.utils import maybe_raise_json_exception
from rethink.models.tps import AuthedUser


async def add_recent_at_node(
        au: AuthedUser,
        req: schemas.recent.AddToRecentSearchHistRequest
) -> schemas.base.AcknowledgeResponse:
    code = await core.recent.added_at_node(au=au, nid=req.nid, to_nid=req.toNid)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, au.language),
        requestId=au.request_id,
    )


async def get_recent_searched(
        au: AuthedUser,
) -> schemas.recent.GetRecentSearchResponse:
    code = const.Code.OK
    return schemas.recent.GetRecentSearchResponse(
        code=code.value,
        message=const.get_msg_by_code(code, au.language),
        requestId=au.request_id,
        queries=au.u.last_state.recent_search,
    )
