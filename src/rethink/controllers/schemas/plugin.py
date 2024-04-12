from typing import List, Any

from pydantic import BaseModel, NonNegativeInt, Field

from rethink import const


class PluginsResponse(BaseModel):
    class Plugin(BaseModel):
        id: str
        name: str
        version: str
        description: str
        iconSrc: str

    code: NonNegativeInt
    message: str
    requestId: str
    plugins: List[Plugin]


class RenderPluginResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    html: str


class PluginCallRequest(BaseModel):
    pluginId: str = Field(max_length=const.PLUGIN_ID_MAX_LENGTH)
    method: str
    data: Any


class PluginCallResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    pluginId: str
    method: str
    data: Any
