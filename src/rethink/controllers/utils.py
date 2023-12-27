import datetime
from dataclasses import dataclass, field
from typing import Sequence
from urllib.parse import urlparse

from rethink import const


@dataclass
class TokenDecode:
    code: const.Code
    uid: str = ""
    language: str = field(default=const.Language.EN.value)


def datetime2str(dt: datetime.datetime) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def is_allowed_mime_type(data_url, allowed_mime_types: Sequence[str]):
    try:
        result = urlparse(data_url)
        if result.scheme != 'data':
            return False

        media_type = result.path.split(';')[0]
        return media_type in allowed_mime_types
    except Exception:  # pylint: disable=broad-except
        return False
