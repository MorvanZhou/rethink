import inspect
import os
from typing import Sequence
from urllib.parse import urlparse

from fastapi import HTTPException

from retk import const, config
from retk.controllers.schemas.user import UserInfoResponse
from retk.core.user import get_user_nodes_count
from retk.logger import logger
from retk.models.tps import AuthedUser, UserMeta
from retk.utils import datetime2str


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
        uid: str,
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
        rel_path = os.path.relpath(previous_frame_file, const.settings.RETHINK_DIR)
        previous_frame_line = previous_f_code.co_firstlineno
        return f"caller='{caller}' in {rel_path}:{previous_frame_line}"

    if log_msg is not None:
        # get parent function name
        one_line_log = log_msg.replace("\n", "\\n")
        if code == const.CodeEnum.EXPIRED_AUTH:
            ll = logger.info
        else:
            ll = logger.error
        ll(
            f"rid='{request_id}' "
            f"| uid='{uid}' "
            f"| {get_parent_function_info()} "
            f"| err='{one_line_log}'"
        )

    status_code = const.CODE2STATUS_CODE[code]
    if status_code == 500:
        one_line_log = const.get_msg_by_code(code, language).replace("\n", "\\n")
        logger.error(
            f"rid='{request_id}' "
            f"| uid='{uid}' "
            f"| {get_parent_function_info()} "
            f"| err='{one_line_log}'"
        )

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
            uid=au.u.id,
            code=code,
            language=au.language,
        )


async def get_user_info_response_from_u_dict(
        u: UserMeta,
        request_id: str,
) -> UserInfoResponse:
    if config.is_local_db():
        max_space = 0
    else:
        max_space = const.USER_TYPE.id2config(u["type"]).max_store_space
    last_state = u["lastState"]
    u_settings = u["settings"]
    return UserInfoResponse(
        requestId=request_id,
        user=UserInfoResponse.User(
            email=u["email"],
            nickname=u["nickname"],
            avatar=u["avatar"],
            source=u["source"],
            createdAt=datetime2str(u["_id"].generation_time),
            usedSpace=u["usedSpace"],
            maxSpace=max_space,
            lastState=UserInfoResponse.User.LastState(
                nodeDisplayMethod=last_state["nodeDisplayMethod"],
                nodeDisplaySortKey=last_state["nodeDisplaySortKey"],
            ),
            settings=UserInfoResponse.User.Settings(
                language=u_settings["language"],
                theme=u_settings["theme"],
                editorMode=u_settings["editorMode"],
                editorFontSize=u_settings["editorFontSize"],
                editorCodeTheme=u_settings["editorCodeTheme"],
                editorSepRightWidth=u_settings.get("editorSepRightWidth", 200),
                editorSideCurrentToolId=u_settings.get("editorSideCurrentToolId", ""),
            ),
            totalNodes=await get_user_nodes_count(uid=u["id"], disabled=False, in_trash=False),
        ),
    )
