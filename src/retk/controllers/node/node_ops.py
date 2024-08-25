from typing import List, Literal

from fastapi.responses import StreamingResponse

from retk import const, core
from retk.controllers import schemas
from retk.controllers.utils import maybe_raise_json_exception, json_exception
from retk.models.tps import AuthedUser, Node
from retk.utils import contain_only_http_link, get_title_description_from_link, datetime2str


def get_node_data(n: Node) -> schemas.node.NodeData:
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
        favorite=n.get("favorite", False),
        fromNodes=from_nodes,
        toNodes=to_nodes,
    )


async def post_node(
        au: AuthedUser,
        req: schemas.node.CreateRequest,
        is_quick: bool = False,
) -> schemas.node.NodeResponse:
    n, code = await core.node.post(
        au=au,
        md=req.md,
        type_=req.type,
        from_nid=req.fromNid,
    )
    maybe_raise_json_exception(au=au, code=code)
    b_type = const.UserBehaviorTypeEnum.NODE_CREATE if not is_quick else const.UserBehaviorTypeEnum.NODE_QUICK_CREATE
    await core.statistic.add_user_behavior(
        uid=au.u.id,
        type_=b_type,
        remark=n['id'],
    )
    return schemas.node.NodeResponse(
        requestId=au.request_id,
        node=get_node_data(n),
    )


async def post_quick_node(
        au: AuthedUser,
        req: schemas.node.CreateRequest,
) -> schemas.node.NodeResponse:
    if contain_only_http_link(req.md) != "":
        title, description = await get_title_description_from_link(
            url=req.md,
            language=au.language,
        )
        if au.language == const.LanguageEnum.ZH.value:
            desc_prefix = "**描述：**\n\n"
            link_prefix = "*链接：*"
        elif au.language == const.LanguageEnum.EN.value:
            desc_prefix = "**Description:**\n\n"
            link_prefix = "*Link:* "
        else:
            desc_prefix = "**Description:**\n\n"
            link_prefix = "*Link:* "
        req.md = f"{title}\n\n{desc_prefix}{description}\n\n{link_prefix}[{req.md}]({req.md})"

    return await post_node(
        au=au,
        req=req,
        is_quick=True,
    )


async def get_node(
        au: AuthedUser,
        nid: str,
) -> schemas.node.NodeResponse:
    n, code = await core.node.get(au=au, nid=nid)
    maybe_raise_json_exception(au=au, code=code)

    return schemas.node.NodeResponse(
        requestId=au.request_id,
        node=get_node_data(n),
    )


async def update_md(
        au: AuthedUser,
        req: schemas.node.PatchMdRequest,
        nid: str,
) -> schemas.node.NodeResponse:
    n, _, code = await core.node.update_md(
        au=au,
        nid=nid,
        md=req.md,
    )
    maybe_raise_json_exception(au=au, code=code)

    return schemas.node.NodeResponse(
        requestId=au.request_id,
        node=get_node_data(n),
    )


async def get_core_nodes(
        au: AuthedUser,
        p: int,
        limit: int,
) -> schemas.node.NodesSearchResponse:
    nodes, total = await core.node.core_nodes(
        au=au,
        page=p,
        limit=limit,
    )
    return schemas.node.NodesSearchResponse(
        requestId=au.request_id,
        data=_get_node_search_response_data(nodes=nodes, total=total),
    )


def _get_node_search_response_data(nodes: List[Node], total: int) -> schemas.node.NodesSearchResponse.Data:
    return schemas.node.NodesSearchResponse.Data(
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
                favorite=n.get("favorite", False)
            ) for n in nodes],
        total=total,
    )


async def get_hist_editions(
        au: AuthedUser,
        nid: str,
) -> schemas.node.HistEditionsResponse:
    versions, code = await core.node.get_hist_editions(
        au=au,
        nid=nid,
    )
    maybe_raise_json_exception(au=au, code=code)

    return schemas.node.HistEditionsResponse(
        requestId=au.request_id,
        versions=versions,
    )


async def get_hist_edition_md(
        au: AuthedUser,
        nid: str,
        version: str,
) -> schemas.node.HistEditionMdResponse:
    md, code = await core.node.get_hist_edition_md(
        au=au,
        nid=nid,
        version=version,
    )
    maybe_raise_json_exception(au=au, code=code)

    return schemas.node.HistEditionMdResponse(
        requestId=au.request_id,
        md=md,
    )


async def set_favorite(
        au: AuthedUser,
        nid: str,
        favorite: bool,
) -> schemas.RequestIdResponse:
    await core.node.set_favorite(
        au=au,
        nid=nid,
        favorite=favorite,
    )

    c_enum = const.UserBehaviorTypeEnum
    await core.statistic.add_user_behavior(
        uid=au.u.id,
        type_=c_enum.NODE_FAVORITE_ADD if favorite else c_enum.NODE_FAVORITE_REMOVE,
        remark=nid,
    )
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )


async def get_favorite_nodes(
        au: AuthedUser,
        p: int,
        limit: int,
) -> schemas.node.NodesSearchResponse:
    nodes, total = await core.node.get_favorite(
        au=au,
        page=p,
        limit=limit,
    )
    await core.statistic.add_user_behavior(
        uid=au.u.id,
        type_=const.UserBehaviorTypeEnum.NODE_FAVORITE_VIEW,
        remark="",
    )
    return schemas.node.NodesSearchResponse(
        requestId=au.request_id,
        data=_get_node_search_response_data(nodes=nodes, total=total),
    )


async def stream_md_export(
        au: AuthedUser,
        nid: str,
        format_: Literal["md", "html", "pdf"],
) -> StreamingResponse:
    media_type, title, file, code = await core.node.md_export(
        au=au,
        nid=nid,
        format_=format_,
    )
    maybe_raise_json_exception(au=au, code=code)
    # stream send file chunk
    if media_type == "application/zip":
        headers = {
            "Content-Disposition": f"attachment; filename={title}.zip",
        }
    elif media_type == "text/markdown":
        headers = {
            "Content-Disposition": f"attachment; filename={title}.md",
        }
    elif media_type == "text/html":
        headers = {
            "Content-Disposition": f"attachment; filename={title}.html",
        }
    elif media_type == "application/pdf":
        headers = {
            "Content-Disposition": f"attachment; filename={title}.pdf",
        }
    else:
        raise json_exception(
            request_id=au.request_id,
            uid=au.u.id,
            code=const.CodeEnum.OPERATION_FAILED,
            language=au.language,
        )
    headers["Request-Id"] = au.request_id

    # iter file by chunk size
    async def iter_file():
        while True:
            chunk = file.read(1024)
            if not chunk:
                break
            yield chunk

    await core.statistic.add_user_behavior(
        uid=au.u.id,
        type_=const.UserBehaviorTypeEnum.NODE_DATA_EXPORT,
        remark=f"{format_}_{nid}",
    )
    return StreamingResponse(
        content=iter_file(),
        media_type=media_type,
        headers=headers,
    )
