import inspect
from typing import Sequence
from urllib.parse import urlparse

from fastapi import HTTPException

from retk import const
from retk.logger import logger
from retk.models.tps import AuthedUser


def is_allowed_mime_type(data_url, allowed_mime_types: Sequence[str]):
    try:
        result = urlparse(data_url)
        if result.scheme != 'data':
            return False

        media_type = result.path.split(';')[0]
        return media_type in allowed_mime_types
    except Exception:  # pylint: disable=broad-except
        return False


def json_exception(
        request_id: str,
        code: const.CodeEnum,
        language: str = const.LanguageEnum.EN.value,
        log_msg: str = None
) -> HTTPException:
    def get_parent_function_info() -> str:
        previous_frame = inspect.currentframe().f_back.f_back
        if previous_frame.f_code.co_name == maybe_raise_json_exception.__name__:
            previous_frame = previous_frame.f_back
        previous_f_code = previous_frame.f_code
        caller = previous_f_code.co_name
        previous_frame_file = previous_f_code.co_filename
        previous_frame_line = previous_f_code.co_firstlineno
        return f"caller='{caller}' in {previous_frame_file}:{previous_frame_line}"

    if log_msg is not None:
        # get parent function name
        one_line_log = log_msg.replace("\n", "\\n")
        if code == const.CodeEnum.EXPIRED_AUTH:
            ll = logger.info
        else:
            ll = logger.error
        ll(f"reqId='{request_id}' | {get_parent_function_info()} | err='{one_line_log}'")

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
        code: const.CodeEnum,
):
    if code != const.CodeEnum.OK:
        raise json_exception(
            request_id=au.request_id,
            code=code,
            language=au.language,
        )
