import time
import traceback
from functools import wraps
from typing import Optional

import jwt
from fastapi import HTTPException, Header, Cookie, Depends
from fastapi.params import Path
from starlette.status import HTTP_403_FORBIDDEN
from typing_extensions import Annotated

from retk import const, config, core
from retk.controllers.utils import json_exception
from retk.logger import logger
from retk.models.tps import AuthedUser, convert_user_dict_to_authed_user
from retk.utils import jwt_decode

REFERER_PREFIX = f"https://{const.settings.DOMAIN}"


def measure_time_spend(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        uid = ""
        try:
            au: AuthedUser = kwargs["au"]
        except KeyError:
            req_id = ""
        else:
            req_id = au.request_id
            if au.u is not None:
                uid = au.u.id

        req_s = str(kwargs.get("req", ""))

        req_s = req_s[:200] + "..." if len(req_s) > 200 else req_s
        if func.__name__ not in ["login", "forget_password", "signup"]:
            logger.debug(f"REQ: reqId='{req_id}' | uid='{uid}' | api='{func.__name__}' | {req_s}")

        resp = await func(*args, **kwargs)
        t1 = time.perf_counter()
        try:
            req_id = resp.requestId
        except AttributeError:
            req_id = ""
        logger.debug(f"RESP: reqId='{req_id}' | uid='{uid}' | api='{func.__name__}' | spend={t1 - t0:.4f}s")
        return resp

    return wrapper


def verify_referer(referer: Optional[str] = Header(None)):
    if config.get_settings().VERIFY_REFERER and not referer.startswith(REFERER_PREFIX):
        logger.error(f"referer={referer} not startswith {REFERER_PREFIX}")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid referer",
        )
    return referer


async def __process_auth_headers(  # noqa: C901
        is_refresh_token: bool,
        refresh_token_id: str,
        token: str = Header(alias="Authorization", default=""),
        request_id: str = Header(
            default="", alias="RequestId", max_length=const.settings.MD_MAX_LENGTH
        )
) -> AuthedUser:
    if token is None or token == "":
        raise json_exception(
            request_id=request_id,
            code=const.CodeEnum.INVALID_AUTH if is_refresh_token else const.CodeEnum.EXPIRED_OR_NO_ACCESS_TOKEN,
            log_msg="empty token",
        )
    au = AuthedUser(
        u=None,
        request_id=request_id,
        language=const.LanguageEnum.EN.value,
    )
    err = ""
    u = None
    try:
        payload = jwt_decode(token=token)
        is_access = payload.get("is_access")
        if is_access is None:
            code = const.CodeEnum.INVALID_AUTH
            err = "invalid token"
        elif is_access == is_refresh_token:
            code = const.CodeEnum.INVALID_AUTH
            err = "invalid token"
        elif is_refresh_token and payload["uid"] != refresh_token_id:
            code = const.CodeEnum.INVALID_AUTH
            err = "invalid token"
        else:
            u, code = await core.user.get(uid=payload["uid"], disabled=False)
            if code != const.CodeEnum.OK:
                err = f"get user failed, code={code}"

    except jwt.exceptions.ExpiredSignatureError:
        code = const.CodeEnum.EXPIRED_AUTH if is_refresh_token else const.CodeEnum.EXPIRED_OR_NO_ACCESS_TOKEN
        err = "auth expired"
    except jwt.exceptions.DecodeError:
        code = const.CodeEnum.INVALID_AUTH
        err = "token decode error"
    except jwt.exceptions.InvalidTokenError:
        code = const.CodeEnum.INVALID_AUTH
        err = "invalid token"
    except Exception:  # pylint: disable=broad-except
        code = const.CodeEnum.INVALID_AUTH
        err = traceback.format_exc()
    if code != const.CodeEnum.OK or u is None:
        raise json_exception(
            request_id=request_id,
            code=code,
            log_msg=err,
        )
    au.language = u["settings"]["language"]
    au.u = convert_user_dict_to_authed_user(u)
    return au


async def process_normal_headers(
        token: str = Cookie(alias=const.settings.COOKIE_ACCESS_TOKEN, default=""),
        request_id: str = Header(
            default="", alias="RequestId", max_length=const.settings.MD_MAX_LENGTH
        )
) -> AuthedUser:
    return await __process_auth_headers(
        is_refresh_token=False,
        refresh_token_id="",
        token=token,
        request_id=request_id
    )


async def process_refresh_token_headers(
        token: str = Cookie(alias=const.settings.COOKIE_REFRESH_TOKEN, default=""),
        id_: str = Cookie(alias=const.settings.COOKIE_REFRESH_TOKEN_ID, default=""),
        request_id: str = Header(
            default="", alias="RequestId", max_length=const.settings.MD_MAX_LENGTH
        )
) -> AuthedUser:
    return await __process_auth_headers(
        is_refresh_token=True,
        refresh_token_id=id_,
        token=token,
        request_id=request_id
    )


async def process_no_auth_headers(
        request_id: str = Header(
            default="", alias="RequestId", max_length=const.settings.MD_MAX_LENGTH
        )
) -> str:
    return request_id


async def process_admin_headers(
        token: str = Cookie(alias=const.settings.COOKIE_ACCESS_TOKEN, default=""),
        request_id: str = Header(
            default="", alias="RequestId", max_length=const.settings.MD_MAX_LENGTH
        )
) -> AuthedUser:
    au = await process_normal_headers(token=token, request_id=request_id)
    if au.u is None or au.u.type != const.USER_TYPE.ADMIN.id:
        raise json_exception(
            request_id=au.request_id,
            code=const.CodeEnum.NOT_PERMITTED,
        )
    return au


ANNOTATED_REQUEST_ID = Annotated[str, Depends(process_no_auth_headers)]
ANNOTATED_AUTHED_USER = Annotated[AuthedUser, Depends(process_normal_headers)]
ANNOTATED_AUTHED_ADMIN = Annotated[AuthedUser, Depends(process_admin_headers)]
ANNOTATED_REFRESH_TOKEN = Annotated[AuthedUser, Depends(process_refresh_token_headers)]

ANNOTATED_UID = Annotated[str, Path(title="The ID of user", max_length=const.settings.UID_MAX_LENGTH, min_length=8)]
ANNOTATED_NID = Annotated[str, Path(title="The ID of node", max_length=const.settings.NID_MAX_LENGTH, min_length=8)]
ANNOTATED_PID = Annotated[str, Path(title="The ID of plugin", max_length=const.settings.PLUGIN_ID_MAX_LENGTH)]
ANNOTATED_FID = Annotated[str, Path(title="The ID of file", max_length=const.settings.FID_MAX_LENGTH)]

DEPENDS_REFERER = Depends(verify_referer)
