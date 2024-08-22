import datetime
import math
import uuid
from typing import Tuple

import jwt

from retk import config

HEADERS = {
    'typ': 'jwt',
    'alg': 'RS256'
}
alphabet = "3467ACDEFGHJKLMNPQRTUVWXYabcdefghkmnoprtuvwxy"
alphabet_len = len(alphabet)
__padding = int(math.ceil(math.log(2 ** 128, alphabet_len)))


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
    return f"Bearer {token}"


def jwt_decode(token: str) -> dict:
    t = token.split("Bearer ", maxsplit=1)
    if len(t) != 2:
        raise jwt.InvalidTokenError("Invalid token")
    return jwt.decode(
        t[1],
        key=config.get_settings().JWT_KEY_PUB,
        algorithms=[HEADERS["alg"]],
        options={"verify_exp": True}
    )


def get_token(uid: str, language: str) -> Tuple[str, str]:
    settings = config.get_settings()
    access_token = jwt_encode(
        exp_delta=settings.ACCESS_TOKEN_EXPIRE_DELTA,
        data={
            "is_access": True,
            "uid": uid,
            "language": language,
        },
    )
    refresh_token = jwt_encode(
        exp_delta=settings.REFRESH_TOKEN_EXPIRE_DELTA,
        data={
            "is_access": False,
            "uid": uid,
            "language": language,
        },
    )
    return access_token, refresh_token
