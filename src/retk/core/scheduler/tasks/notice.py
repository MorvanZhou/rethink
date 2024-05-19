import asyncio
from datetime import datetime
from typing import List, Dict

from bson import ObjectId
from bson.tz_util import utc

from retk import const, config
from retk.models.client import init_mongo


async def __get_users_in_batches(db, batch_size=100):
    # Get the total number of users
    total_users = await db["users"].count_documents({})
    if config.is_local_db():
        fn = db["users"].find(
            {},
        ).sort(
            [("_id", -1)]
        )
    else:
        fn = db["users"].find(
            {}, projection=["id"]
        ).sort(
            [("_id", -1)]
        )
    for i in range(0, total_users, batch_size):
        # Sort by _id in descending order and limit the result
        users = await fn.skip(i).limit(batch_size).to_list(None)
        yield users


async def __deliver_scheduled_system_notices_batch(
        db,
        users: List[Dict[str, str]],
        sender_id: str,
        notice_id: ObjectId
) -> int:
    if len(users) == 0:
        return 0
    notices = [{
        "_id": ObjectId(),
        "senderId": sender_id,
        "recipientId": user["id"],
        "noticeId": notice_id,
        "read": False,
        "readTime": None,
    } for user in users]
    # Insert all notices at once
    doc = await db["noticeSystem"].insert_many(notices)
    return len(doc.inserted_ids)


def deliver_unscheduled_system_notices():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(async_deliver_unscheduled_system_notices())
    loop.close()
    return res


async def async_deliver_unscheduled_system_notices():
    _, db = init_mongo(connection_timeout=5)
    unscheduled = await db["noticeManagerDelivery"].find({
        "scheduled": False,
    }).sort("publishAt", -1).to_list(None)
    total_users = 0
    success_users = 0
    for notice in unscheduled:
        notice_id = notice["_id"]
        sender_id = notice["senderId"]
        recipient_type = notice["recipientType"]
        # notice["publishAt"] is utc time but the tzinfo is not set, so we need to set it
        if notice["publishAt"].astimezone(utc) <= datetime.now(tz=utc):
            # send notice
            if recipient_type == const.notice.RecipientTypeEnum.ALL.value:
                async for users in __get_users_in_batches(db, batch_size=100):
                    success_users_count = await __deliver_scheduled_system_notices_batch(
                        db=db,
                        users=users,
                        sender_id=sender_id,
                        notice_id=notice_id
                    )
                    total_users += len(users)
                    success_users += success_users_count
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
                if len(notices) > 0:
                    docs = await db["noticeSystem"].insert_many(notices)
                    success_users += len(docs.inserted_ids)
                total_users += len(batch_type_ids)
            elif recipient_type == const.notice.RecipientTypeEnum.ADMIN.value:
                # Get all admins
                admins = await db["users"].find(
                    {"type": const.USER_TYPE.ADMIN.id}, {"id", 1}).to_list(None)
                success_users_count = await __deliver_scheduled_system_notices_batch(
                    db=db,
                    users=admins,
                    sender_id=sender_id,
                    notice_id=notice_id
                )
                total_users += len(admins)
                success_users += success_users_count
            elif recipient_type == const.notice.RecipientTypeEnum.MANAGER.value:
                # Get all managers
                managers = await db["users"].find(
                    {"type": const.USER_TYPE.MANAGER.id}, projection=["id"]).to_list(None)
                success_users_count = await __deliver_scheduled_system_notices_batch(
                    db=db,
                    users=managers,
                    sender_id=sender_id,
                    notice_id=notice_id
                )
                total_users += len(managers)
                success_users += success_users_count
            else:
                raise ValueError(f"Unknown recipient type: {recipient_type}")

            # Update the notice to indicate that it has been scheduled
            await db["noticeManagerDelivery"].update_one(
                {"_id": notice_id},
                {"$set": {"scheduled": True}}
            )
    return f"send success {success_users}/{total_users} users"
