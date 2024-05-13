from datetime import datetime
from typing import List, Dict, Optional, Tuple

from bson import ObjectId

from retk import const
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
        publish_at = datetime.now()
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

    for i in range(0, total_users, batch_size):
        # Sort by _id in descending order and limit the result
        users = await client.coll.users.find(
            {}, projection=["id"]
        ).sort(
            [("_id", -1)]
        ).skip(i).limit(batch_size).to_list(None)
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


async def deliver_unscheduled_system_notices():
    unscheduled = await client.coll.notice_manager_delivery.find({
        "scheduled": False,
    }).to_list(None)
    for notice in unscheduled:
        notice_id = notice["_id"]
        sender_id = notice["senderId"]
        recipient_type = notice["recipientType"]
        if notice["publishAt"] <= datetime.now():
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


async def get_user_notice(au: AuthedUser) -> Tuple[Dict[str, List[Dict]], const.CodeEnum]:
    system_notices = await client.coll.notice_system.find(
        {"recipientId": au.u.id},
        projection=["noticeId", "read", "readTime"]
    ).to_list(None)

    return {
        "system": system_notices,
    }, const.CodeEnum.OK
