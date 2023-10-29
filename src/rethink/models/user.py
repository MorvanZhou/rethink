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
        "recentCursorSearchSelectedNIds": [],
        "recentSearch": [],
        "language": language,
        "nodeDisplayMethod": const.NodeDisplayMethod.CARD.value,
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
        node_display_method = u["nodeDisplayMethod"]
    else:
        if node_display_method > len(const.NodeDisplayMethod) or node_display_method < 0:
            return None, const.Code.INVALID_NODE_DISPLAY_METHOD

    res = COLL.users.update_one(
        {"id": uid},
        {"$set": {
            "email": email,
            "hashed": hashed,
            "nickname": nickname,
            "avatar": avatar,
            "modifiedAt": datetime.datetime.now(tz=utc),
            "language": language,
            "nodeDisplayMethod": node_display_method,
        }}
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
