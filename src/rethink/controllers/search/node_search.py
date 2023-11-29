from rethink import const, models
from rethink.controllers import schemas
from rethink.controllers.utils import TokenDecode


async def cursor_query(
        td: TokenDecode,
        req: schemas.search.CursorQueryRequest,
) -> schemas.search.NodesSearchResponse:
    if td.code != const.Code.OK:
        return schemas.search.NodesSearchResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
            data=None
        )
    nodes, total = await models.search.cursor_query(
        uid=td.uid,
        nid=req.nid,
        cursor_text=req.textBeforeCursor,
        page=req.page,
        page_size=req.pageSize,
    )
    code = const.Code.OK
    return schemas.node.NodesSearchResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
        data=schemas.node.NodesSearchResponse.Data(
            nodes=nodes,
            total=total,
        )
    )


async def search_user_nodes(
        td: TokenDecode,
        req: schemas.search.SearchUserNodesRequest,
) -> schemas.node.NodesSearchResponse:
    if td.code != const.Code.OK:
        return schemas.node.NodesSearchResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
            nodes=[],
        )
    nodes, total = await models.search.search(
        uid=td.uid,
        query=req.query,
        sort_key=req.sortKey,
        reverse=req.reverse,
        page=req.page,
        page_size=req.pageSize,
        exclude_nids=req.nidExclude,
    )
    code = const.Code.OK
    return schemas.node.NodesSearchResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
        data=schemas.node.NodesSearchResponse.Data(
            nodes=nodes,
            total=total,
        )
    )


async def add_to_recent_cursor_search(
        td: TokenDecode,
        req: schemas.search.AddToRecentSearchHistRequest
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = await models.search.add_recent_cursor_search(uid=td.uid, nid=req.nid, to_nid=req.toNid)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )


async def get_recent(
        td: TokenDecode,
        rid: str,
) -> schemas.search.GetRecentSearchResponse:
    if td.code != const.Code.OK:
        return schemas.search.GetRecentSearchResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=rid,
            queries=[],
        )
    queries = await models.search.get_recent_search(uid=td.uid)
    code = const.Code.OK
    return schemas.search.GetRecentSearchResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=rid,
        queries=queries,
    )


async def put_recent(
        td: TokenDecode,
        req: schemas.search.PutRecentSearchRequest,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = await models.search.put_recent_search(uid=td.uid, query=req.query)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )
