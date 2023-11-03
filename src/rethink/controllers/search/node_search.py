from rethink import const, models
from rethink.controllers import schemas
from rethink.controllers.utils import TokenDecode, datetime2str


def cursor_query(
        td: TokenDecode,
        req: schemas.search.CursorQueryRequest,
) -> schemas.search.CursorQueryResponse:
    if td.code != const.Code.OK:
        return schemas.search.CursorQueryResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
            nodes=None
        )
    recommended_nodes = models.node.cursor_query(
        uid=td.uid,
        nid=req.nid,
        cursor_text=req.textBeforeCursor,
    )
    code = const.Code.OK
    return schemas.search.CursorQueryResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
        nodes=[schemas.node.NodesInfoResponse.Data.NodeInfo(
            id=n["id"],
            title=n["title"],
            snippet=n["snippet"],
            type=n["type"],
            createdAt=datetime2str(n["_id"].generation_time),
            modifiedAt=datetime2str(n["modifiedAt"]),
        ) for n in recommended_nodes],
    )


def search_user_nodes(
        td: TokenDecode,
        req: schemas.search.SearchUserNodesRequest,
) -> schemas.node.NodesInfoResponse:
    if td.code != const.Code.OK:
        return schemas.node.NodesInfoResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
            nodes=[],
        )
    nodes, total = models.search.user_node(
        uid=td.uid,
        query=req.query,
        sort_key=req.sortKey,
        sort_order=req.sortOrder,
        page=req.page,
        page_size=req.pageSize,
        nid_exclude=req.nidExclude,
    )
    code = const.Code.OK
    return schemas.node.NodesInfoResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
        data=schemas.node.parse_nodes_info(nodes, total),
    )


def add_to_recent_cursor_search(
        td: TokenDecode,
        req: schemas.search.AddToRecentSearchHistRequest
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = models.search.add_recent_cursor_search(uid=td.uid, nid=req.nid, to_nid=req.toNid)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )


def get_recent(
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
    queries = models.search.get_recent_search(uid=td.uid)
    code = const.Code.OK
    return schemas.search.GetRecentSearchResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=rid,
        queries=queries,
    )


def put_recent(
        td: TokenDecode,
        req: schemas.search.PutRecentSearchRequest,
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = models.search.put_recent_search(uid=td.uid, query=req.query)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )
