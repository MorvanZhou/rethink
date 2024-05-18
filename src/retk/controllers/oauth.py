from typing import Dict

from fastapi import Request
from fastapi.responses import JSONResponse

from retk import config, const, core, utils
from retk.controllers.account import set_cookie_response
from retk.controllers.utils import json_exception
from retk.depend.sso.base import SSOLoginError, SSOBase
from retk.depend.sso.facebook import FacebookSSO
from retk.depend.sso.github import GithubSSO
# from retk.depend.sso.qq import QQSSO
from .schemas.oauth import OAuthResponse

sso_map: Dict[str, SSOBase] = {}
user_source_map: Dict[str, int] = {}


def init_oauth_provider_map():
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
        "github": const.UserSourceEnum.GITHUB.value,
        "facebook": const.UserSourceEnum.FACEBOOK.value,
    })


async def login_provider(provider_name: str) -> OAuthResponse:
    try:
        p = sso_map[provider_name]
    except KeyError:
        raise json_exception(
            request_id="",
            code=const.CodeEnum.OAUTH_PROVIDER_NOT_FOUND,
            language=const.LanguageEnum.EN.value,
        )
    return OAuthResponse(
        uri=await p.get_login_url(),
    )


async def provider_callback(provider_name: str, req: Request) -> JSONResponse:
    try:
        p = sso_map[provider_name]
        user_source = user_source_map[provider_name]
    except KeyError:
        raise json_exception(
            request_id="",
            code=const.CodeEnum.OAUTH_PROVIDER_NOT_FOUND,
            language=const.LanguageEnum.EN.value,
        )
    try:
        user = await p.verify_and_process(req)
    except SSOLoginError:
        raise json_exception(
            request_id="",
            code=const.CodeEnum.INVALID_AUTH,
        )
    if user is None:
        raise json_exception(
            request_id="",
            code=const.CodeEnum.INVALID_AUTH,
        )
    u, code = await core.user.get_account(account=user.id, source=user_source)
    if code == const.CodeEnum.OK:
        access_token, refresh_token = utils.get_token(
            uid=u["id"],
            language=u["settings"]["language"],
        )

        return set_cookie_response(
            uid=u["id"],
            req_id="",
            status_code=200,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    # no user found, create one
    language = const.LanguageEnum.EN.value
    u, code = await core.user.add(
        account=user.id,
        source=user_source,
        email=user.email if user.email else "",
        hashed="",
        nickname=user.display_name if user.display_name else "",
        avatar=user.picture if user.picture else "",
        language=language,
    )

    if code != const.CodeEnum.OK:
        raise json_exception(
            request_id="",
            code=code,
        )

    code = await core.node.new_user_add_default_nodes(language=language, uid=u["id"])
    if code != const.CodeEnum.OK:
        raise json_exception(
            request_id="",
            code=code,
        )

    access_token, refresh_token = utils.get_token(
        uid=u["id"],
        language=language,
    )
    return set_cookie_response(
        uid=u["id"],
        req_id="",
        status_code=201,
        access_token=access_token,
        refresh_token=refresh_token,
    )
