import datetime
import html
from typing import Optional, Tuple

from bson import ObjectId
from bson.tz_util import utc

from rethink import const, config
from . import tps, utils
from .database import COLL


async def add(
        account: str,
        source: int,
        email: str,
        hashed: str,
        nickname: str,
        avatar: str,
        language: str,
) -> Tuple[str, const.Code]:
    if await COLL.users.find_one({"account": account, "source": source}) is not None:
        return "", const.Code.EMAIL_OCCUPIED
    oid = ObjectId()
    # assert language in const.Language
    if not const.Language.is_valid(language):
        language = const.Language.EN.value
    data: tps.UserMeta = {
        "_id": oid,
        "id": utils.short_uuid(),
        "account": account,
        "source": source,
        "email": email,
        "hashed": hashed,
        "avatar": str(avatar),
        "disabled": False,
        "nickname": nickname,
        "modifiedAt": oid.generation_time,
        "nodeIds": [],
        "language": language,
        "usedSpace": 0,
        "type": const.USER_TYPE.NORMAL.id,
        "lastState": {
            "recentCursorSearchSelectedNIds": [],
            "recentSearch": [],
            "nodeDisplayMethod": const.NodeDisplayMethod.CARD.value,
            "nodeDisplaySortKey": "modifiedAt"
        }
    }
    res = await COLL.users.insert_one(data)
    if not res.acknowledged:
        return "", const.Code.OPERATION_FAILED
    return data["id"], const.Code.OK


async def update(
        uid: str,
        hashed: str = "",
        nickname: str = "",
        avatar: str = "",
        language: str = "",
        node_display_method: int = -1,
        node_display_sort_key: str = "",
) -> Tuple[Optional[tps.UserMeta], const.Code]:
    u, code = await get(uid=uid)
    if code != const.Code.OK:
        return None, code

    new_data = {"modifiedAt": datetime.datetime.now(tz=utc), }

    hashed = hashed.strip()
    if hashed != "" and hashed != u["hashed"]:
        new_data["hashed"] = hashed
    nickname = nickname.strip()
    nickname = html.escape(nickname)
    if nickname != "" and nickname != u["nickname"]:
        new_data["nickname"] = nickname
    avatar = str(avatar).strip()
    if avatar != "" and avatar != u["avatar"]:
        new_data["avatar"] = avatar
    language = language.strip()
    if language != "" and language != u["language"]:
        if not const.Language.is_valid(language):
            return None, const.Code.INVALID_LANGUAGE
        new_data["language"] = language

    if node_display_method != u["lastState"]["nodeDisplayMethod"] and node_display_method >= 0:
        if node_display_method >= len(const.NodeDisplayMethod):
            return None, const.Code.INVALID_NODE_DISPLAY_METHOD
        new_data["lastState.nodeDisplayMethod"] = node_display_method
    if node_display_sort_key != "" and node_display_sort_key != u["lastState"]["nodeDisplaySortKey"]:
        if node_display_sort_key not in ["modifiedAt", "createdAt", "title"]:
            return None, const.Code.INVALID_NODE_DISPLAY_SORT_KEY
        new_data["lastState.nodeDisplaySortKey"] = node_display_sort_key

    res = await COLL.users.update_one(
        {"id": uid},
        {"$set": new_data},
    )
    if res.modified_count != 1:
        return None, const.Code.OPERATION_FAILED
    return await get(uid=uid)


async def delete(uid: str) -> const.Code:
    res = await COLL.users.delete_one({"id": uid})
    return const.Code.OK if res.deleted_count == 1 else const.Code.OPERATION_FAILED


async def disable(uid: str) -> const.Code:
    res = await COLL.users.update_one(
        {"id": uid},
        {"$set": {"disabled": True}}
    )
    return const.Code.OK if res.modified_count == 1 else const.Code.OPERATION_FAILED


async def enable(uid: str) -> const.Code:
    res = await COLL.users.update_one(
        {"id": uid},
        {"$set": {"disabled": False}}
    )
    return const.Code.OK if res.modified_count == 1 else const.Code.OPERATION_FAILED


async def get_by_email(email: str) -> Tuple[Optional[tps.UserMeta], const.Code]:
    if config.get_settings().ONE_USER:
        source = const.UserSource.LOCAL.value
    else:
        source = const.UserSource.EMAIL.value
    return await get_account(account=email, source=source)


async def get_account(account: str, source: int) -> Tuple[Optional[tps.UserMeta], const.Code]:
    u = await COLL.users.find_one({"source": source, "account": account, "disabled": False})
    if u is None:
        return None, const.Code.ACCOUNT_OR_PASSWORD_ERROR
    return u, const.Code.OK


async def get(uid: str) -> Tuple[Optional[tps.UserMeta], const.Code]:
    u = await COLL.users.find_one({"id": uid, "disabled": False})
    if u is None:
        return None, const.Code.ACCOUNT_OR_PASSWORD_ERROR
    if u["usedSpace"] < 0:
        # reset usedSpace to 0
        await COLL.users.update_one(
            {"id": uid},
            {"$set": {"usedSpace": 0}}
        )
        u["usedSpace"] = 0

    return u, const.Code.OK


async def get_hash_by_uid(uid: str) -> Optional[str]:
    u = await COLL.users.find_one({"id": uid, "disabled": False})
    if u is None:
        return None
    return u["hashed"]


async def is_exist(uid: str) -> bool:
    try:
        await COLL.users.find({"id": uid, "disabled": False}, limit=1).next()
    except StopIteration:
        return False
    return True


async def update_used_space(uid: str, delta: int) -> const.Code:
    if delta == 0:
        return const.Code.OK
    if not await is_exist(uid=uid):
        return const.Code.ACCOUNT_OR_PASSWORD_ERROR
    res = await COLL.users.update_one(
        {"id": uid},
        {"$inc": {"usedSpace": delta}}
    )
    return const.Code.OK if res.modified_count == 1 else const.Code.OPERATION_FAILED


async def user_space_not_enough(uid: str = None, u: tps.UserMeta = None) -> bool:
    if uid is None and u is None:
        raise ValueError("uid and u cannot be None at the same time")
    if config.is_local_db():
        return False
    if uid is not None:
        u, code = await get(uid=uid)
        if code != const.Code.OK:
            return True
    return u["usedSpace"] > const.USER_TYPE.id2config(u["type"]).max_store_space


async def reset_password(uid: str, hashed: str) -> const.Code:
    res = await COLL.users.update_one(
        {"id": uid},
        {"$set": {"hashed": hashed}}
    )
    return const.Code.OK if res.acknowledged == 1 else const.Code.OPERATION_FAILED
