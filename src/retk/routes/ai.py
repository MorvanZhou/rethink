from typing import Optional

from fastapi import APIRouter

from retk.controllers import schemas
from retk.controllers.ai import knowledge, llm_settings
from retk.routes import utils

router = APIRouter(
    prefix="/api/ai",
    tags=["ai"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    path="/llm/settings",
    status_code=200,
    response_model=schemas.ai.LLMApiSettingsResponse,
)
async def get_llm_api(
        au: utils.ANNOTATED_AUTHED_USER,
) -> schemas.ai.LLMApiSettingsResponse:
    return await llm_settings.get_llm_api_settings(au=au)


@router.patch(
    path="/llm/settings",
    status_code=200,
    response_model=schemas.ai.LLMApiSettingsResponse,
)
async def change_llm_api(
        au: utils.ANNOTATED_AUTHED_USER,
        req: schemas.ai.LLMApiSettingsRequest,
) -> schemas.ai.LLMApiSettingsResponse:
    return await llm_settings.change_llm_api_settings(
        au=au,
        req=req,
    )


@router.delete(
    path="/llm/settings",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
async def delete_llm_api(
        au: utils.ANNOTATED_AUTHED_USER,
) -> schemas.RequestIdResponse:
    return await llm_settings.delete_llm_api_settings(au=au)


@router.get(
    path="/llm/settings/test",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
async def llm_api_test(
        au: utils.ANNOTATED_AUTHED_USER,
) -> schemas.RequestIdResponse:
    return await llm_settings.llm_api_test(au=au)


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
    path="/extended-nodes/{eid}",
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


@router.delete(
    path="/extended-nodes/{eid}",
    status_code=200,
    response_model=schemas.RequestIdResponse,
)
async def reject_extended_node(
        au: utils.ANNOTATED_AUTHED_USER,
        eid: str,
        referer: Optional[str] = utils.DEPENDS_REFERER,
) -> schemas.RequestIdResponse:
    return await knowledge.reject_extended_node(
        au=au,
        eid=eid,
    )
