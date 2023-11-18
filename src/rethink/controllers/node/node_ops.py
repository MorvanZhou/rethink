from typing import List

from rethink import const, models
from rethink.controllers import schemas
from rethink.controllers.utils import TokenDecode, datetime2str


def __get_node_data(n: models.tps.Node) -> schemas.node.NodeData:
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


async def put_node(
        td: TokenDecode,
        req: schemas.node.PutRequest,
) -> schemas.node.PutResponse:
    if td.code != const.Code.OK:
        return schemas.node.PutResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
            node=None
        )

    n, code = await models.node.add(
        uid=td.uid,
        md=req.md,
        type_=req.type,
        from_nid=req.fromNid,
    )
    if code != const.Code.OK:
        return schemas.node.PutResponse(
            code=code.value,
            message=const.get_msg_by_code(code, td.language),
            requestId=req.requestId,
            node=None,
        )
    return schemas.node.PutResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
        node=__get_node_data(n),
    )


async def put_quick_node(
        td: TokenDecode,
        req: schemas.node.PutRequest,
) -> schemas.node.PutResponse:
    if td.code != const.Code.OK:
        return schemas.node.PutResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
            node=None
        )

    if models.utils.contain_only_http_link(req.md) != "":
        title, description = await models.utils.get_title_description_from_link(
            url=req.md,
            language=td.language,
        )
        if td.language == const.Language.ZH.value:
            desc_prefix = "**描述：**\n\n"
            link_prefix = "*链接：*"
        elif td.language == const.Language.EN.value:
            desc_prefix = "**Description:**\n\n"
            link_prefix = "*Link:* "
        else:
            desc_prefix = "**Description:**\n\n"
            link_prefix = "*Link:* "
        req.md = f"{title}\n\n{desc_prefix}{description}\n\n{link_prefix}[{req.md}]({req.md})"

    return await put_node(
        td=td,
        req=req,
    )


async def get_node(
        td: TokenDecode,
        req_id: str,
        nid: str,
) -> schemas.node.GetResponse:
    n, code = await models.node.get(uid=td.uid, nid=nid)
    if code != const.Code.OK:
        return schemas.node.GetResponse(
            requestId=req_id,
            code=code.value,
            message=const.get_msg_by_code(code, td.language),
            node=None,
        )
    return schemas.node.GetResponse(
        requestId=req_id,
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        node=__get_node_data(n),
    )


async def update_node(
        td: TokenDecode,
        req: schemas.node.UpdateRequest,
) -> schemas.node.GetResponse:
    if td.code != const.Code.OK:
        return schemas.node.GetResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
            node=None
        )
    n, code = await models.node.update(
        uid=td.uid,
        nid=req.nid,
        md=req.md,
    )
    return schemas.node.GetResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
        node=__get_node_data(n),
    )
