import time
import traceback
from functools import wraps
from typing import Optional

import jwt
from fastapi import HTTPException, Header, Depends
from fastapi.params import Path
from starlette.status import HTTP_403_FORBIDDEN
from typing_extensions import Annotated

from retk import const, config, core
from retk.controllers.utils import json_exception
from retk.logger import logger
from retk.models.tps import AuthedUser, convert_user_dict_to_authed_user
from retk.utils import jwt_decode

REFERER_PREFIX = f"https://{const.DOMAIN}"


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


async def process_normal_headers(
        token: str = Header(alias="Authorization", default=""),
        request_id: str = Header(
            default="", alias="RequestId", max_length=const.REQUEST_ID_MAX_LENGTH
        )
) -> AuthedUser:
    """if no requestId, default to empty string"""
    au = AuthedUser(
        u=None,
        request_id=request_id,
        language=const.Language.EN.value,
    )
    err = ""
    if token is None or token == "":
        return au
    u = None
    try:
        payload = jwt_decode(token=token)
        u, code = await core.user.get(uid=payload["uid"])
        if code != const.Code.OK:
            err = f"get user failed, code={code}"
    except jwt.exceptions.ExpiredSignatureError:
        code = const.Code.EXPIRED_AUTH
        err = "auth expired"
    except jwt.exceptions.DecodeError:
        code = const.Code.INVALID_AUTH
        err = "token decode error"
    except jwt.exceptions.InvalidTokenError:
        code = const.Code.INVALID_AUTH
        err = "invalid token"
    except Exception:  # pylint: disable=broad-except
        code = const.Code.INVALID_AUTH
        err = traceback.format_exc()
    if code != const.Code.OK or u is None:
        raise json_exception(
            request_id=request_id,
            code=code,
            log_msg=err,
        )
    au.language = u["settings"]["language"]
    au.u = convert_user_dict_to_authed_user(u)
    return au


async def process_admin_headers(
        token: str = Header(alias="Authorization", default=""),
        request_id: str = Header(
            default="", alias="RequestId", max_length=const.REQUEST_ID_MAX_LENGTH
        )
) -> AuthedUser:
    au = await process_normal_headers(token=token, request_id=request_id)
    if au.u is None or au.u.type != const.USER_TYPE.ADMIN.id:
        raise json_exception(
            request_id=au.request_id,
            code=const.Code.NOT_PERMITTED,
        )
    return au


ANNOTATED_AUTHED_USER = Annotated[AuthedUser, Depends(process_normal_headers)]
ANNOTATED_AUTHED_ADMIN = Annotated[AuthedUser, Depends(process_admin_headers)]

ANNOTATED_UID = Annotated[str, Path(title="The ID of user", max_length=const.UID_MAX_LENGTH, min_length=8)]
ANNOTATED_NID = Annotated[str, Path(title="The ID of node", max_length=const.NID_MAX_LENGTH, min_length=8)]
ANNOTATED_PID = Annotated[str, Path(title="The ID of plugin", max_length=const.PLUGIN_ID_MAX_LENGTH)]
ANNOTATED_FID = Annotated[str, Path(title="The ID of file", max_length=const.FID_MAX_LENGTH)]

DEPENDS_REFERER = Depends(verify_referer)
