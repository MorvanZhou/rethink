from fastapi import Request, APIRouter
from fastapi.params import Annotated, Path
from fastapi.responses import JSONResponse

from retk.controllers import oauth as co
from retk.routes import utils

router = APIRouter(
    prefix="/api/oauth",
    tags=["oauth"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    path="/login/{provider}",
    status_code=200,
    response_model=co.OAuthResponse,
)
@utils.measure_time_spend
async def login_github(
        provider: str = Annotated[str, Path(title="The provider name", max_length=40)],
) -> co.OAuthResponse:
    return await co.login_provider(provider_name=provider)


@router.get(
    path="/callback/{provider}",
    status_code=200,
)
@utils.measure_time_spend
async def callback_github(
        request: Request,
        provider: str = Annotated[str, Path(title="The provider name", max_length=40)],
) -> JSONResponse:
    return await co.provider_callback(provider_name=provider, req=request)
