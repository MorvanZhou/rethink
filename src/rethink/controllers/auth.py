import base64
import hashlib
import traceback
from typing import Optional, Tuple

import bcrypt
import jwt
from fastapi import Header

from rethink import config, const, core, regex
from rethink.controllers.utils import TokenDecode
from rethink.logger import logger
from rethink.models import tps
from rethink.utils import jwt_decode


def __one_line_traceback() -> str:
    return traceback.format_exc().replace("\n", "\\n")


async def token2uid(token: str = Header(...)) -> TokenDecode:
    uid = ""
    err = ""
    language = const.Language.EN.value
    try:
        payload = jwt_decode(token=token)
        u, code = await core.user.get(uid=payload["uid"])
        if code != const.Code.OK:
            logger.error(f"core.user.get err: {const.CODE_MESSAGES[code].zh}")
            return TokenDecode(code=code, language=language)
        uid = u["id"]
        language = u["settings"]["language"]
    except jwt.exceptions.ExpiredSignatureError:
        code = const.Code.EXPIRED_AUTH
        err = "auth token expired"
    except jwt.exceptions.DecodeError:
        code = const.Code.INVALID_AUTH
        err = __one_line_traceback()
    except jwt.exceptions.InvalidTokenError:
        code = const.Code.INVALID_AUTH
        err = __one_line_traceback()
    except Exception:  # pylint: disable=broad-except
        code = const.Code.INVALID_AUTH
        err = __one_line_traceback()
    if code != const.Code.OK:
        logger.error(f"jwt_decode err: {err}")
    return TokenDecode(code=code, uid=uid, language=language)


async def get_user_by_email(email: str) -> Tuple[Optional[tps.UserMeta], const.Code]:
    return await core.user.get_by_email(email=email)


async def verify_user(u: tps.UserMeta, password: str) -> bool:
    if config.get_settings().ONE_USER:
        return True
    base_pw = _base_password(password=password, email=u["email"])
    match = bcrypt.checkpw(base_pw, u["hashed"].encode("utf-8"))
    return match


def _base_password(password: str, email: str) -> bytes:
    # update hash strategy
    s = f"{password}&&{config.get_settings().DB_SALT}$${email}"
    logger.debug(f"hashing: {s}")
    return base64.b64encode(
        hashlib.sha256(s.encode("utf-8")).digest()
    )


def hash_password(password: str, email: str) -> str:
    bpw = _base_password(password=password, email=email)
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(bpw, salt=salt).decode("utf-8")


def validate_email_pwd(email: str, password: str) -> const.Code:
    if config.get_settings().ONE_USER:
        logger.warning("on ONE_USER mode, user registration will be skipped")
        return const.Code.ONE_USER_MODE
    if regex.EMAIL.match(email) is None:
        return const.Code.INVALID_EMAIL
    if regex.VALID_PASSWORD.match(password) is None:
        return const.Code.INVALID_PASSWORD
    return const.Code.OK


async def register_user(
        email: str,
        password: str,
        language: str = const.Language.EN.value,
) -> Tuple[str, const.Code]:
    code = validate_email_pwd(email=email, password=password)
    if code != const.Code.OK:
        return "", code
    u, code = await core.user.get_by_email(email=email)
    if code == const.Code.OK or u is not None:
        return "", const.Code.USER_EXIST

    uid, code = await core.user.add(
        account=email,
        source=const.UserSource.EMAIL.value,
        email=email,
        hashed=hash_password(password=password, email=email),
        nickname=email.split("@")[0],
        avatar="",
        language=language,
    )
    if code != const.Code.OK:
        return "", code

    code = await core.node.new_user_add_default_nodes(uid=uid, language=language)
    return uid, code


async def update_password(
        email: str,
        password: str,
) -> Tuple[Optional[tps.UserMeta], const.Code]:
    code = validate_email_pwd(email=email, password=password)
    if code != const.Code.OK:
        return None, code
    u, code = await core.user.get_by_email(email=email)
    if code != const.Code.OK:
        return None, code
    if u is None:
        return None, const.Code.INVALID_AUTH
    code = await core.user.reset_password(
        uid=u["id"],
        hashed=hash_password(password=password, email=email)
    )
    return u, code
