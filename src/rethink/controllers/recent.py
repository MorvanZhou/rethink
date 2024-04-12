from rethink import const, core
from rethink.controllers import schemas
from rethink.controllers.utils import Headers


async def add_recent_at_node(
        h: Headers,
        req: schemas.recent.AddToRecentSearchHistRequest
) -> schemas.base.AcknowledgeResponse:
    if h.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
        )
    code = await core.recent.added_at_node(uid=h.uid, nid=req.nid, to_nid=req.toNid)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
    )


async def get_recent_searched(
        h: Headers,
) -> schemas.recent.GetRecentSearchResponse:
    if h.code != const.Code.OK:
        return schemas.recent.GetRecentSearchResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            queries=[],
        )
    queries = await core.recent.get_recent_searched(uid=h.uid)
    code = const.Code.OK
    return schemas.recent.GetRecentSearchResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
        queries=queries,
    )
