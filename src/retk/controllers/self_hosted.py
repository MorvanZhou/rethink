from datetime import datetime

from bson import ObjectId

from retk import const, __version__
from retk.core import self_hosted
from retk.core.notice import put_system_notice
from retk.logger import logger
from retk.models.client import client
from retk.models.tps import AuthedUser

_local_system_authed_user = AuthedUser(
    u=AuthedUser.User(
        _id=ObjectId(),
        id="system",
        source=0,
        account="system",
        nickname="system",
        email="system@rethink.com",
        avatar="",
        hashed="",
        disabled=False,
        modified_at=datetime.now(),
        used_space=0,
        type=const.USER_TYPE.MANAGER,
        last_state=AuthedUser.User.LastState(
            node_display_method=0,
            node_display_sort_key="",
            recent_search=[],
            recent_cursor_search_selected_nids=[]
        ),
        settings=AuthedUser.User.Settings(
            language="en",
            theme="light",
            editor_mode="markdown",
            editor_font_size=14,
            editor_code_theme="default",
            editor_sep_right_width=300,
            editor_side_current_tool_id=""
        )
    ),
    language="en",
    request_id=""
)


async def notice_new_pkg_version():
    remote, code = await self_hosted.get_latest_pkg_version()
    if code != const.CodeEnum.OK:
        logger.error("get latest version failed")
        return
    local = self_hosted.parse_version(__version__)
    if local is None:
        logger.error("parse version failed")
        return

    has_new_version = False
    for vr, vl in zip(remote, local):
        if vr > vl:
            has_new_version = True
            break
    if has_new_version:
        res = await client.coll.notice_manager_delivery.find({
            "senderId": "system",
        }).to_list(None)
        if len(res) == 0:
            await put_system_notice(
                au=_local_system_authed_user,
                title="New version available",
                content="New version available, please update your client",
                recipient_type=const.notice.RecipientTypeEnum.ALL,
                batch_type_ids=[],
                publish_at=datetime.now()
            )
