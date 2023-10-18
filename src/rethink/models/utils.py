import datetime
import math
import re
import uuid
from io import StringIO

import jwt
import pypinyin
from markdown import Markdown

from rethink import config

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


def md2txt(text):
    for found in list(__code_pattern.finditer(text))[::-1]:
        span = found.span()
        code = found.group(1)
        text = f"{text[: span[0]]}{code}{text[span[1]:]}"
    return __md.convert(text)


def text2search_keys(text: str) -> str:
    s1 = "".join(pypinyin.lazy_pinyin(text))
    s2 = "".join(pypinyin.lazy_pinyin(text, style=pypinyin.Style.BOPOMOFO))
    s = {s1, s2, text}
    return " ".join(s).lower()


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
