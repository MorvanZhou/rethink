import datetime
import ipaddress
import os
import re
import socket
import webbrowser
from typing import Tuple, Optional, List, Literal
from urllib.parse import urlparse

import httpx
from bson import ObjectId

from retk import config, const
from retk.logger import logger
from retk.models import tps


def datetime2str(dt: datetime.datetime) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


ASYNC_CLIENT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
              "application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


def is_internal_ip(ip):
    internal_ip_ranges = [
        ("127.0.0.0", "127.255.255.255"),
        ("10.0.0.0", "10.255.255.255"),
        ("9.0.0.0", "9.255.255.255"),
        ("100.64.0.0", "100.127.255.255"),
        ("192.168.0.0", "192.168.255.255"),
        ("172.16.0.0", "172.31.255.255"),
    ]

    for start, end in internal_ip_ranges:
        if ipaddress.IPv4Address(start) <= ip <= ipaddress.IPv4Address(end):
            return True
    return False


# SSRF protection
def ssrf_check(url: str) -> bool:
    if url.startswith("http://localhost") or url.startswith("http://127.0.0.1"):
        return True
    if '@' in url:
        return True
    host = urlparse(url).hostname
    if host is None:
        return True
    # cos url
    settings = config.get_settings()
    if host == f"{settings.COS_BUCKET_NAME}.cos.{settings.COS_REGION}.myqcloud.com" or host == settings.COS_DOMAIN:
        return True
    try:
        ip = ipaddress.IPv4Address(socket.gethostbyname(host))
    except socket.gaierror:
        return True
    if ip.is_private:
        return True
    if is_internal_ip(ip):
        return True
    return False


async def get_title_description_from_link(
        url: str,
        language: str,
        count=0
) -> Tuple[str, str]:
    if language == const.LanguageEnum.ZH.value:
        no_title = "网址没发现标题"
        no_description = "网址没发现描述"
    elif language == const.LanguageEnum.EN.value:
        no_title = "No title found"
        no_description = "No description found"
    else:
        no_title = "No title found"
        no_description = "No description found"

    if count > 2:
        logger.debug(f"too many 30X code, failed to get {url}")
        return no_title, no_description

    # SSRF protection
    if ssrf_check(url):
        return no_title, no_description
    # end of SSRF protection

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=url,
                headers=ASYNC_CLIENT_HEADERS,
                timeout=3.
            )
    except (
            httpx.ConnectTimeout,
            RuntimeError,
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.HTTPError
    ) as e:
        logger.debug(f"failed to get {url}: {e}")
        return no_title, no_description
    if response.status_code in (301, 302):
        return await get_title_description_from_link(
            url=response.headers["Location"],
            language=language,
            count=count + 1,
        )
    if response.status_code != 200:
        return no_title, no_description
    html = response.text

    title, description = "", ""
    found = re.search(r'<meta[^>]*name="title"[^>]*content="([^"]*)"[^>]*>', html, re.DOTALL)
    if found is None:
        found = re.search(r'<meta[^>]*content="([^"]*)"[^>]*name="title"[^>]*>', html, re.DOTALL)
    if found is None:
        found = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL)
    if found:
        title = found.group(1).strip()

    found = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"[^>]*>', html, re.DOTALL)
    if found is None:
        found = re.search(r'<meta[^>]*content="([^"]*)"[^>]*name="description"[^>]*>', html, re.DOTALL)
    if found:
        description = found.group(1).strip()[:400]
    if title == "":
        title = no_title
    if description == "":
        description = no_description
    return title, description


def mask_email(email: str):
    if email == "":
        return ""
    if "@" not in email:
        return email
    name, end = email.split("@", 1)
    if len(name) <= 1:
        e = f"{name[0]}**@{end}"
    elif len(name) == 2:
        e = f"{name[0]}**{name[1]}@{end}"
    else:
        e = f"{name[:2]}**{name[-1]}@{end}"
    return e


def local_finish_up():
    if config.is_local_db():
        addr = os.getenv('VUE_APP_API_URL')
        print(f"Rethink running on {addr} (Press CTRL+C to quit)")
        if os.getenv("RETHINK_SERVER_HEADLESS", "0") == "0" and addr:
            webbrowser.open_new_tab(addr)


def get_user_dict(
        _id: ObjectId,
        uid: str,
        source: int,
        account: str,
        nickname: str,
        email: str,
        avatar: str,
        hashed: str,
        disabled: bool,
        modified_at: datetime.datetime,
        used_space: int,
        type_: int,

        last_state_recent_cursor_search_selected_nids: List[str],
        last_state_recent_search: List[str],
        last_state_node_display_method: int,
        last_state_node_display_sort_key: str,

        settings_language: str,
        settings_theme: Literal["light", "dark"],
        settings_editor_mode: Literal["ir", "wysiwyg"],
        settings_editor_font_size: int,
        settings_editor_code_theme: tps.user.CODE_THEME_TYPES,
        settings_editor_sep_right_width: int,
        settings_editor_side_current_tool_id: str,
) -> tps.UserMeta:
    return tps.UserMeta(
        _id=_id,
        id=uid,
        source=source,
        account=account,
        nickname=nickname,
        email=email,
        avatar=avatar,
        hashed=hashed,
        disabled=disabled,
        modifiedAt=modified_at,
        usedSpace=used_space,
        type=type_,

        lastState=tps.user._LastState(
            recentCursorSearchSelectedNIds=last_state_recent_cursor_search_selected_nids,
            recentSearch=last_state_recent_search,
            nodeDisplayMethod=last_state_node_display_method,
            nodeDisplaySortKey=last_state_node_display_sort_key,
        ),
        settings=tps.user._Settings(
            language=settings_language,
            theme=settings_theme,
            editorMode=settings_editor_mode,
            editorFontSize=settings_editor_font_size,
            editorCodeTheme=settings_editor_code_theme,
            editorSepRightWidth=settings_editor_sep_right_width,
            editorSideCurrentToolId=settings_editor_side_current_tool_id,
        ),
    )


def get_node_dict(
        _id: ObjectId,
        nid: str,
        uid: str,
        md: str,
        title: str,
        snippet: str,
        type_: int,
        disabled: bool,
        in_trash: bool,
        modified_at: datetime.datetime,
        in_trash_at: Optional[datetime.datetime],
        from_node_ids: List[str],
        to_node_ids: List[str],
        history: List[str],
) -> tps.Node:
    return tps.Node(
        _id=_id,
        id=nid,
        uid=uid,
        md=md,
        title=title,
        snippet=snippet,
        type=type_,
        disabled=disabled,
        inTrash=in_trash,
        modifiedAt=modified_at,
        inTrashAt=in_trash_at,
        fromNodeIds=from_node_ids,
        toNodeIds=to_node_ids,
        history=history,
        favorite=False,
    )
