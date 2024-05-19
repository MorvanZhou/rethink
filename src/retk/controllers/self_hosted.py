from datetime import datetime

from bson import ObjectId
from bson.tz_util import utc

from retk import const, __version__
from retk.core import self_hosted, scheduler, user
from retk.core.notice import post_in_manager_delivery
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
        modified_at=datetime.now(tz=utc),
        used_space=0,
        type=const.USER_TYPE.MANAGER.id,
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

__new_version_title_zh = "发现新版本 ({})"
__new_version_content_temp_zh = """
更新您的本地版本 ({}) 到最新 ({}) 以获取最新功能和错误修复。

请在终端中运行此命令来升级：
    
```
pip install -U retk
```
"""

__new_version_title_en = "Find new version ({})"
__new_version_content_temp_en = """
Update your local version ({}) to the latest version ({}) to get the latest features and bug fixes.

Please run this command in your terminal to update:

```
pip install -U retk
```
"""


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
        u, code = await user.get_by_email(const.DEFAULT_USER["email"])
        if code != const.CodeEnum.OK:
            logger.error("get user failed")
            return
        language = u["settings"]["language"]

        local_version_str = ".".join(map(str, local))
        remote_version_str = ".".join(map(str, remote))

        title = (
            __new_version_title_zh if language == "zh" else __new_version_title_en
        ).format(local_version_str, remote_version_str)
        content = (
            __new_version_content_temp_zh if language == "zh" else __new_version_content_temp_en
        ).format(local_version_str, remote_version_str)
        for notice in res:
            if notice["title"] == __new_version_title_zh or notice["title"] == __new_version_title_en:
                return
        await post_in_manager_delivery(
            au=_local_system_authed_user,
            title=title,
            content=content,
            recipient_type=const.notice.RecipientTypeEnum.ALL.value,
            batch_type_ids=[],
            publish_at=datetime.now(tz=utc)
        )
        await scheduler.tasks.notice.async_deliver_unscheduled_system_notices()
