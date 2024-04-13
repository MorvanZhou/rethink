from typing import List, Any

from pydantic import BaseModel, Field

from rethink import const


class PluginsResponse(BaseModel):
    class Plugin(BaseModel):
        id: str
        name: str
        version: str
        description: str
        iconSrc: str

    requestId: str
    plugins: List[Plugin]


class RenderPluginResponse(BaseModel):
    requestId: str
    html: str


class PluginCallRequest(BaseModel):
    pluginId: str = Field(max_length=const.PLUGIN_ID_MAX_LENGTH)
    method: str
    data: Any


class PluginCallResponse(BaseModel):
    requestId: str
    pluginId: str
    method: str
    data: Any
