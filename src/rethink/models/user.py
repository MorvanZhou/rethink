import datetime
from typing import List, Optional, Tuple

from bson import ObjectId
from bson.tz_util import utc

from rethink import const, config
from . import tps, utils
from .database import COLL


def add(
        account: str,
        source: int,
        email: str,
        hashed: str,
        nickname: str,
        avatar: str,
        language: str,
) -> Tuple[str, const.Code]:
    if COLL.users.find_one({"account": account, "source": source}) is not None:
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
    res = COLL.users.insert_one(data)
    if not res.acknowledged:
        return "", const.Code.OPERATION_FAILED
    un_data: tps.UserNodeIds = {
        "_id": data["_id"],
        "id": data["id"],
        "nodeIds": [],
    }
    res = COLL.unids.insert_one(un_data)
    if not res.acknowledged:
        return "", const.Code.OPERATION_FAILED
    return data["id"], const.Code.OK


def update(
        uid: str,
        email: str = "",
        hashed: str = "",
        nickname: str = "",
        avatar: str = "",
        language: str = "",
        node_display_method: int = -1,
        node_display_sort_key: str = "",
) -> Tuple[Optional[tps.UserMeta], const.Code]:
    u, code = get(uid=uid)
    if code != const.Code.OK:
        return None, code
    email = email.strip()
    if email not in ["", u["email"]] and COLL.users.find_one(
            {"account": email, "source": const.UserSource.EMAIL.value}
    ) is not None:
        return None, const.Code.EMAIL_OCCUPIED
    if email == "":
        email = u["email"]
    hashed = hashed.strip()
    if hashed == "":
        hashed = u["hashed"]
    nickname = nickname.strip()
    if nickname == "":
        nickname = u["nickname"]
    avatar = str(avatar).strip()
    if avatar == "":
        avatar = u["avatar"]
    language = language.strip()
    if language == "":
        language = u["language"]
    elif not const.Language.is_valid(language):
        return None, const.Code.INVALID_LANGUAGE

    if node_display_method == -1:
        node_display_method = u["lastState"]["nodeDisplayMethod"]
    else:
        if node_display_method > len(const.NodeDisplayMethod) or node_display_method < 0:
            return None, const.Code.INVALID_NODE_DISPLAY_METHOD
    if node_display_sort_key == "":
        node_display_sort_key = u["lastState"]["nodeDisplaySortKey"]
    else:
        if node_display_sort_key not in ["modifiedAt", "createdAt", "title"]:
            return None, const.Code.INVALID_NODE_DISPLAY_SORT_KEY
    res = COLL.users.update_one(
        {"id": uid},
        {"$set": {
            "email": email,
            "hashed": hashed,
            "nickname": nickname,
            "avatar": avatar,
            "modifiedAt": datetime.datetime.now(tz=utc),
            "language": language,
            "lastState.nodeDisplayMethod": node_display_method,
            "lastState.nodeDisplaySortKey": node_display_sort_key,
        }},
    )
    if res.modified_count != 1:
        return None, const.Code.OPERATION_FAILED
    return get(uid=uid)


def delete(uid: str) -> const.Code:
    res = COLL.users.delete_one({"id": uid})
    return const.Code.OK if res.deleted_count == 1 else const.Code.OPERATION_FAILED


def disable(uid: str) -> const.Code:
    res = COLL.users.update_one(
        {"id": uid},
        {"$set": {"disabled": True}}
    )
    return const.Code.OK if res.modified_count == 1 else const.Code.OPERATION_FAILED


def enable(uid: str) -> const.Code:
    res = COLL.users.update_one(
        {"id": uid},
        {"$set": {"disabled": False}}
    )
    return const.Code.OK if res.modified_count == 1 else const.Code.OPERATION_FAILED


def get_by_email(email: str) -> Tuple[Optional[tps.UserMeta], const.Code]:
    if config.get_settings().ONE_USER:
        source = const.UserSource.LOCAL.value
    else:
        source = const.UserSource.EMAIL.value
    return get_account(account=email, source=source)


def get_account(account: str, source: int) -> Tuple[Optional[tps.UserMeta], const.Code]:
    u = COLL.users.find_one({"source": source, "account": account, "disabled": False})
    if u is None:
        return None, const.Code.ACCOUNT_OR_PASSWORD_ERROR
    return u, const.Code.OK


def get(uid: str) -> Tuple[Optional[tps.UserMeta], const.Code]:
    u = COLL.users.find_one({"id": uid, "disabled": False})
    if u is None:
        return None, const.Code.ACCOUNT_OR_PASSWORD_ERROR
    if u["usedSpace"] < 0:
        # reset usedSpace to 0
        COLL.users.update_one(
            {"id": uid},
            {"$set": {"usedSpace": 0}}
        )
        u["usedSpace"] = 0

    return u, const.Code.OK


def get_hash_by_uid(uid: str) -> Optional[str]:
    u = COLL.users.find_one({"id": uid, "disabled": False})
    if u is None:
        return None
    return u["hashed"]


def is_exist(uid: str) -> bool:
    try:
        COLL.users.find({"id": uid, "disabled": False}, limit=1).next()
    except StopIteration:
        return False
    return True


def get_node_ids(uid: str) -> Tuple[List[str], const.Code]:
    if not is_exist(uid=uid):
        return [], const.Code.ACCOUNT_OR_PASSWORD_ERROR
    doc = COLL.unids.find_one({"id": uid})
    return doc["nodeIds"], const.Code.OK


def update_used_space(uid: str, delta: int) -> const.Code:
    if not is_exist(uid=uid):
        return const.Code.ACCOUNT_OR_PASSWORD_ERROR
    res = COLL.users.update_one(
        {"id": uid},
        {"$inc": {"usedSpace": delta}}
    )
    return const.Code.OK if res.modified_count == 1 else const.Code.OPERATION_FAILED


def user_space_not_enough(uid: str = None, u: tps.UserMeta = None) -> bool:
    if uid is None and u is None:
        raise ValueError("uid and u cannot be None at the same time")
    if config.is_local_db():
        return False
    if uid is not None:
        u, code = get(uid=uid)
        if code != const.Code.OK:
            return True
    return u["usedSpace"] > const.USER_TYPE.id2config(u["type"]).max_store_space
