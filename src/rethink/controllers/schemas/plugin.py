from typing import List

from pydantic import BaseModel, NonNegativeInt, Field

from rethink import const


class PluginsResponse(BaseModel):
    class Plugin(BaseModel):
        id: str
        name: str
        version: str
        description: str

    code: NonNegativeInt
    message: str
    requestId: str
    plugins: List[Plugin]


class RenderPluginRequest(BaseModel):
    pluginId: str = Field(max_length=const.PLUGIN_ID_MAX_LENGTH)
    requestId: str = Field(default="", max_length=const.REQUEST_ID_MAX_LENGTH)


class RenderPluginResponse(BaseModel):
    code: NonNegativeInt
    message: str
    requestId: str
    html: str
