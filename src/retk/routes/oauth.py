from fastapi import Request, APIRouter
from fastapi.params import Annotated, Path

from retk.controllers import oauth as co
from retk.controllers.schemas.account import TokenResponse
from retk.routes import utils

router = APIRouter(
    prefix="/oauth",
    tags=["oauth"],
    responses={404: {"description": "Not found"}},
)


@router.on_event("startup")
async def startup_event():
    co.init_provider_map()


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
    response_model=TokenResponse,
)
@utils.measure_time_spend
async def callback_github(
        request: Request,
        provider: str = Annotated[str, Path(title="The provider name", max_length=40)],
) -> TokenResponse:
    return await co.provider_callback(provider_name=provider, req=request)
