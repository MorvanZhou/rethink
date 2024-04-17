import base64
import hashlib
import os
from typing import Optional, Tuple

import bcrypt

from retk import config, const, regex
from retk.core import user, node
from retk.logger import logger
from retk.models import tps


async def get_user_by_email(email: str) -> Tuple[Optional[tps.UserMeta], const.Code]:
    return await user.get_by_email(email=email)


async def is_right_password(email: str, hashed: str, password: str) -> bool:
    if config.get_settings().ONE_USER:
        pw = os.getenv("RETHINK_SERVER_PASSWORD", None)
        if pw is not None:
            return pw == password
        return True
    base_pw = _base_password(password=password, email=email)
    match = bcrypt.checkpw(base_pw, hashed.encode("utf-8"))
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


def login_by_email_pwd(email: str, password: str) -> const.Code:
    if config.get_settings().ONE_USER:
        logger.warning("on ONE_USER mode, user registration will be skipped")
        return const.Code.ONE_USER_MODE
    if regex.EMAIL.match(email) is None:
        return const.Code.INVALID_EMAIL
    if regex.VALID_PASSWORD.match(password) is None:
        return const.Code.INVALID_PASSWORD
    return const.Code.OK


async def signup(
        email: str,
        password: str,
        language: str = const.Language.EN.value,
) -> Tuple[Optional[tps.UserMeta], const.Code]:
    code = login_by_email_pwd(email=email, password=password)
    if code != const.Code.OK:
        return None, code
    u, code = await user.get_by_email(email=email)
    if code == const.Code.OK or u is not None:
        return None, const.Code.USER_EXIST

    u, code = await user.add(
        account=email,
        source=const.UserSource.EMAIL.value,
        email=email,
        hashed=hash_password(password=password, email=email),
        nickname=email.split("@")[0],
        avatar="",
        language=language,
    )
    if code != const.Code.OK:
        return None, code

    code = await node.new_user_add_default_nodes(uid=u["id"], language=language)
    return u, code


async def reset_password(
        email: str,
        password: str,
) -> Tuple[Optional[tps.UserMeta], const.Code]:
    code = login_by_email_pwd(email=email, password=password)
    if code != const.Code.OK:
        return None, code
    u, code = await user.get_by_email(email=email)
    if code != const.Code.OK:
        return None, code
    if u is None:
        return None, const.Code.INVALID_AUTH
    code = await user.reset_password(
        uid=u["id"],
        hashed=hash_password(password=password, email=email)
    )
    return u, code
