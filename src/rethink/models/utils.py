import datetime
import io
import math
import re
import uuid
from html.parser import HTMLParser
from io import StringIO
from typing import Tuple

import httpx
import jwt
from markdown import Markdown

from rethink import config, const
from rethink.logger import logger

HEADERS = {
    'typ': 'jwt',
    'alg': 'RS256'
}
alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
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
        if response.status_code in [302, 301]:
            url = response.headers["Location"]
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
