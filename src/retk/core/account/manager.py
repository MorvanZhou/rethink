import base64
import hashlib
import os
from typing import Optional, Tuple

import bcrypt

from retk import config, const, regex
from retk.core import user, node
from retk.logger import logger
from retk.models import tps
from retk.models.client import client


async def get_user_by_email(email: str) -> Tuple[Optional[tps.UserMeta], const.CodeEnum]:
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


def login_by_email_pwd(email: str, password: str) -> const.CodeEnum:
    if config.get_settings().ONE_USER:
        logger.warning("on ONE_USER mode, user registration will be skipped")
        return const.CodeEnum.ONE_USER_MODE
    if regex.EMAIL.match(email) is None:
        return const.CodeEnum.INVALID_EMAIL
    if regex.VALID_PASSWORD.match(password) is None:
        return const.CodeEnum.INVALID_PASSWORD
    return const.CodeEnum.OK


async def signup(
        email: str,
        password: str,
        language: str = const.LanguageEnum.EN.value,
) -> Tuple[Optional[tps.UserMeta], const.CodeEnum]:
    code = login_by_email_pwd(email=email, password=password)
    if code != const.CodeEnum.OK:
        return None, code
    u, code = await user.get_by_email(email=email)
    if code == const.CodeEnum.OK or u is not None:
        return None, const.CodeEnum.USER_EXIST

    u, code = await user.add(
        account=email,
        source=const.UserSourceEnum.EMAIL.value,
        email=email,
        hashed=hash_password(password=password, email=email),
        nickname=email.split("@")[0],
        avatar="",
        language=language,
    )
    if code != const.CodeEnum.OK:
        return None, code

    code = await node.new_user_add_default_nodes(uid=u["id"], language=language)
    return u, code


async def delete(uid: str):
    res = await client.coll.users.delete_one({"id": uid})
    if res.deleted_count != 1:
        return
    await client.coll.nodes.delete_many({"uid": uid})
    await client.coll.user_file.delete_many({"uid": uid})
    await client.coll.import_data.delete_many({"uid": uid})
    await client.search.force_delete_all(uid=uid)


async def disable(uid: str) -> const.CodeEnum:
    res = await client.coll.users.update_one(
        {"id": uid},
        {"$set": {"disabled": True}}
    )
    return const.CodeEnum.OK if res.acknowledged == 1 else const.CodeEnum.OPERATION_FAILED


async def enable(uid: str) -> const.CodeEnum:
    res = await client.coll.users.update_one(
        {"id": uid},
        {"$set": {"disabled": False}}
    )
    return const.CodeEnum.OK if res.acknowledged == 1 else const.CodeEnum.OPERATION_FAILED
