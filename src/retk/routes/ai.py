from typing import Optional

from fastapi import APIRouter

from retk.controllers import schemas
from retk.controllers.ai import knowledge
from retk.routes import utils

router = APIRouter(
    prefix="/api/ai",
    tags=["node"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    path="/extended-nodes",
    status_code=200,
    response_model=schemas.ai.GetExtendedNodesResponse,
)
@utils.measure_time_spend
async def get_extended_nodes(
        au: utils.ANNOTATED_AUTHED_USER,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.ai.GetExtendedNodesResponse:
    return await knowledge.get_extended_nodes(
        au=au,
    )


@router.post(
    path="/extended-nodes/accept/{eid}",
    status_code=201,
    response_model=schemas.node.NodeResponse,
)
async def accept_extended_node(
        au: utils.ANNOTATED_AUTHED_USER,
        eid: str,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.node.NodeResponse:
    return await knowledge.accept_extended_node(
        au=au,
        eid=eid,
    )
