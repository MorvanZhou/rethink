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
            result=None
        )
    query, recommended_nodes = models.node.cursor_query(
        uid=td.uid,
        nid=req.nid,
        cursor_text=req.textBeforeCursor,
    )
    code = const.Code.OK
    return schemas.search.CursorQueryResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
        result=schemas.search.CursorQueryResponse.Result(
            nodes=[schemas.node.NodesInfoResponse.NodeInfo(
                id=n["id"],
                title=n["title"],
                snippet=n["snippet"],
                type=n["type"],
                createdAt=datetime2str(n["_id"].generation_time),
                modifiedAt=datetime2str(n["modifiedAt"]),
            ) for n in recommended_nodes
            ],
            query=query,
        )
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
    nodes = models.node.search_user_node(
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
        nodes=[schemas.node.NodesInfoResponse.NodeInfo(
            id=n["id"],
            title=n["title"],
            snippet=n["snippet"],
            type=n["type"],
            createdAt=datetime2str(n["_id"].generation_time),
            modifiedAt=datetime2str(n["modifiedAt"]),
        ) for n in nodes],
    )


def add_to_recent_search_history(
        td: TokenDecode,
        req: schemas.search.AddToRecentSearchHistRequest
) -> schemas.base.AcknowledgeResponse:
    if td.code != const.Code.OK:
        return schemas.base.AcknowledgeResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
        )
    code = models.node.add_to_recent_history(uid=td.uid, nid=req.nid, to_nid=req.toNid)
    return schemas.base.AcknowledgeResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
    )
