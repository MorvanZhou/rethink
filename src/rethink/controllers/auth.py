import base64
import datetime
import hashlib
import re
import traceback
from typing import Optional, Tuple

import bcrypt
import jwt
from fastapi import Header

from rethink import config, const, models
from rethink.logger import logger
from .utils import TokenDecode

HEADERS = {
    'typ': 'jwt',
    'alg': 'RS256'
}

# at least 6 characters, at most 20 characters, at least one letter and one number
VALID_PASSWORD_PTN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{6,20}$")


def jwt_encode(uid: str, language: str) -> str:
    """
    Create token

    Args:
        uid: user id
        language: user language

    Returns:
        str: token
    """
    payload = {
        "id": uid,
        "language": language,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=config.get_settings().JWT_EXPIRED_DAYS)
    }
    token = jwt.encode(
        payload=payload,
        key=config.get_settings().JWT_KEY,
        algorithm=HEADERS["alg"],
        headers=HEADERS,
    )
    return token


def token2uid(token: str = Header(...)) -> TokenDecode:
    uid = ""
    err = ""
    language = const.Language.EN.value
    try:
        payload = jwt.decode(
            token,
            key=config.get_settings().JWT_KEY_PUB,
            algorithms=[HEADERS["alg"]],
            options={"verify_exp": True}
        )
        u, code = models.user.get(uid=payload["id"])
        if code != const.Code.OK:
            logger.error(f"models.user.get err: {const.CODE_MESSAGES[code].cn}")
            return TokenDecode(code=code, language=language)
        uid = u["id"]
        language = u["language"]
    except jwt.ExpiredSignatureError:
        code = const.Code.EXPIRED_AUTH
        err = traceback.format_exc().replace("\n", "\\n")
    except jwt.DecodeError:
        code = const.Code.INVALID_AUTH
        err = traceback.format_exc().replace("\n", "\\n")
    except Exception:  # pylint: disable=broad-except
        code = const.Code.INVALID_AUTH
        err = traceback.format_exc().replace("\n", "\\n")
    if code != const.Code.OK:
        logger.error(f"jwt_decode err: {err}")
    return TokenDecode(code=code, uid=uid, language=language)


def get_user_by_email(email: str) -> Tuple[Optional[models.tps.UserMeta], const.Code]:
    return models.user.get_by_email(email=email)


def verify_user(u: models.tps.UserMeta, password: str) -> bool:
    if config.get_settings().ONE_USER:
        return True
    base_pw = _base_password(password=password, email=u["email"])
    db_hash = models.user.get_hash_by_uid(u["id"])
    match = bcrypt.checkpw(base_pw, db_hash.encode("utf-8"))
    return match


def _base_password(password: str, email: str) -> bytes:
    return base64.b64encode(hashlib.sha256(f"{password}&&{email}".encode("utf-8")).digest())


def register_user(
        email: str,
        password: str,
        language: str = const.Language.EN.value,
) -> Tuple[str, const.Code]:
    if config.get_settings().ONE_USER:
        logger.warning("on ONE_USER mode, user registration will be ignored")
        return "", const.Code.ONE_USER_MODE
    if VALID_PASSWORD_PTN.match(password) is None:
        return "", const.Code.INVALID_PASSWORD
    u, code = models.user.get_by_email(email=email)
    if code == const.Code.OK or u is not None:
        return "", const.Code.USER_EXIST

    bpw = _base_password(password=password, email=email)
    hashed = bcrypt.hashpw(bpw, config.get_settings().DB_SALT)
    uid, code = models.user.add(
        account=email,
        source=const.UserSource.EMAIL.value,
        email=email,
        hashed=hashed.decode("utf-8"),
        nickname=email.split("@")[0],
        avatar="",
        language=language,
    )
    if code != const.Code.OK:
        return "", code

    code = models.node.new_user_add_default_nodes(uid=uid, language=language)
    return uid, code
