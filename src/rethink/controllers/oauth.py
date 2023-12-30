from typing import Optional

from fastapi import Request

from rethink import config, const, models
from rethink.sso.base import SSOLoginError
from rethink.sso.facebook import FacebookSSO
from rethink.sso.github import GithubSSO
from rethink.sso.qq import QQSSO
from .schemas.base import TokenResponse
from .schemas.oauth import OAuthResponse

GITHUB_SSO: Optional[GithubSSO] = None
QQ_SSO: Optional[QQSSO] = None
FACEBOOK_SSO: Optional[FacebookSSO] = None


async def login_github() -> OAuthResponse:
    global GITHUB_SSO
    if GITHUB_SSO is None:
        GITHUB_SSO = GithubSSO(
            client_id=config.get_settings().OAUTH_CLIENT_ID_GITHUB,
            client_secret=config.get_settings().OAUTH_CLIENT_SEC_GITHUB,
            redirect_uri=f"{config.get_settings().OAUTH_REDIRECT_URL}/github",
            allow_insecure_http=False,
            use_state=False,
            scope=None,
        )
    uri = await GITHUB_SSO.get_login_url()
    return OAuthResponse(
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, const.Language.EN.value),
        uri=uri,
    )


async def callback_github(req: Request) -> TokenResponse:
    try:
        user = await GITHUB_SSO.verify_and_process(req)
    except SSOLoginError:
        code = const.Code.INVALID_AUTH
        return TokenResponse(
            requestId="",
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            token="",
        )
    if user is None:
        code = const.Code.INVALID_AUTH
        return TokenResponse(
            requestId="",
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            token="",
        )
    u, code = await models.user.get_account(account=user.id, source=const.UserSource.GITHUB.value)
    if code == const.Code.OK:
        return TokenResponse(
            requestId="",
            code=const.Code.OK.value,
            message=const.get_msg_by_code(const.Code.OK, const.Language.EN.value),
            token=models.utils.jwt_encode(
                exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
                data={"uid": u["id"], "language": u["language"]},
            ),
        )

    # no user found, create one
    language = const.Language.EN.value
    uid, code = await models.user.add(
        account=user.id,
        source=const.UserSource.GITHUB.value,
        email=user.email if user.email else "",
        hashed="",
        nickname=user.display_name if user.display_name else "",
        avatar=user.picture if user.picture else "",
        language=language,
    )
    if code != const.Code.OK:
        return TokenResponse(
            requestId="",
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            token="",
        )
    token = models.utils.jwt_encode(
        exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
        data={"uid": uid, "language": language},
    )
    code = await models.node.new_user_add_default_nodes(language=language, uid=uid)

    return TokenResponse(
        requestId="",
        code=code.value,
        message=const.get_msg_by_code(const.Code.OK, language=language),
        token=token,
    )


async def login_facebook() -> OAuthResponse:
    global FACEBOOK_SSO
    if FACEBOOK_SSO is None:
        FACEBOOK_SSO = FacebookSSO(
            client_id=config.get_settings().OAUTH_CLIENT_ID_FACEBOOK,
            client_secret=config.get_settings().OAUTH_CLIENT_SEC_FACEBOOK,
            redirect_uri=f"{config.get_settings().OAUTH_REDIRECT_URL}/facebook",
            allow_insecure_http=False,
            use_state=False,
            scope=None,
        )
    uri = await FACEBOOK_SSO.get_login_url()
    return OAuthResponse(
        code=const.Code.OK.value,
        message=const.get_msg_by_code(const.Code.OK, const.Language.EN.value),
        uri=uri,
    )


