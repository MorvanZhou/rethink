from typing import Optional

from fastapi import APIRouter, Header

from rethink.controllers import plugin as plugin_ops
from rethink.controllers import schemas
from rethink.routes import utils

router = APIRouter(
    prefix="/api/plugins",
    tags=["user"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    path="/",
    status_code=200,
    response_model=schemas.plugin.PluginsResponse,
)
@utils.measure_time_spend
async def get_plugin_home(
        h: utils.ANNOTATED_HEADERS,
        rid: Optional[str] = Header(None),
) -> schemas.plugin.PluginsResponse:
    return await plugin_ops.get_all_plugins(h=h, rid=rid)


@router.get(
    path="/{pid}",
    status_code=200,
    response_model=schemas.plugin.RenderPluginResponse,
)
@utils.measure_time_spend
async def render_plugin_home(
        h: utils.ANNOTATED_HEADERS,
        pid: str = utils.ANNOTATED_PID,
) -> schemas.plugin.RenderPluginResponse:
    return await plugin_ops.render_plugin_home(h=h, pid=pid)


@router.get(
    path="/editor-side",
    status_code=200,
    response_model=schemas.plugin.PluginsResponse,
)
@utils.measure_time_spend
async def get_plugin_with_editor_side(
        h: utils.ANNOTATED_HEADERS,
) -> schemas.plugin.PluginsResponse:
    return await plugin_ops.get_plugins_with_render_editor_side(h=h)


@router.get(
    path="/{pid}/editor-side/{nid}",
    status_code=200,
    response_model=schemas.plugin.RenderPluginResponse,
)
@utils.measure_time_spend
async def render_editor_side(
        h: utils.ANNOTATED_HEADERS,
        pid: str = utils.ANNOTATED_PID,
        nid: str = utils.ANNOTATED_NID,
) -> schemas.plugin.RenderPluginResponse:
    return await plugin_ops.render_editor_side(h=h, pid=pid, nid=nid)


@router.post(
    path="/call",
    status_code=200,
    response_model=schemas.plugin.PluginCallResponse
)
@utils.measure_time_spend
async def plugin_call(
        h: utils.ANNOTATED_HEADERS,
        req: schemas.plugin.PluginCallRequest,
) -> schemas.plugin.PluginCallResponse:
    return await plugin_ops.plugin_call(h=h, req=req)
