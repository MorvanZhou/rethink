from datetime import datetime

from bson import ObjectId

from retk import const
from retk.models.client import client
from retk.models.tps import AuthedUser, NoticeManagerDelivery


async def put_system_notice(
        au: AuthedUser,
        title: str,
        content: str,
        recipient_type: int,
        batch_type_ids: list[str],
        publish_at: datetime
) -> const.Code:
    if const.USER_TYPE.id2config(au.u.type) not in (const.USER_TYPE.ADMIN, const.USER_TYPE.MANAGER):
        return const.Code.NOT_PERMITTED
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
    res = await client.coll.notice_system.insert_one(notice)
    if not res.acknowledged:
        return const.Code.OPERATION_FAILED
    return const.Code.OK