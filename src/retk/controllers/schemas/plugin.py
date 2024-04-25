from typing import List, Any

from pydantic import BaseModel, Field

from retk.const import settings


class PluginsResponse(BaseModel):
    class Plugin(BaseModel):
        id: str
        name: str
        version: str
        description: str
        author: str
        iconSrc: str

    requestId: str
    plugins: List[Plugin]


class RenderPluginResponse(BaseModel):
    requestId: str
    html: str


class PluginCallRequest(BaseModel):
    requestId: str = Field(description="request id", max_length=settings.REQUEST_ID_MAX_LENGTH, default="")
    pluginId: str = Field(max_length=settings.PLUGIN_ID_MAX_LENGTH)
    method: str
    data: Any


class PluginCallResponse(BaseModel):
    success: bool
    message: str
    requestId: str
    pluginId: str
    method: str
    data: Any
