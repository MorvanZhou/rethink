import datetime
import traceback
from dataclasses import dataclass, field
from typing import Sequence
from urllib.parse import urlparse

import jwt
from fastapi import Header

from rethink import core, const
from rethink.logger import logger
from rethink.utils import jwt_decode


@dataclass
class Headers:
    code: const.Code
    uid: str = ""
    language: str = field(default=const.Language.EN.value)
    request_id: str = ""


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


def __one_line_traceback() -> str:
    return traceback.format_exc().replace("\n", "\\n")


async def process_headers(
        token: str = Header(alias="Authorization", default=""),
        request_id: str = Header(
            default="", alias="RequestId", max_length=const.REQUEST_ID_MAX_LENGTH
        )
) -> Headers:
    """if no requestId, default to empty string"""
    uid = ""
    err = ""
    language = const.Language.EN.value
    if token is None or token == "":
        return Headers(
            code=const.Code.INVALID_AUTH,
            language=language,
            request_id=request_id,
        )
    try:
        payload = jwt_decode(token=token)
        u, code = await core.user.get(uid=payload["uid"])
        if code != const.Code.OK:
            logger.error(f"core.user.get err: {const.CODE_MESSAGES[code].zh}")
            return Headers(
                code=code,
                language=language,
                request_id=request_id,
            )
        uid = u["id"]
        language = u["settings"]["language"]
    except jwt.exceptions.ExpiredSignatureError:
        code = const.Code.EXPIRED_AUTH
        err = "auth token expired"
    except jwt.exceptions.DecodeError:
        code = const.Code.INVALID_AUTH
        err = __one_line_traceback()
    except jwt.exceptions.InvalidTokenError:
        code = const.Code.INVALID_AUTH
        err = __one_line_traceback()
    except Exception:  # pylint: disable=broad-except
        code = const.Code.INVALID_AUTH
        err = __one_line_traceback()
    if code != const.Code.OK:
        logger.error(f"jwt_decode err: {err}")
    return Headers(
        code=code,
        uid=uid,
        language=language,
        request_id=request_id
    )
