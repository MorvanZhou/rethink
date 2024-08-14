from fastapi import APIRouter

from retk.controllers import schemas, browser_extension
from retk.routes import utils

router = APIRouter(
    prefix="/api/browser-extension",
    tags=["browser"],
    responses={404: {"description": "Not found"}},
)


@router.put(
    "/login",
    status_code=200,
    response_model=schemas.browser_extension.LoginTokenResponse,
)
@utils.measure_time_spend
async def browser_extension_login(
        req_id: utils.ANNOTATED_REQUEST_ID,
        req: schemas.account.LoginRequest,
) -> schemas.browser_extension.LoginTokenResponse:
    return await browser_extension.browser_extension_login(req_id=req_id, req=req)


@router.get(
    "/access-token",
    status_code=200,
    response_model=schemas.browser_extension.LoginTokenResponse,
)
@utils.measure_time_spend
async def browser_extension_refresh_token(
        au: utils.ANNOTATED_REFRESH_TOKEN_BROWSER_EXTENSION,
) -> schemas.browser_extension.LoginTokenResponse:
    return await browser_extension.get_access_token(au=au)


@router.post(
    path="/nodes",
    status_code=201,
    response_model=schemas.node.NodeResponse,
)
@utils.measure_time_spend
async def post_node_from_browser_extension(
        au: utils.ANNOTATED_AUTHED_USER_BROWSER_EXTENSION,
        req: schemas.browser_extension.CreateNodeRequest,
) -> schemas.node.NodeResponse:
    return await browser_extension.post_node(
        au=au,
        req=req,
    )
