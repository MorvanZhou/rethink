from rethink import const
from rethink.controllers import schemas
from rethink.controllers.utils import TokenDecode
from rethink.plugins.base import get_plugins as ps


async def get_plugins(
        td: TokenDecode,
        rid: str = "",
) -> schemas.plugin.PluginsResponse:
    if td.code != const.Code.OK:
        return schemas.plugin.PluginsResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=rid,
            plugins=[]
        )

    plugins = [
        schemas.plugin.PluginsResponse.Plugin(
            id=p.id,
            name=p.name,
            version=p.version,
            description=p.description,
            author=p.author,
        )
        for p in ps().values()
    ]
    return schemas.plugin.PluginsResponse(
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, td.language),
        requestId=rid,
        plugins=plugins
    )


async def render_plugin(
        td: TokenDecode,
        req: schemas.plugin.RenderPluginRequest,
) -> schemas.plugin.RenderPluginResponse:
    if td.code != const.Code.OK:
        return schemas.plugin.RenderPluginResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
            html=""
        )
    plugins = ps()
    if req.pluginId not in plugins:
        return schemas.plugin.RenderPluginResponse(
            code=const.Code.PLUGIN_NOT_FOUND.value,
            message=const.get_msg_by_code(const.Code.PLUGIN_NOT_FOUND, td.language),
            requestId=req.requestId,
            html=""
        )
    try:
        plugin = plugins[req.pluginId]
        html = plugin.render()
        code = const.Code.OK
    except KeyError:
        html = ""
        code = const.Code.PLUGIN_NOT_FOUND
    return schemas.plugin.RenderPluginResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.pluginId,
        html=html,
    )
