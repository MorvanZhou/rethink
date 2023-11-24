import base64
import hashlib
import re
import traceback
from typing import Optional, Tuple

import bcrypt
import jwt
from fastapi import Header

from rethink import config, const, models
from rethink.controllers.utils import TokenDecode
from rethink.logger import logger
from rethink.models.utils import jwt_decode

# at least 6 characters, at most 20 characters, at least one letter and one number
VALID_PASSWORD_PTN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{6,20}$")


async def token2uid(token: str = Header(...)) -> TokenDecode:
    uid = ""
    err = ""
    language = const.Language.EN.value
    try:
        payload = jwt_decode(token=token)
        u, code = await models.user.get(uid=payload["uid"])
        if code != const.Code.OK:
            logger.error(f"models.user.get err: {const.CODE_MESSAGES[code].zh}")
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


async def get_user_by_email(email: str) -> Tuple[Optional[models.tps.UserMeta], const.Code]:
    return await models.user.get_by_email(email=email)


async def verify_user(u: models.tps.UserMeta, password: str) -> bool:
    if config.get_settings().ONE_USER:
        return True
    base_pw = _base_password(password=password, email=u["email"])
    db_hash = await models.user.get_hash_by_uid(u["id"])
    match = bcrypt.checkpw(base_pw, db_hash.encode("utf-8"))
    return match


def _base_password(password: str, email: str) -> bytes:
    return base64.b64encode(hashlib.sha256(f"{password}&&{email}".encode("utf-8")).digest())


async def register_user(
        email: str,
        password: str,
        language: str = const.Language.EN.value,
) -> Tuple[str, const.Code]:
    if config.get_settings().ONE_USER:
        logger.warning("on ONE_USER mode, user registration will be skipped")
        return "", const.Code.ONE_USER_MODE
    if VALID_PASSWORD_PTN.match(password) is None:
        return "", const.Code.INVALID_PASSWORD
    u, code = await models.user.get_by_email(email=email)
    if code == const.Code.OK or u is not None:
        return "", const.Code.USER_EXIST

    bpw = _base_password(password=password, email=email)
    hashed = bcrypt.hashpw(bpw, config.get_settings().DB_SALT)
    uid, code = await models.user.add(
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

    code = await models.node.new_user_add_default_nodes(uid=uid, language=language)
    return uid, code
