import datetime
from dataclasses import dataclass, field

from rethink import const


@dataclass
class TokenDecode:
    code: const.Code
    uid: str = ""
    language: str = field(default=const.Language.EN.value)


def datetime2str(dt: datetime.datetime) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
