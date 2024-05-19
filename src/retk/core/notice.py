from datetime import datetime
from typing import List, Optional, Tuple, TypedDict

from bson import ObjectId
from bson.tz_util import utc

from retk import const, config
from retk.models.client import client
from retk.models.tps import AuthedUser, NoticeManagerDelivery
from retk.utils import datetime2str, md2html, md2txt


async def post_in_manager_delivery(
        au: AuthedUser,
        title: str,
        content: str,
        recipient_type: int,
        batch_type_ids: List[str],
        publish_at: Optional[datetime] = None  # if None, use current
) -> Tuple[Optional[NoticeManagerDelivery], const.CodeEnum]:
    if const.USER_TYPE.id2config(au.u.type) not in (const.USER_TYPE.ADMIN, const.USER_TYPE.MANAGER):
        return None, const.CodeEnum.NOT_PERMITTED
    if publish_at is None:
        publish_at = datetime.now(tz=utc)

    # if publish_at is not utc, convert it to utc
    if publish_at.tzinfo is None or publish_at.tzinfo.utcoffset(publish_at) is None:
        publish_at = publish_at.replace(tzinfo=utc)
    elif publish_at.tzinfo != utc:
        publish_at = publish_at.astimezone(utc)

    # add system notice
    notice: NoticeManagerDelivery = {
        "_id": ObjectId(),
        "senderType": au.u.type,
        "senderId": au.u.id,
        "title": title,
        "html": md2html(content),
        "snippet": md2txt(content)[:20],
        "recipientType": recipient_type,  # send to which user type, 0: all, 1: batch, 2: admin, 3: manager
        "batchTypeIds": batch_type_ids,  # if recipient=batch, put user id here
        "publishAt": publish_at,  # publish time
        "scheduled": False,  # has been scheduled to sent to user
    }
    res = await client.coll.notice_manager_delivery.insert_one(notice)
    if not res.acknowledged:
        return None, const.CodeEnum.OPERATION_FAILED
    return notice, const.CodeEnum.OK


async def get_system_notices(
        page: int,
        limit: int,
) -> Tuple[List[NoticeManagerDelivery], int]:
    total = await client.coll.notice_manager_delivery.count_documents({})
    notices = await client.coll.notice_manager_delivery.find(
        {}
    ).skip(page * limit).limit(limit=limit).to_list(None)
    return notices, total


async def get_system_notice(
        uid: str,
        notice_id: str,
) -> Tuple[Optional[NoticeManagerDelivery], const.CodeEnum]:
    notice = await client.coll.notice_manager_delivery.find_one(
        {"_id": ObjectId(notice_id), "scheduled": True}
    )
    if notice is None or notice["senderType"] not in [const.USER_TYPE.ADMIN.id, const.USER_TYPE.MANAGER.id]:
        # check if the notice exists and is sent by admin or manager
        return None, const.CodeEnum.NOTICE_NOT_FOUND
    if notice["recipientType"] == const.notice.RecipientTypeEnum.ALL:
        # this notice is for all users
        return notice, const.CodeEnum.OK
    elif notice["recipientType"] == const.notice.RecipientTypeEnum.BATCH:
        # this notice is for some users
        if uid in notice["batchTypeIds"]:
            # check if the user is in the batch
            return notice, const.CodeEnum.OK
        return None, const.CodeEnum.NOTICE_NOT_FOUND
    else:
        # this notice is for a specific user type
        u = await client.coll.users.find_one({"id": uid})
        if u is None or u["type"] != notice["recipientType"]:
            # check if the user is the recipient type
            return None, const.CodeEnum.NOTICE_NOT_FOUND
    return notice, const.CodeEnum.OK


class Notice(TypedDict):
    id: str
    title: str
    snippet: str
    publishAt: str
    read: bool
    readTime: Optional[str]


class SystemNotices(TypedDict):
    total: int
    notices: List[Notice]


class Notices(TypedDict):
    hasUnread: bool
    system: SystemNotices


async def get_user_notices(
        au: AuthedUser,
        unread_only: bool = False,
        page: int = 0,
        limit: int = 10,
) -> Tuple[Notices, const.CodeEnum]:
    c = {"recipientId": au.u.id}
    if unread_only:
        c["read"] = False
    if not config.is_local_db():
        user_system_notices = await client.coll.notice_system.find(
            c,
            projection={"noticeId": 1, "read": 1, "readTime": 1}
        ).sort("_id", -1).skip(page * limit).limit(limit=limit).to_list(None)
        # Get the details of the notices
        n_details = await client.coll.notice_manager_delivery.find(
            {"_id": {"$in": [n["noticeId"] for n in user_system_notices]}},
            projection={"title": 1, "snippet": 1, "publishAt": 1}
        ).to_list(None)
    else:
        user_system_notices = await client.coll.notice_system.find(
            c,
        ).sort("_id", -1).skip(page * limit).limit(limit=limit).to_list(None)
        user_system_notices = [{
            "noticeId": n["noticeId"],
            "read": n["read"],
            "readTime": n["readTime"],
        } for n in user_system_notices]
        # Get the details of the notices
        n_details = await client.coll.notice_manager_delivery.find(
            {"_id": {"$in": [n["noticeId"] for n in user_system_notices]}},
        ).to_list(None)

    total_system_system = await client.coll.notice_system.count_documents(c)
    if c.get("read", True):
        # if not unread_only, check if there are unread notices
        has_unread = await client.coll.notice_system.count_documents({"recipientId": au.u.id, "read": False}) > 0
    else:
        has_unread = total_system_system > 0

    n_details_dict = {n["_id"]: n for n in n_details}
    new_system_notices: List[Notice] = []
    for usn in user_system_notices:
        detail = n_details_dict[usn["noticeId"]]
        new_system_notices.append({
            "id": str(usn["noticeId"]),
            "title": detail["title"],
            "snippet": detail["snippet"],
            "publishAt": datetime2str(detail["publishAt"]),
            "read": usn["read"],
            "readTime": datetime2str(usn["readTime"]) if usn["readTime"] is not None else None,
        })

    return {
        "hasUnread": has_unread,
        "system": {
            "total": total_system_system,
            "notices": new_system_notices,
        }
    }, const.CodeEnum.OK


async def mark_system_notice_read(
        uid: str,
        notice_id: str,
) -> const.CodeEnum:
    res = await client.coll.notice_system.update_one(
        {"recipientId": uid, "noticeId": ObjectId(notice_id)},
        {"$set": {"read": True, "readTime": datetime.now(tz=utc)}}
    )
    if not res.acknowledged:
        return const.CodeEnum.OPERATION_FAILED
    return const.CodeEnum.OK


async def mark_all_system_notice_read(
        au: AuthedUser,
) -> const.CodeEnum:
    res = await client.coll.notice_system.update_many(
        {"recipientId": au.u.id},
        {"$set": {"read": True, "readTime": datetime.now(tz=utc)}}
    )
    if not res.acknowledged:
        return const.CodeEnum.OPERATION_FAILED
    return const.CodeEnum.OK
