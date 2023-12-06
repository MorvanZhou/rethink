import datetime
from dataclasses import dataclass, field
from typing import Tuple

from rethink import const
from rethink.models.verify.verification import verify_captcha


@dataclass
class TokenDecode:
    code: const.Code
    uid: str = ""
    language: str = field(default=const.Language.EN.value)


def datetime2str(dt: datetime.datetime) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def match_captcha(token: str, code_str: str, language: str) -> Tuple[const.Code, str]:
    code = verify_captcha(token=token, code_str=code_str)
    _msg = const.CODE_MESSAGES[code]
    if language == const.Language.ZH.value:
        msg = _msg.zh
    elif language == const.Language.EN.value:
        msg = _msg.en
    else:
        msg = _msg.en
    return code, msg
