from typing import Dict

from fastapi import Request

from rethink import config, const, core, utils
from rethink.controllers.utils import json_exception
from rethink.depend.sso.base import SSOLoginError, SSOBase
from rethink.depend.sso.facebook import FacebookSSO
from rethink.depend.sso.github import GithubSSO
# from rethink.depend.sso.qq import QQSSO
from .schemas.account import TokenResponse
from .schemas.oauth import OAuthResponse

sso_map: Dict[str, SSOBase] = {}
user_source_map: Dict[str, int] = {}


def init_provider_map():
    sso_map.update({
        "github": GithubSSO(
            client_id=config.get_settings().OAUTH_CLIENT_ID_GITHUB,
            client_secret=config.get_settings().OAUTH_CLIENT_SEC_GITHUB,
            redirect_uri=f"{config.get_settings().OAUTH_REDIRECT_URL}/github",
            allow_insecure_http=False,
            use_state=False,
        ),
        "facebook": FacebookSSO(
            client_id=config.get_settings().OAUTH_CLIENT_ID_FACEBOOK,
            client_secret=config.get_settings().OAUTH_CLIENT_SEC_FACEBOOK,
            redirect_uri=f"{config.get_settings().OAUTH_REDIRECT_URL}/facebook",
            allow_insecure_http=False,
            use_state=False,
        ),
    })
    user_source_map.update({
        "github": const.UserSource.GITHUB.value,
        "facebook": const.UserSource.FACEBOOK.value,
    })


async def login_provider(provider_name: str) -> OAuthResponse:
    try:
        p = sso_map[provider_name]
    except KeyError:
        raise json_exception(
            request_id="",
            code=const.Code.OAUTH_PROVIDER_NOT_FOUND,
            language=const.Language.EN.value,
        )
    return OAuthResponse(
        uri=await p.get_login_url(),
    )


async def provider_callback(provider_name: str, req: Request) -> TokenResponse:
    try:
        p = sso_map[provider_name]
        user_source = user_source_map[provider_name]
    except KeyError:
        raise json_exception(
            request_id="",
            code=const.Code.OAUTH_PROVIDER_NOT_FOUND,
            language=const.Language.EN.value,
        )
    try:
        user = await p.verify_and_process(req)
    except SSOLoginError:
        raise json_exception(
            request_id="",
            code=const.Code.INVALID_AUTH,
        )
    if user is None:
        raise json_exception(
            request_id="",
            code=const.Code.INVALID_AUTH,
        )
    u, code = await core.user.get_account(account=user.id, source=user_source)
    if code == const.Code.OK:
        return TokenResponse(
            requestId="",
            token=utils.jwt_encode(
                exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
                data={"uid": u["id"], "language": u["settings"]["language"]},
            ),
        )

    # no user found, create one
    language = const.Language.EN.value
    u, code = await core.user.add(
        account=user.id,
        source=user_source,
        email=user.email if user.email else "",
        hashed="",
        nickname=user.display_name if user.display_name else "",
        avatar=user.picture if user.picture else "",
        language=language,
    )

    if code != const.Code.OK:
        raise json_exception(
            request_id="",
            code=code,
        )

    token = utils.jwt_encode(
        exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
        data={"uid": u["id"], "language": language},
    )
    code = await core.node.new_user_add_default_nodes(language=language, uid=u["id"])
    if code != const.Code.OK:
        raise json_exception(
            request_id="",
            code=code,
        )
    return TokenResponse(
        requestId="",
        token=token,
    )
