from datetime import datetime
from typing import Tuple, Optional

import httpx
from bson import ObjectId
from bson.tz_util import utc

from retk import const
from retk._version import __version__
from retk.core import scheduler
from retk.core import user
from retk.core.notice import post_in_manager_delivery
from retk.logger import logger
from retk.models.client import client
from retk.models.tps import AuthedUser
from retk.utils import ASYNC_CLIENT_HEADERS, md2html

__new_version_title_zh = "发现新版本 ({})"
__new_version_content_temp_zh = """
更新您的本地版本 ({}) 到最新 ({}) 以获取最新功能和错误修复。

## 自动更新

请点击右上角的用户头像，并找到更新按钮，点击即可自动更新。

## 手动更新

您也可以手动在终端中运行此命令来升级：

```
pip install -U retk
```

等更新完毕后，再重启您的服务。
"""

__new_version_title_en = "Find new version ({})"
__new_version_content_temp_en = """
Update your local version ({}) to the latest version ({}) to get the latest features and bug fixes.

## Auto Update

Please click the user icon in the upper right corner and find the update button, click to update automatically.

## Manual Update

You can also manually run this command in the terminal to upgrade:

```
pip install -U retk
```

After the update is complete, restart your service.
"""

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


def parse_version(version: str) -> Optional[Tuple[int, int, int]]:
    vs = version.split(".")
    if len(vs) != 3:
        return None
    try:
        vs = (int(vs[0]), int(vs[1]), int(vs[2]))
    except ValueError:
        return None
    return vs


async def get_latest_pkg_version() -> Tuple[Tuple[int, int, int], const.CodeEnum]:
    url = 'https://pypi.org/pypi/retk/json'
    default_version = (0, 0, 0)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=url,
                headers=ASYNC_CLIENT_HEADERS,
                follow_redirects=False,
                timeout=2.
            )
    except (
            httpx.ConnectTimeout,
            RuntimeError,
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.HTTPError
    ) as e:
        logger.debug(f"failed to get {url}: {e}")
        return default_version, const.CodeEnum.OPERATION_FAILED

    if response.status_code != 200:
        logger.debug(f"failed to get {url}: {response.status_code}, {response.text}")
        return default_version, const.CodeEnum.OPERATION_FAILED

    package_info = response.json()

    try:
        v = package_info['info']['version']
    except KeyError:
        logger.debug(f"failed to get {url}: {response.text}")
        return default_version, const.CodeEnum.OPERATION_FAILED
    vs = parse_version(v)
    if vs is None:
        logger.debug(f"failed to get {url}: {v}")
        return default_version, const.CodeEnum.OPERATION_FAILED
    return vs, const.CodeEnum.OK


async def has_new_version() -> Tuple[bool, Tuple[int, int, int], Tuple[int, int, int]]:
    has = False
    remote, code = await get_latest_pkg_version()
    if code != const.CodeEnum.OK:
        logger.error("get latest version failed")
        return has, (0, 0, 0), (0, 0, 0)
    local = parse_version(__version__)
    if local is None:
        logger.error("parse version failed")
        return has, (0, 0, 0), (0, 0, 0)

    for vr, vl in zip(remote, local):
        if vr > vl:
            has = True
            break
    return has, remote, local


async def notice_new_pkg_version():
    has, remote, local = await has_new_version()
    if has:
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
        ).format(remote_version_str)
        content = (
            __new_version_content_temp_zh if language == "zh" else __new_version_content_temp_en
        ).format(local_version_str, remote_version_str)
        for notice in res:
            if notice["title"] == title and notice["html"] == md2html(content, with_css=True):
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
