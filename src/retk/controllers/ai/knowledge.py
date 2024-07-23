from retk import core
from retk.controllers import schemas
from retk.controllers.node.node_ops import get_node_data
from retk.controllers.utils import maybe_raise_json_exception
from retk.models.tps import AuthedUser


async def get_extended_nodes(
        au: AuthedUser,
) -> schemas.ai.GetExtendedNodesResponse:
    docs = await core.ai.llm.knowledge.extended.get_extended_nodes(uid=au.u.id)
    nodes = []
    for doc in docs:
        res = doc["extendMd"].split("\n", 1)
        if len(res) == 2:
            title, content = res
        else:
            title, content = res[0], ""
        node = schemas.ai.GetExtendedNodesResponse.Node(
            id=str(doc["_id"]),
            sourceNid=doc["sourceNid"],
            sourceTitle=doc["sourceMd"].split("\n", 1)[0].strip(),
            title=title.strip(),
            content=content.strip(),
            searchTerms=list(filter(
                lambda x: x != "",
                map(str.strip, doc.get("extendSearchTerms", "").split(","))
            ))[:3],
        )
        nodes.append(node)
    return schemas.ai.GetExtendedNodesResponse(
        requestId=au.request_id,
        nodes=nodes
    )


async def accept_extended_node(
        au: AuthedUser,
        eid: str,
) -> schemas.node.NodeResponse:
    n, code = await core.ai.llm.knowledge.extended.accept_extended_node(
        au=au,
        eid=eid,
    )
    maybe_raise_json_exception(au=au, code=code)
    return schemas.node.NodeResponse(
        requestId=au.request_id,
        node=get_node_data(n),
    )


async def reject_extended_node(
        au: AuthedUser,
        eid: str,
) -> schemas.RequestIdResponse:
    await core.ai.llm.knowledge.extended.reject_extended_node(
        au=au,
        eid=eid,
    )
    return schemas.RequestIdResponse(
        requestId=au.request_id,
    )
