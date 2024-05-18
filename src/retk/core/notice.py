from datetime import datetime
from typing import List, Optional, Tuple, TypedDict

from bson import ObjectId
from bson.tz_util import utc

from retk import const, config
from retk.models.client import client
from retk.models.tps import AuthedUser, NoticeManagerDelivery
from retk.utils import datetime2str


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
        "content": content,
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


class Notice(TypedDict):
    id: str
    title: str
    content: str
    publishAt: str
    read: bool
    readTime: Optional[datetime]


class SystemNotices(TypedDict):
    total: int
    notices: List[Notice]


class Notices(TypedDict):
    system: SystemNotices


async def get_user_notices(au: AuthedUser) -> Tuple[Notices, const.CodeEnum]:
    if not config.is_local_db():
        system_notices = await client.coll.notice_system.find(
            {"recipientId": au.u.id},
            projection={"noticeId": 1, "read": 1, "readTime": 1}
        ).limit(10).to_list(None)
        # Get the details of the notices
        n_details = await client.coll.notice_manager_delivery.find(
            {"_id": {"$in": [n["noticeId"] for n in system_notices]}},
            projection={"title": 1, "content": 1, "publishAt": 1}
        ).to_list(None)
    else:
        system_notices = await client.coll.notice_system.find(
            {"recipientId": au.u.id},
        ).limit(10).to_list(None)
        system_notices = [{
            "noticeId": n["noticeId"],
            "read": n["read"],
            "readTime": n["readTime"],
        } for n in system_notices]
        # Get the details of the notices
        n_details = await client.coll.notice_manager_delivery.find(
            {"_id": {"$in": [n["noticeId"] for n in system_notices]}},
        ).to_list(None)

    total_system_system = await client.coll.notice_system.count_documents({"recipientId": au.u.id})
    n_details_dict = {n["_id"]: n for n in n_details}
    new_system_notices: List[Notice] = []
    for sn in system_notices:
        detail = n_details_dict[sn["noticeId"]]
        new_system_notices.append({
            "id": str(sn["noticeId"]),
            "title": detail["title"],
            "content": detail["content"],
            "publishAt": datetime2str(detail["publishAt"]),
            "read": sn["read"],
            "readTime": sn["readTime"],
        })

    return {
        "system": {
            "total": total_system_system,
            "notices": new_system_notices,
        }
    }, const.CodeEnum.OK


async def mark_system_notice_read(
        au: AuthedUser,
        notice_id: str,
) -> const.CodeEnum:
    res = await client.coll.notice_system.update_one(
        {"recipientId": au.u.id, "noticeId": ObjectId(notice_id)},
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
