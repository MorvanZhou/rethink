import datetime
import io
import ipaddress
import math
import re
import socket
import uuid
from html.parser import HTMLParser
from io import StringIO
from typing import Tuple
from urllib.parse import urlparse

import httpx
import jwt
from markdown import Markdown

from rethink import config, const
from rethink.logger import logger

HEADERS = {
    'typ': 'jwt',
    'alg': 'RS256'
}
alphabet = "3467ACDEFGHJKLMNPQRTUVWXYabcdefghkmnoprtuvwxy"
alphabet_len = len(alphabet)
__padding = int(math.ceil(math.log(2 ** 128, alphabet_len)))
__code_pattern = re.compile(r"^```[^\S\r\n]*[a-z]*?\n(.*?)\n```$", re.MULTILINE | re.DOTALL)


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


def __unmark_element(element, stream=None):
    if stream is None:
        stream = io.StringIO()
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


def md2txt(md: str) -> str:
    for found in list(__code_pattern.finditer(md))[::-1]:
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


def split_title_body(fulltext: str) -> (str, str):
    title_body = fulltext.split("\n", maxsplit=1)
    title = title_body[0].strip()
    try:
        body = title_body[1].strip()
    except IndexError:
        body = ""
    return title, body


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
    return token


def jwt_decode(token: str) -> dict:
    return jwt.decode(
        token,
        key=config.get_settings().JWT_KEY_PUB,
        algorithms=[HEADERS["alg"]],
        options={"verify_exp": True}
    )


def change_link_title(md: str, nid: str, new_title: str) -> str:
    new_md = re.sub(
        r"\[@[^].]*?]\(/n/{}/?\)".format(nid),
        f"[@{new_title}](/n/{nid})",
        md,
    )
    return new_md


ONLY_HTTP_LINK_PTN = re.compile(r"^https?://\S*$")


def contain_only_http_link(md: str) -> str:
    content = md.strip()
    if ONLY_HTTP_LINK_PTN.match(content) is None:
        return ""
    return content


ASYNC_CLIENT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
              "application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
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
    try:
        ip = ipaddress.IPv4Address(socket.gethostbyname(host))
    except socket.gaierror:
        return True
    if ip.is_private:
        return True
    if is_internal_ip(ip):
        return True


async def get_title_description_from_link(url: str, language: str) -> Tuple[str, str]:
    if language == const.Language.ZH.value:
        no_title = "网址没发现标题"
        no_description = "网址没发现描述"
    elif language == const.Language.EN.value:
        no_title = "No title found"
        no_description = "No description found"
    else:
        no_title = "No title found"
        no_description = "No description found"

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
            logger.info(f"failed to get {url}: {e}")
            return no_title, no_description
        if response.status_code in (301, 302):
            url = response.headers["Location"]
            if ssrf_check(url):
                return no_title, no_description
            return await get_title_description_from_link(url=url, language=language)
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


class MLStripper(HTMLParser):
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


def strip_html_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


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