async def callback_facebook(req: Request) -> TokenResponse:
    try:
        user = await FACEBOOK_SSO.verify_and_process(req)
    except SSOLoginError:
        code = const.Code.INVALID_AUTH
        return TokenResponse(
            requestId="",
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            token="",
        )
    if user is None:
        code = const.Code.INVALID_AUTH
        return TokenResponse(
            requestId="",
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            token="",
        )
    u, code = await models.user.get_account(account=user.id, source=const.UserSource.GITHUB.value)
    if code == const.Code.OK:
        return TokenResponse(
            requestId="",
            code=const.Code.OK.value,
            message=const.get_msg_by_code(const.Code.OK, const.Language.EN.value),
            token=models.utils.jwt_encode(
                exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
                data={"uid": u["id"], "language": u["language"]},
            ),
        )

    # no user found, create one
    language = const.Language.EN.value
    uid, code = await models.user.add(
        account=user.id,
        source=const.UserSource.FACEBOOK.value,
        email=user.email,
        hashed="",
        nickname=user.display_name,
        avatar=user.picture,
        language=language,
    )
    if code != const.Code.OK:
        return TokenResponse(
            requestId="",
            code=code.value,
            message=const.get_msg_by_code(code, const.Language.EN.value),
            token="",
        )
    token = models.utils.jwt_encode(
        exp_delta=config.get_settings().JWT_EXPIRED_DELTA,
        data={"uid": uid, "language": language},
    )
    code = await models.node.new_user_add_default_nodes(language=language, uid=uid)
    return TokenResponse(
        requestId="",
        code=code.value,
        message=const.get_msg_by_code(const.Code.OK, language=language),
        token=token,
    )

# async def login_qq() -> OAuthResponse:
#     global QQ_SSO
#     if QQ_SSO is None:
#         QQ_SSO = QQSSO(
#             client_id=config.get_settings().OAUTH_CLIENT_ID_QQ,
#             client_secret=config.get_settings().OAUTH_CLIENT_SEC_QQ,
#             redirect_uri=f"{config.get_settings().OAUTH_REDIRECT_URL}/qq",
#             allow_insecure_http=False,
#             use_state=False,
#             scope=None,
#         )
#     uri = await QQ_SSO.get_login_url()
#     return OAuthResponse(
#         code=const.Code.OK.value,
#         message=const.get_msg_by_code(const.Code.OK, const.Language.EN.value),
#         uri=uri,
#     )
#
#
# async def callback_qq(req: Request) -> LoginResponse:
#     try:
#         user = await QQ_SSO.verify_and_process(req)
#     except SSOLoginError:
#         code = const.Code.INVALID_AUTH
#         return LoginResponse(
#             requestId="",
#             code=code.value,
#             message=const.get_msg_by_code(code, const.Language.EN.value),
#             token="",
#         )
#     if user is None:
#         code = const.Code.INVALID_AUTH
#         return LoginResponse(
#             requestId="",
#             code=code.value,
#             message=const.get_msg_by_code(code, const.Language.EN.value),
#             token="",
#         )
#     u, code = await models.user.get_account(account=user.id, source=const.UserSource.GITHUB.value)
#     if code == const.Code.OK:
#         return LoginResponse(
#             requestId="",
#             code=const.Code.OK.value,
#             message=const.get_msg_by_code(const.Code.OK, const.Language.EN.value),
#             token=controllers.auth.jwt_encode(
#                 uid=u["id"],
#                 language=u["language"],
#             ),
#         )
#
#     # no user found, create one
#     language = const.Language.EN.value
#     uid, code = await models.user.add(
#         account=user.id,
#         source=const.UserSource.GITHUB.value,
#         email=user.email,
#         hashed="",
#         nickname=user.display_name,
#         avatar=user.picture,
#         language=language,
#     )
#     if code != const.Code.OK:
#         return LoginResponse(
#             requestId="",
#             code=code.value,
#             message=const.get_msg_by_code(code, const.Language.EN.value),
#             token="",
#         )
#     token = controllers.auth.jwt_encode(
#         uid=uid,
#         language=language,
#     )
#     new_user_node = const.NEW_USER_FIRST_NODE[language]
#     _, code = await models.node.add(
#         uid=uid,
#         title=new_user_node["title"],
#         text=new_user_node["text"],
#     )
#     return LoginResponse(
#         requestId="",
#         code=code.value,
#         message=const.get_msg_by_code(const.Code.OK, language=language),
#         token=token,
#     )
