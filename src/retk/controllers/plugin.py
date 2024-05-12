from retk import const, config
from retk.controllers import schemas
from retk.controllers.utils import maybe_raise_json_exception, json_exception
from retk.core import node
from retk.models.tps import AuthedUser
from retk.plugins.base import get_plugins, event_plugin_map


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
        requestId=au.request_id,
        plugins=plugins
    )


async def __render(
        au: AuthedUser,
        pid: str,
        nid: str = "",
):
    plugins = get_plugins()
    if pid not in plugins:
        return maybe_raise_json_exception(au=au, code=const.CodeEnum.PLUGIN_NOT_FOUND)

    try:
        plugin = plugins[pid]
    except KeyError:
        return maybe_raise_json_exception(au=au, code=const.CodeEnum.PLUGIN_NOT_FOUND)

    try:
        if nid != "":
            n, code = await node.get(au=au, nid=nid)
            maybe_raise_json_exception(au=au, code=code)

            html = plugin.render_editor_side(
                uid=au.u.id, nid=nid, md=n["md"], language=au.language
            )
        else:
            html = plugin.render_plugin_home(language=au.language)

    except NotImplementedError:
        html = plugin.description
    return schemas.plugin.RenderPluginResponse(
        requestId=au.request_id,
        html=html,
    )


async def render_plugin_home(
        au: AuthedUser,
        pid: str,
) -> schemas.plugin.RenderPluginResponse:
    return await __render(au=au, pid=pid)


async def render_editor_side(
        au: AuthedUser,
        pid: str,
        nid: str,
) -> schemas.plugin.RenderPluginResponse:
    return await __render(au=au, pid=pid, nid=nid)


async def plugin_call(
        req: schemas.plugin.PluginCallRequest,
) -> schemas.plugin.PluginCallResponse:
    if not config.is_local_db():
        raise json_exception(
            request_id=req.requestId,
            code=const.CodeEnum.NOT_PERMITTED,
            language=const.LanguageEnum.EN.value,
            log_msg="plugin call is not allowed in production",
        )
    plugins = get_plugins()
    try:
        plugin = plugins[req.pluginId]
    except KeyError:
        return schemas.plugin.PluginCallResponse(
            success=False,
            message="plugin not found",
            requestId=req.requestId,
            pluginId=req.pluginId,
            method=req.method,
            data=None,
        )

    res = plugin.handle_api_call(req.method, req.data)
    return schemas.plugin.PluginCallResponse(
        success=res.success,
        message=res.message,
        requestId=req.requestId,
        pluginId=req.pluginId,
        method=req.method,
        data=res.data,
    )
