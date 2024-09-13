from collections import OrderedDict as OD
from datetime import datetime
from io import BytesIO
from random import choices
from typing import Tuple, Dict, OrderedDict

from captcha.audio import AudioCaptcha
from captcha.image import ImageCaptcha

from retk import const
from retk.core.utils import cached_verification

DEFAULT_CAPTCHA_EXPIRE_SECOND = 60

img_captcha = ImageCaptcha(font_sizes=(35, 30, 32))
audio_captcha = AudioCaptcha()

alphabet = "347ACEFGJLMNPRTY"
alphabet_len = len(alphabet)
code_idx_range = list(range(0, alphabet_len - 1))

cache_captcha: OrderedDict[str, Tuple[datetime, str]] = OD()


def generate(length: int = 4, sound: bool = False) -> Tuple[str, Dict[str, BytesIO]]:
    code = [alphabet[i] for i in choices(code_idx_range, k=length)]
    code_str = "".join(code)
    data = {
        "img": img_captcha.generate(code_str),
    }
    if sound:
        data["sound"] = audio_captcha.generate(code_str)
    cid = cached_verification.add_to_cache(
        cached=cache_captcha,
        code=code_str.lower(),
        expired_seconds=DEFAULT_CAPTCHA_EXPIRE_SECOND
    )
    return cid, data


def verify_captcha(cid: str, code_str: str) -> const.CodeEnum:
    return cached_verification.verify_captcha(
        cached=cache_captcha,
        cid=cid,
        user_code=code_str
    )
