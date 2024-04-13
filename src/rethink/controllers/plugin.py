from rethink import const
from rethink.controllers import schemas
from rethink.controllers.utils import maybe_raise_json_exception
from rethink.core import node
from rethink.models.tps import AuthedUser
from rethink.plugins.base import get_plugins, event_plugin_map


async def get_all_plugins(
        au: AuthedUser,
) -> schemas.plugin.PluginsResponse:
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
        message=const.get_msg_by_code(const.Code.OK, au.language),
        requestId=au.request_id,
        plugins=plugins
    )


async def get_plugins_with_render_editor_side(
        au: AuthedUser,
) -> schemas.plugin.PluginsResponse:
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
        message=const.get_msg_by_code(const.Code.OK, au.language),
        requestId=au.request_id,
        plugins=plugins
    )


def __render(
        au: AuthedUser,
        pid: str,
        nid: str = "",
):
    plugins = get_plugins()
    if pid not in plugins:
        return maybe_raise_json_exception(au=au, code=const.Code.PLUGIN_NOT_FOUND)

    try:
        plugin = plugins[pid]
    except KeyError:
        return maybe_raise_json_exception(au=au, code=const.Code.PLUGIN_NOT_FOUND)

    try:
        if nid != "":
            n, code = node.get(au=au, nid=nid)
            maybe_raise_json_exception(au=au, code=code)

            html = plugin.render_editor_side(
                uid=au.u.id, nid=nid, md=n["md"], language=au.language
            )
        else:
            html = plugin.render_plugin_home(language=au.language)

    except NotImplementedError:
        html = plugin.description
    return schemas.plugin.RenderPluginResponse(
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, au.language),
        requestId=au.request_id,
        html=html,
    )


async def render_plugin_home(
        au: AuthedUser,
        pid: str,
) -> schemas.plugin.RenderPluginResponse:
    return __render(au=au, pid=pid)


async def render_editor_side(
        au: AuthedUser,
        pid: str,
        nid: str,
) -> schemas.plugin.RenderPluginResponse:
    return __render(au=au, pid=pid, nid=nid)


async def plugin_call(
        au: AuthedUser,
        req: schemas.plugin.PluginCallRequest,
) -> schemas.plugin.PluginCallResponse:
    plugins = get_plugins()
    try:
        plugin = plugins[req.pluginId]
    except KeyError:
        return maybe_raise_json_exception(au=au, code=const.Code.PLUGIN_NOT_FOUND)

    data = plugin.handle_api_call(req.method, req.data)
    return schemas.plugin.PluginCallResponse(
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, const.Language.EN.value),
        requestId=au.request_id,
        pluginId=req.pluginId,
        method=req.method,
        data=data,
    )
