from typing import List

from rethink import const, core
from rethink.controllers import schemas
from rethink.controllers.utils import Headers, datetime2str
from rethink.models import tps
from rethink.utils import contain_only_http_link, get_title_description_from_link


def __get_node_data(n: tps.Node) -> schemas.node.NodeData:
    from_nodes: List[schemas.node.NodeData.LinkedNode] = []
    to_nodes: List[schemas.node.NodeData.LinkedNode] = []
    for nodes, n_nodes in zip(
            [from_nodes, to_nodes],
            [n.get("fromNodes", []), n.get("toNodes", [])]):
        for _n in n_nodes:
            nodes.append(
                schemas.node.NodeData.LinkedNode(
                    id=_n["id"],
                    title=_n["title"],
                    md=_n["md"],
                    snippet=_n["snippet"],
                    type=_n["type"],
                    disabled=_n["disabled"],
                    inTrash=_n["inTrash"],
                    createdAt=datetime2str(_n["_id"].generation_time),
                    modifiedAt=datetime2str(_n["modifiedAt"]),
                )
            )
    return schemas.node.NodeData(
        id=n["id"],
        md=n["md"],
        title=n["title"],
        snippet=n["snippet"],
        type=n["type"],
        disabled=n["disabled"],
        createdAt=datetime2str(n["_id"].generation_time),
        modifiedAt=datetime2str(n["modifiedAt"]),
        fromNodes=from_nodes,
        toNodes=to_nodes,
    )


async def post_node(
        h: Headers,
        req: schemas.node.CreateRequest,
) -> schemas.node.CreateResponse:
    if h.code != const.Code.OK:
        return schemas.node.CreateResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            node=None
        )

    n, code = await core.node.post(
        uid=h.uid,
        md=req.md,
        type_=req.type,
        from_nid=req.fromNid,
    )
    if code != const.Code.OK:
        return schemas.node.CreateResponse(
            code=code.value,
            message=const.get_msg_by_code(code, h.language),
            requestId=h.request_id,
            node=None,
        )
    return schemas.node.CreateResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
        node=__get_node_data(n),
    )


async def post_quick_node(
        h: Headers,
        req: schemas.node.CreateRequest,
) -> schemas.node.CreateResponse:
    if h.code != const.Code.OK:
        return schemas.node.CreateResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            node=None
        )

    if contain_only_http_link(req.md) != "":
        title, description = await get_title_description_from_link(
            url=req.md,
            language=h.language,
        )
        if h.language == const.Language.ZH.value:
            desc_prefix = "**描述：**\n\n"
            link_prefix = "*链接：*"
        elif h.language == const.Language.EN.value:
            desc_prefix = "**Description:**\n\n"
            link_prefix = "*Link:* "
        else:
            desc_prefix = "**Description:**\n\n"
            link_prefix = "*Link:* "
        req.md = f"{title}\n\n{desc_prefix}{description}\n\n{link_prefix}[{req.md}]({req.md})"

    return await post_node(
        h=h,
        req=req,
    )


async def get_node(
        h: Headers,
        nid: str,
) -> schemas.node.GetResponse:
    n, code = await core.node.get(uid=h.uid, nid=nid)
    if code != const.Code.OK:
        return schemas.node.GetResponse(
            requestId=h.request_id,
            code=code.value,
            message=const.get_msg_by_code(code, h.language),
            node=None,
        )
    return schemas.node.GetResponse(
        requestId=h.request_id,
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        node=__get_node_data(n),
    )


async def update_md(
        h: Headers,
        req: schemas.node.PatchMdRequest,
        nid: str,
) -> schemas.node.GetResponse:
    if h.code != const.Code.OK:
        return schemas.node.GetResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            node=None
        )
    n, old_n, code = await core.node.update_md(
        uid=h.uid,
        nid=nid,
        md=req.md,
    )
    return schemas.node.GetResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
        node=__get_node_data(n),
    )


async def get_core_nodes(
        h: Headers,
        p: int,
        limit: int,
) -> schemas.node.CoreNodesResponse:
    if h.code != const.Code.OK:
        return schemas.node.CoreNodesResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            data=None,
        )
    nodes, total = await core.node.core_nodes(
        uid=h.uid,
        page=p,
        limit=limit,
    )
    return schemas.node.CoreNodesResponse(
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, h.language),
        requestId=h.request_id,
        data=schemas.node.NodesSearchResponse.Data(
            total=total,
            nodes=[
                schemas.node.NodesSearchResponse.Data.Node(
                    id=n["id"],
                    title=n["title"],
                    snippet=n["snippet"],
                    titleHighlight="",
                    bodyHighlights=[],
                    score=0,
                    type=n["type"],
                    createdAt=datetime2str(n["_id"].generation_time),
                    modifiedAt=datetime2str(n["modifiedAt"]),
                ) for n in nodes],
        ),
    )


async def get_hist_editions(
        h: Headers,
        nid: str,
) -> schemas.node.HistEditionsResponse:
    if h.code != const.Code.OK:
        return schemas.node.HistEditionsResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            versions=[],
        )
    versions, code = await core.node.get_hist_editions(
        uid=h.uid,
        nid=nid,
    )
    return schemas.node.HistEditionsResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
        versions=versions,
    )


async def get_hist_edition_md(
        h: Headers,
        nid: str,
        version: str,
) -> schemas.node.HistEditionMdResponse:
    if h.code != const.Code.OK:
        return schemas.node.HistEditionMdResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            md="",
        )
    md, code = await core.node.get_hist_edition_md(
        uid=h.uid,
        nid=nid,
        version=version,
    )
    return schemas.node.HistEditionMdResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
        md=md,
    )
