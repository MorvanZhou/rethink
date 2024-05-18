from fastapi import APIRouter

from retk.controllers import plugin as plugin_ops
from retk.controllers import schemas
from retk.routes import utils

router = APIRouter(
    prefix="/api/plugins",
    tags=["plugins"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    path="/",
    status_code=200,
    response_model=schemas.plugin.PluginsResponse,
)
@utils.measure_time_spend
async def get_plugin_home(
        au: utils.ANNOTATED_AUTHED_USER,
) -> schemas.plugin.PluginsResponse:
    return await plugin_ops.get_all_plugins(au=au)


# must before /{pid}, otherwise /editor-side will be treated as /{pid} as a string
@router.get(
    path="/editor-side",
    status_code=200,
    response_model=schemas.plugin.PluginsResponse,
)
@utils.measure_time_spend
async def get_plugin_with_editor_side(
        au: utils.ANNOTATED_AUTHED_USER,
) -> schemas.plugin.PluginsResponse:
    return await plugin_ops.get_plugins_with_render_editor_side(au=au)


@router.get(
    path="/{pid}",
    status_code=200,
    response_model=schemas.plugin.RenderPluginResponse,
)
@utils.measure_time_spend
async def render_plugin_home(
        au: utils.ANNOTATED_AUTHED_USER,
        pid: str = utils.ANNOTATED_PID,
) -> schemas.plugin.RenderPluginResponse:
    return await plugin_ops.render_plugin_home(au=au, pid=pid)


@router.get(
    path="/{pid}/editor-side/{nid}",
    status_code=200,
    response_model=schemas.plugin.RenderPluginResponse,
)
@utils.measure_time_spend
async def render_editor_side(
        au: utils.ANNOTATED_AUTHED_USER,
        pid: str = utils.ANNOTATED_PID,
        nid: str = utils.ANNOTATED_NID,
) -> schemas.plugin.RenderPluginResponse:
    return await plugin_ops.render_editor_side(au=au, pid=pid, nid=nid)


@router.post(
    path="/call",
    status_code=200,
    response_model=schemas.plugin.PluginCallResponse
)
@utils.measure_time_spend
async def plugin_call(
        req: schemas.plugin.PluginCallRequest,
) -> schemas.plugin.PluginCallResponse:
    return await plugin_ops.plugin_call(req=req)
