from datetime import timedelta
from io import BytesIO
from random import choices
from typing import Tuple, Dict

import jwt
from captcha.audio import AudioCaptcha
from captcha.image import ImageCaptcha

from retk import const, config
from retk.utils import jwt_encode, jwt_decode

DEFAULT_CAPTCHA_EXPIRE_SECOND = 60

img_captcha = ImageCaptcha(font_sizes=(35, 30, 32))
audio_captcha = AudioCaptcha()

alphabet = "347ACEFGJLMNPRTY"
alphabet_len = len(alphabet)
code_idx_range = list(range(0, alphabet_len - 1))


def generate(length: int = 4, sound: bool = False) -> Tuple[str, Dict[str, BytesIO]]:
    code = [alphabet[i] for i in choices(code_idx_range, k=length)]
    code_str = "".join(code)
    data = {
        "img": img_captcha.generate(code_str),
    }
    if sound:
        data["sound"] = audio_captcha.generate(code_str)
    token = jwt_encode(
        exp_delta=timedelta(seconds=DEFAULT_CAPTCHA_EXPIRE_SECOND),
        data={"code": code_str.lower() + config.get_settings().CAPTCHA_SALT}
    )
    # TODO: 以后有 redis 之后要考虑 token 的一次性校验。校验过一次后，需要主动失效
    return token, data


def verify_captcha(token: str, code_str: str) -> const.CodeEnum:
    code = const.CodeEnum.CAPTCHA_ERROR
    try:
        data = jwt_decode(token)
        if data["code"] == code_str.lower() + config.get_settings().CAPTCHA_SALT:
            code = const.CodeEnum.OK
    except jwt.ExpiredSignatureError:
        code = const.CodeEnum.CAPTCHA_EXPIRED
    except (jwt.DecodeError, Exception):  # pylint: disable=broad-except
        code = const.CodeEnum.INVALID_AUTH
    return code
