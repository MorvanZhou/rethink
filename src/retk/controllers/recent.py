from retk import core
from retk.controllers import schemas
from retk.controllers.utils import maybe_raise_json_exception
from retk.models.tps import AuthedUser


async def add_recent_at_node(
        au: AuthedUser,
        req: schemas.recent.AtNodeRequest
) -> schemas.RequestIdResponse:
    code = await core.recent.added_at_node(au=au, nid=req.nid, to_nid=req.toNid)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def get_recent_searched(
        au: AuthedUser,
) -> schemas.recent.GetRecentSearchResponse:
    return schemas.recent.GetRecentSearchResponse(
        requestId=au.request_id,
        queries=au.u.last_state.recent_search,
    )
