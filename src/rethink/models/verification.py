from datetime import timedelta
from io import BytesIO
from random import randint
from typing import Tuple, Dict

import jwt
from captcha.audio import AudioCaptcha
from captcha.image import ImageCaptcha

from rethink import const
from .utils import alphabet, alphabet_len, jwt_encode, jwt_decode

DEFAULT_CAPTCHA_EXPIRE_SECOND = 60

img_captcha = ImageCaptcha(font_sizes=(35, 30, 32))
audio_captcha = AudioCaptcha()


def random_captcha(length: int = 4, sound: bool = False) -> Tuple[str, Dict[str, BytesIO]]:
    code = [alphabet[randint(0, alphabet_len - 1)] for _ in range(length)]
    code_str = "".join(code)
    data = {
        "img": img_captcha.generate(code_str),
    }
    if sound:
        data["sound"] = audio_captcha.generate(code_str)
    token = jwt_encode(
        exp_delta=timedelta(seconds=DEFAULT_CAPTCHA_EXPIRE_SECOND),
        data={"code": code_str.lower()}
    )
    return token, data


def verify_captcha(token: str, code_str: str) -> const.Code:
    code = const.Code.CAPTCHA_ERROR
    try:
        data = jwt_decode(token)
        if data["code"] == code_str.lower():
            code = const.Code.OK
    except jwt.ExpiredSignatureError:
        code = const.Code.CAPTCHA_EXPIRED
    except (jwt.DecodeError, Exception):
        code = const.Code.INVALID_AUTH
    return code
