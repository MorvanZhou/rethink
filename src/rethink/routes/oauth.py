from fastapi import Request, APIRouter

from rethink.controllers import oauth as co
from rethink.controllers.schemas.base import TokenResponse
from rethink.routes.utils import measure_time_spend

router = APIRouter(
    prefix="/oauth",
    tags=["oauth"],
    responses={404: {"description": "Not found"}},
)


@router.get(path="/login/github", response_model=co.OAuthResponse)
@measure_time_spend
async def login_github() -> co.OAuthResponse:
    return await co.login_github()


@router.get(path="/callback/github", response_model=TokenResponse)
@measure_time_spend
async def callback_github(request: Request) -> TokenResponse:
    return await co.callback_github(req=request)

# @router.get(path="/login/facebook", response_model=co.OAuthResponse)
# @measure_time_spend
# async def login_facebook() -> co.OAuthResponse:
#     return await co.login_facebook()
#
#
# @router.get(path="/callback/facebook", response_model=cu.UserLoginResponse)
# @measure_time_spend
# async def callback_facebook(request: Request) -> cu.UserLoginResponse:
#     return await co.callback_facebook(req=request)
