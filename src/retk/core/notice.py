import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from bson import ObjectId
from bson.tz_util import utc

from retk import const, config
from retk.models.client import client
from retk.models.tps import AuthedUser, NoticeManagerDelivery


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


async def __get_users_in_batches(batch_size=100):
    # Get the total number of users
    total_users = await client.coll.users.count_documents({})
    if config.is_local_db():
        fn = client.coll.users.find(
            {},
        ).sort(
            [("_id", -1)]
        )
    else:
        fn = client.coll.users.find(
            {}, projection=["id"]
        ).sort(
            [("_id", -1)]
        )
    for i in range(0, total_users, batch_size):
        # Sort by _id in descending order and limit the result
        users = await fn.skip(i).limit(batch_size).to_list(None)
        yield users


async def __deliver_scheduled_system_notices_batch(
        users: List[Dict[str, str]],
        sender_id: str,
        notice_id: ObjectId
):
    notices = [{
        "_id": ObjectId(),
        "senderId": sender_id,
        "recipientId": user["id"],
        "noticeId": notice_id,
        "read": False,
        "readTime": None,
    } for user in users]
    # Insert all notices at once
    await client.coll.notice_system.insert_many(notices)


def deliver_unscheduled_system_notices():
    async def _deliver_unscheduled_system_notices():
        unscheduled = await client.coll.notice_manager_delivery.find({
            "scheduled": False,
        }).to_list(None)
        for notice in unscheduled:
            notice_id = notice["_id"]
            sender_id = notice["senderId"]
            recipient_type = notice["recipientType"]
            if notice["publishAt"] <= datetime.now(tz=utc):
                # send notice
                if recipient_type == const.notice.RecipientTypeEnum.ALL.value:
                    async for users in __get_users_in_batches(batch_size=100):
                        await __deliver_scheduled_system_notices_batch(
                            users=users,
                            sender_id=sender_id,
                            notice_id=notice_id
                        )
                elif recipient_type == const.notice.RecipientTypeEnum.BATCH.value:
                    batch_type_ids = notice["batchTypeIds"]
                    # Create a list of notices
                    notices = [{
                        "_id": ObjectId(),
                        "senderId": sender_id,
                        "recipientId": user_id,
                        "noticeId": notice_id,
                        "read": False,
                        "readTime": None,
                    } for user_id in batch_type_ids]
                    # Insert all notices at once
                    await client.coll.notice_system.insert_many(notices)
                elif recipient_type == const.notice.RecipientTypeEnum.ADMIN.value:
                    # Get all admins
                    admins = await client.coll.users.find(
                        {"type": const.USER_TYPE.ADMIN.value}, {"id", 1}).to_list(None)
                    await __deliver_scheduled_system_notices_batch(
                        users=admins,
                        sender_id=sender_id,
                        notice_id=notice_id
                    )
                elif recipient_type == const.notice.RecipientTypeEnum.MANAGER.value:
                    # Get all managers
                    managers = await client.coll.users.find(
                        {"type": const.USER_TYPE.MANAGER.value}, {"id", 1}).to_list(None)
                    await __deliver_scheduled_system_notices_batch(
                        users=managers,
                        sender_id=sender_id,
                        notice_id=notice_id
                    )
                else:
                    raise ValueError(f"Unknown recipient type: {recipient_type}")

                # Update the notice to indicate that it has been scheduled
                await client.coll.notice_manager_delivery.update_one(
                    {"_id": notice_id},
                    {"$set": {"scheduled": True}}
                )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(_deliver_unscheduled_system_notices())
    loop.close()
    return res


async def get_user_notices(au: AuthedUser) -> Tuple[Dict[str, List[Dict]], const.CodeEnum]:
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

    n_details_dict = {n["_id"]: n for n in n_details}
    for sn in system_notices:
        detail = n_details_dict[sn["noticeId"]]
        sn["title"] = detail["title"]
        sn["content"] = detail["content"]
        sn["publishAt"] = detail["publishAt"]

    return {
        "system": system_notices,
    }, const.CodeEnum.OK
