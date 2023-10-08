from typing import List

from rethink import const, models
from rethink.controllers import schemas
from rethink.controllers.utils import TokenDecode, datetime2str


def __split_title_text(text: str) -> (str, str):
    title_text = text.split("\n", maxsplit=1)
    title = title_text[0].strip()
    try:
        text = title_text[1].strip()
    except IndexError:
        text = ""
    return title, text


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
                    text=_n["text"],
                    snippet=_n["snippet"],
                    type=_n["type"],
                    disabled=_n["disabled"],
                    createdAt=datetime2str(_n["_id"].generation_time),
                    modifiedAt=datetime2str(_n["modifiedAt"]),
                )
            )
    return schemas.node.NodeData(
        id=n["id"],
        title=n["title"],
        text=n["text"],
        type=n["type"],
        disabled=n["disabled"],
        createdAt=datetime2str(n["_id"].generation_time),
        modifiedAt=datetime2str(n["modifiedAt"]),
        fromNodes=from_nodes,
        toNodes=to_nodes,
    )


def put_node(
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

    title, text = __split_title_text(text=req.fulltext)
    n, code = models.node.add(
        uid=td.uid,
        title=title,
        text=text,
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


def get_node(
        td: TokenDecode,
        req_id: str,
        nid: str,
) -> schemas.node.GetResponse:
    n, code = models.node.get(uid=td.uid, nid=nid)
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


def update_node(
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
    title, text = __split_title_text(text=req.fulltext)
    n, code = models.node.update(
        uid=td.uid,
        nid=req.nid,
        title=title,
        text=text,
    )
    return schemas.node.GetResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.requestId,
        node=__get_node_data(n),
    )
