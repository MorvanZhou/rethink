from rethink import const
from rethink.controllers import schemas
from rethink.controllers.utils import TokenDecode
from rethink.plugins.base import get_plugins, event_plugin_map


async def get_all_plugins(
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
            iconSrc=p.icon_src,
        )
        for p in get_plugins().values()
    ]
    return schemas.plugin.PluginsResponse(
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, td.language),
        requestId=rid,
        plugins=plugins
    )


async def get_plugins_with_render_editor_side(
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
    plugins = []
    for p in event_plugin_map["render_editor_side"]:
        plugins.append(
            schemas.plugin.PluginsResponse.Plugin(
                id=p.id,
                name=p.name,
                version=p.version,
                description=p.description,
                author=p.author,
                iconSrc=p.icon_src,
            )
        )
    return schemas.plugin.PluginsResponse(
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, td.language),
        requestId=rid,
        plugins=plugins
    )


def __render(
        td: TokenDecode,
        req: schemas.plugin.RenderPluginRequest,
        method_name: str,
):
    if td.code != const.Code.OK:
        return schemas.plugin.RenderPluginResponse(
            code=td.code.value,
            message=const.get_msg_by_code(td.code, td.language),
            requestId=req.requestId,
            html=""
        )
    plugins = get_plugins()
    if req.pluginId not in plugins:
        return schemas.plugin.RenderPluginResponse(
            code=const.Code.PLUGIN_NOT_FOUND.value,
            message=const.get_msg_by_code(const.Code.PLUGIN_NOT_FOUND, td.language),
            requestId=req.requestId,
            html=""
        )

    try:
        plugin = plugins[req.pluginId]
    except KeyError:
        html = ""
        code = const.Code.PLUGIN_NOT_FOUND
        return schemas.plugin.RenderPluginResponse(
            code=code.value,
            message=const.get_msg_by_code(code, td.language),
            requestId=req.pluginId,
            html=html,
        )

    code = const.Code.OK
    try:
        if method_name == "render_plugin_home":
            html = plugin.render_plugin_home()
        elif method_name == "render_editor_side":
            html = plugin.render_editor_side()
        else:
            html = ""
            code = const.Code.INVALID_SETTING
    except NotImplementedError:
        html = plugin.description
    return schemas.plugin.RenderPluginResponse(
        code=code.value,
        message=const.get_msg_by_code(code, td.language),
        requestId=req.pluginId,
        html=html,
    )


async def render_plugin_home(
        td: TokenDecode,
        req: schemas.plugin.RenderPluginRequest,
) -> schemas.plugin.RenderPluginResponse:
    return __render(td, req, "render_plugin_home")


async def render_editor_side(
        td: TokenDecode,
        req: schemas.plugin.RenderPluginRequest,
) -> schemas.plugin.RenderPluginResponse:
    return __render(td, req, "render_editor_side")
