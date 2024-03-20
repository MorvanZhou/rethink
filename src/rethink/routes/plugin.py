from typing import Optional

from fastapi import Depends, APIRouter, Header
from typing_extensions import Annotated

from rethink.controllers import plugin as plugin_ops
from rethink.controllers import schemas
from rethink.controllers.auth import token2uid
from rethink.controllers.utils import TokenDecode
from rethink.routes.utils import measure_time_spend

router = APIRouter(
    prefix="/api",
    tags=["user"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    path="/plugins",
    response_model=schemas.plugin.PluginsResponse,
)
@measure_time_spend
async def get_plugins(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        rid: Optional[str] = Header(None),
) -> schemas.plugin.PluginsResponse:
    return await plugin_ops.get_plugins(td=token_decode, rid=rid)


@router.post(
    path="/plugin",
    response_model=schemas.plugin.RenderPluginResponse,
)
@measure_time_spend
async def render_plugin(
        token_decode: Annotated[TokenDecode, Depends(token2uid)],
        req: schemas.plugin.RenderPluginRequest,
) -> schemas.plugin.RenderPluginResponse:
    return await plugin_ops.render_plugin(td=token_decode, req=req)
