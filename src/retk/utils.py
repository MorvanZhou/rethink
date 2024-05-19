import datetime
import ipaddress
import math
import os
import re
import socket
import uuid
import webbrowser
from html.parser import HTMLParser
from io import StringIO
from typing import Tuple, Optional, List, Dict, Any
from urllib.parse import urlparse

import httpx
import jwt
from bson import ObjectId
from markdown import Markdown

from retk import config, const, regex
from retk.logger import logger
from retk.models import tps

HEADERS = {
    'typ': 'jwt',
    'alg': 'RS256'
}
alphabet = "3467ACDEFGHJKLMNPQRTUVWXYabcdefghkmnoprtuvwxy"
alphabet_len = len(alphabet)
__padding = int(math.ceil(math.log(2 ** 128, alphabet_len)))


def short_uuid() -> str:
    """
    The output has the most significant digit first.
    """
    number = uuid.uuid4().int
    output = ""

    while number:
        number, digit = divmod(number, alphabet_len)
        output += alphabet[digit]
    if __padding:
        remainder = max(__padding - len(output), 0)
        output = output + alphabet[0] * remainder
    return output[::-1]


def jwt_encode(exp_delta: datetime.timedelta, data: dict) -> str:
    """
    Create token

    Args:
        exp_delta: expired delta
        data: payload data

    Returns:
        str: token
    """
    payload = {
        "exp": datetime.datetime.utcnow() + exp_delta
    }
    payload.update(data)
    token = jwt.encode(
        payload=payload,
        key=config.get_settings().JWT_KEY,
        algorithm=HEADERS["alg"],
        headers=HEADERS,
    )
    return f"Bearer {token}"


def jwt_decode(token: str) -> dict:
    t = token.split("Bearer ", maxsplit=1)
    if len(t) != 2:
        raise jwt.InvalidTokenError("Invalid token")
    return jwt.decode(
        t[1],
        key=config.get_settings().JWT_KEY_PUB,
        algorithms=[HEADERS["alg"]],
        options={"verify_exp": True}
    )


class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def strip_html_tags(html: str) -> str:
    s = HTMLStripper()
    s.feed(html[:1000])
    return s.get_data()


def split_title_body(fulltext: str) -> (str, str):
    title_body = fulltext.split("\n", maxsplit=1)
    title = title_body[0].strip()
    try:
        body = title_body[1].strip()
    except IndexError:
        body = ""
    return title, body


def __unmark_element(element, stream=None):
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        __unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


# patching Markdown
Markdown.output_formats["plain"] = __unmark_element
__md = Markdown(output_format="plain")
__md.stripTopLevelTags = False
__md_html = Markdown(
    output_format="html",
)


def md2txt(md: str) -> str:
    for found in list(regex.MD_CODE.finditer(md))[::-1]:
        span = found.span()
        code = found.group(1)
        md = f"{md[: span[0]]}{code}{md[span[1]:]}"
    return __md.convert(md)


def preprocess_md(md: str, snippet_len: int = 200) -> Tuple[str, str, str]:
    title, body = split_title_body(fulltext=md)
    title = md2txt(title.strip())
    body = md2txt(body.strip())
    snippet = strip_html_tags(body)[:snippet_len]
    return title, body, snippet


def md2html(md: str) -> str:
    _html = __md_html.convert(md)
    # prevent XSS and other security issues
    _html = re.sub(r"<script[^>]*>.*?</script>", "", _html, flags=re.DOTALL)
    return _html


def change_link_title(md: str, nid: str, new_title: str) -> str:
    new_md = re.sub(
        r"\[@[^].]*?]\(/n/{}/?\)".format(nid),
        f"[@{new_title}](/n/{nid})",
        md,
    )
    return new_md


def contain_only_http_link(md: str) -> str:
    content = md.strip()
    if regex.ONLY_HTTP_URL.match(content) is None:
        return ""
    return content


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
    if host == f"{settings.COS_BUCKET_NAME}.cos.{settings.COS_REGION}.myqcloud.com":
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


async def get_title_description_from_link(  # noqa: C901
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

    async with httpx.AsyncClient() as client:
        try:
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
        host = os.getenv('RETHINK_SERVER_HOSTNAME')
        port = os.getenv('VUE_APP_API_PORT')
        print(f"Rethink running on http://{host}:{port} (Press CTRL+C to quit)")
        if os.getenv("RETHINK_SERVER_HEADLESS", "0") == "0" and host and port:
            webbrowser.open_new_tab(
                f"http://{host}:{port}"
            )


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
        settings_theme: str,
        settings_editor_mode: str,
        settings_editor_font_size: int,
        settings_editor_code_theme: str,
        settings_editor_sep_right_width: int,
        settings_editor_side_current_tool_id: str,
) -> tps.UserMeta:
    return {
        "_id": _id,
        "id": uid,
        "source": source,
        "account": account,
        "nickname": nickname,
        "email": email,
        "avatar": avatar,
        "hashed": hashed,
        "disabled": disabled,
        "modifiedAt": modified_at,
        "usedSpace": used_space,
        "type": type_,

        "lastState": {
            "recentCursorSearchSelectedNIds": last_state_recent_cursor_search_selected_nids,
            "recentSearch": last_state_recent_search,
            "nodeDisplayMethod": last_state_node_display_method,
            "nodeDisplaySortKey": last_state_node_display_sort_key,
        },
        "settings": {
            "language": settings_language,
            "theme": settings_theme,
            "editorMode": settings_editor_mode,
            "editorFontSize": settings_editor_font_size,
            "editorCodeTheme": settings_editor_code_theme,
            "editorSepRightWidth": settings_editor_sep_right_width,
            "editorSideCurrentToolId": settings_editor_side_current_tool_id,
        },
    }


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
        history: List[Dict[str, Any]],
) -> tps.Node:
    return {
        "_id": _id,
        "id": nid,
        "uid": uid,
        "md": md,
        "title": title,
        "snippet": snippet,
        "type": type_,
        "disabled": disabled,
        "inTrash": in_trash,
        "modifiedAt": modified_at,
        "inTrashAt": in_trash_at,
        "fromNodeIds": from_node_ids,
        "toNodeIds": to_node_ids,
        "history": history,
    }


def get_token(uid: str, language: str) -> Tuple[str, str]:
    settings = config.get_settings()
    access_token = jwt_encode(
        exp_delta=settings.ACCESS_TOKEN_EXPIRE_DELTA,
        data={
            "is_access": True,
            "uid": uid,
            "language": language,
        },
    )
    refresh_token = jwt_encode(
        exp_delta=settings.REFRESH_TOKEN_EXPIRE_DELTA,
        data={
            "is_access": False,
            "uid": uid,
            "language": language,
        },
    )
    return access_token, refresh_token
