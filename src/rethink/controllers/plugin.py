from rethink import const
from rethink.controllers import schemas
from rethink.controllers.utils import Headers
from rethink.core import node
from rethink.plugins.base import get_plugins, event_plugin_map


async def get_all_plugins(
        h: Headers,
        rid: str = "",
) -> schemas.plugin.PluginsResponse:
    if h.code != const.Code.OK:
        return schemas.plugin.PluginsResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
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
        message=const.get_msg_by_code(const.Code.OK, h.language),
        requestId=rid,
        plugins=plugins
    )


async def get_plugins_with_render_editor_side(
        h: Headers,
) -> schemas.plugin.PluginsResponse:
    if h.code != const.Code.OK:
        return schemas.plugin.PluginsResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
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
        message=const.get_msg_by_code(const.Code.OK, h.language),
        requestId=h.request_id,
        plugins=plugins
    )


def __render(
        h: Headers,
        pid: str,
        nid: str = "",
):
    if h.code != const.Code.OK:
        return schemas.plugin.RenderPluginResponse(
            code=h.code.value,
            message=const.get_msg_by_code(h.code, h.language),
            requestId=h.request_id,
            html=""
        )
    plugins = get_plugins()
    if pid not in plugins:
        return schemas.plugin.RenderPluginResponse(
            code=const.Code.PLUGIN_NOT_FOUND.value,
            message=const.get_msg_by_code(const.Code.PLUGIN_NOT_FOUND, h.language),
            requestId=h.request_id,
            html=""
        )

    try:
        plugin = plugins[pid]
    except KeyError:
        html = ""
        code = const.Code.PLUGIN_NOT_FOUND
        return schemas.plugin.RenderPluginResponse(
            code=code.value,
            message=const.get_msg_by_code(code, h.language),
            requestId=h.request_id,
            html=html,
        )

    code = const.Code.OK
    try:
        if nid != "":
            n, code = node.get(uid=h.uid, nid=nid)
            if code != const.Code.OK:
                return schemas.plugin.RenderPluginResponse(
                    code=code.value,
                    message=const.get_msg_by_code(code, h.language),
                    requestId=h.request_id,
                    html=""
                )
            html = plugin.render_editor_side(uid=h.uid, nid=nid, md=n["md"], language=h.language)
        else:
            html = plugin.render_plugin_home(language=h.language)

    except NotImplementedError:
        html = plugin.description
    return schemas.plugin.RenderPluginResponse(
        code=code.value,
        message=const.get_msg_by_code(code, h.language),
        requestId=h.request_id,
        html=html,
    )


async def render_plugin_home(
        h: Headers,
        pid: str,
) -> schemas.plugin.RenderPluginResponse:
    return __render(h, pid=pid)


async def render_editor_side(
        h: Headers,
        pid: str,
        nid: str,
) -> schemas.plugin.RenderPluginResponse:
    code = const.Code.OK
    if code != const.Code.OK:
        return schemas.plugin.RenderPluginResponse(
            code=code.value,
            message=const.get_msg_by_code(code, h.language),
            requestId=h.request_id,
            html=""
        )

    return __render(h, pid=pid, nid=nid)


async def plugin_call(
        h: Headers,
        req: schemas.plugin.PluginCallRequest,
) -> schemas.plugin.PluginCallResponse:
    plugins = get_plugins()
    try:
        plugin = plugins[req.pluginId]
    except KeyError:
        code = const.Code.PLUGIN_NOT_FOUND
        return schemas.plugin.PluginCallResponse(
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            requestId=h.request_id,
            method=req.method,
            data=None,
        )
    data = plugin.handle_api_call(req.method, req.data)
    return schemas.plugin.PluginCallResponse(
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, const.Language.EN.value),
        requestId=h.request_id,
        pluginId=req.pluginId,
        method=req.method,
        data=data,
    )
