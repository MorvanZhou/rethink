from collections import OrderedDict
from datetime import timedelta, datetime
from typing import Tuple

from retk import const
from retk.utils.auth import short_uuid


def add_to_cache(cached: OrderedDict[str, Tuple[datetime, str]], code: str, expired_seconds: int) -> str:
    now = datetime.utcnow()
    pop_list = []
    for k, v in cached.items():
        if v[0] < now:
            pop_list.append(k)
        else:
            break

    [cached.pop(k) for k in pop_list]

    expire_at = now + timedelta(seconds=expired_seconds)
    cid = short_uuid()
    cached[cid] = (expire_at, code)
    return cid


def verify_captcha(cached: OrderedDict[str, Tuple[datetime, str]], cid: str, user_code: str) -> const.CodeEnum:
    try:
        data = cached[cid]
        cache_expire = data[0]
        cache_str = data[1]
    except KeyError:
        code = const.CodeEnum.CAPTCHA_EXPIRED
    except IndexError:
        code = const.CodeEnum.CAPTCHA_ERROR
    else:
        now = datetime.utcnow()
        if now > cache_expire:
            code = const.CodeEnum.CAPTCHA_EXPIRED
        elif cache_str == user_code.lower():
            code = const.CodeEnum.OK
        else:
            code = const.CodeEnum.CAPTCHA_ERROR
    try:
        cached.pop(cid)
    except KeyError:
        pass
    return code
