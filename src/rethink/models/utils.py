import datetime
import io
import math
import re
import uuid
from typing import Tuple

import httpx
import jwt
import pypinyin
from markdown import Markdown

from rethink import config
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


def preprocess_md(md: str) -> Tuple[str, str]:
    title, body = split_title_body(fulltext=md)
    title = md2txt(title.strip())
    body = body.strip()
    snippet = md2txt(md=body)[:200]
    return title, snippet


def txt2search_keys(txt: str) -> str:
    s1 = "".join(pypinyin.lazy_pinyin(txt))
    s2 = "".join(pypinyin.lazy_pinyin(txt, style=pypinyin.Style.BOPOMOFO))
    s = {s1, s2, txt}
    return " ".join(s).lower()


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
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
}


async def get_title_description_from_link(url: str) -> Tuple[str, str]:
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
            return "", ""
        if response.status_code in [302, 301]:
            url = response.headers["Location"]
            return await get_title_description_from_link(url)
        if response.status_code != 200:
            return "", ""
        html = response.text[:10000]

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
    return title, description
