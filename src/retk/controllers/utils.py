import datetime
import inspect
import traceback
from typing import Sequence
from urllib.parse import urlparse

import jwt
from fastapi import Header, HTTPException

from retk import core, const
from retk.logger import logger
from retk.models.tps import AuthedUser, convert_user_dict_to_authed_user
from retk.utils import jwt_decode


def datetime2str(dt: datetime.datetime) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def is_allowed_mime_type(data_url, allowed_mime_types: Sequence[str]):
    try:
        result = urlparse(data_url)
        if result.scheme != 'data':
            return False

        media_type = result.path.split(';')[0]
        return media_type in allowed_mime_types
    except Exception:  # pylint: disable=broad-except
        return False


async def process_headers(
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
    try:
        payload = jwt_decode(token=token)
        u, code = await core.user.get(uid=payload["uid"])
        if code != const.Code.OK:
            logger.error(f"core.user.get err: {const.CODE_MESSAGES[code].zh}")
            raise json_exception(
                request_id=request_id,
                code=code,
            )
        au.language = u["settings"]["language"]
        au.u = convert_user_dict_to_authed_user(u)
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
    if code != const.Code.OK:
        raise json_exception(
            request_id=request_id,
            code=code,
            log_msg=err,
        )
    return au


def json_exception(
        request_id: str,
        code: const.Code,
        language: str = const.Language.EN.value,
        log_msg: str = None
) -> HTTPException:
    def get_parent_function_info() -> str:
        previous_frame = inspect.currentframe().f_back.f_back.f_code
        caller = previous_frame.co_name
        previous_frame_file = previous_frame.co_filename
        previous_frame_line = previous_frame.co_firstlineno
        return f"caller='{caller}' in {previous_frame_file}:{previous_frame_line}"

    if log_msg is not None:
        # get parent function name
        one_line_log = log_msg.replace("\n", "\\n")
        logger.error(f"reqId='{request_id}' | {get_parent_function_info()} | err='{one_line_log}'")

    status_code = const.CODE2STATUS_CODE[code]
    if status_code == 500:
        one_line_log = const.get_msg_by_code(code, language).replace("\n", "\\n")
        logger.error(f"reqId='{request_id}' | {get_parent_function_info()} | err='{one_line_log}'")

    return HTTPException(
        status_code=status_code,
        detail={
            "code": code.value,
            "msg": const.get_msg_by_code(code, language),
            "requestId": request_id,
        }
    )


def maybe_raise_json_exception(
        au: AuthedUser,
        code: const.Code,
):
    if code != const.Code.OK:
        raise json_exception(
            request_id=au.request_id,
            code=code,
            language=au.language,
        )
